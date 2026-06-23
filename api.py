"""
ResumeAI FastAPI Backend
Serves static frontend and provides REST API for all ML/NLP operations.
"""

import os
import io
import json
import time
import sqlite3
import pickle
import tempfile
import re
from collections import Counter

import firebase_admin
from firebase_admin import credentials, firestore

import numpy as np
import pandas as pd

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from src.nlp_utils import clean_text, extract_skills, parse_resume_sections
from src.screen_matcher import ResumeMatcher

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

# Firebase Initialization
FIREBASE_CRED_PATH = "serviceAccountKey.json"
db = None

try:
    if not firebase_admin._apps:
        if os.path.exists(FIREBASE_CRED_PATH):
            cred = credentials.Certificate(FIREBASE_CRED_PATH)
            firebase_admin.initialize_app(cred)
            print(f"✅ Successfully initialized Firebase using {FIREBASE_CRED_PATH}.")
        elif "FIREBASE_CREDENTIALS_JSON" in os.environ:
            import json
            cred_dict = json.loads(os.environ["FIREBASE_CREDENTIALS_JSON"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Successfully initialized Firebase using env var credentials.")
        else:
            # Fallback to Application Default Credentials (ADC)
            firebase_admin.initialize_app(options={'projectId': 'ai-resume-872f9'})
            print("✅ Successfully initialized Firebase using Application Default Credentials (ADC).")
    
    db = firestore.client()
except Exception as e:
    print(f"❌ Failed to initialize Firebase: {e}\n⚠️ Please run 'gcloud auth application-default login' in your terminal.")
    db = None

app = FastAPI(title="ResumeAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# No-cache middleware — ensures browser always loads latest JS/CSS
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") and (path.endswith(".js") or path.endswith(".css") or path.endswith(".html")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse("static/index.html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

@app.get("/style.css", response_class=FileResponse)
async def serve_style():
    return FileResponse("static/style.css")

@app.get("/app.js", response_class=FileResponse)
async def serve_app():
    return FileResponse("static/app.js")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ─────────────────────────────────────────────
# Constants & Schema
# ─────────────────────────────────────────────
REQUIRED_COLUMNS = {"name", "email", "resume_text"}
OPTIONAL_DEFAULTS = {
    "phone": "N/A",
    "category": "General",
    "experience_years": 0,
    "education_degree": "Not Specified",
    "education_institution": "Not Specified",
    "skills": "",
    "id": None,
}

# ─────────────────────────────────────────────
# Global State (in-memory dataset store)
# ─────────────────────────────────────────────
_dataset: List[dict] = []
_matcher = ResumeMatcher()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _load_sqlite_as_dataset():
    """Load from the existing SQLite DB as fallback."""
    db_path = "data/candidates.db"
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(
            "SELECT id, name, email, phone, category, experience_years, "
            "education_degree, education_institution, skills, resume_text FROM candidates",
            conn
        )
        conn.close()
        return df.to_dict(orient="records")
    except Exception:
        return []


def _normalize_df(df: pd.DataFrame) -> List[dict]:
    """Normalize uploaded CSV columns to the expected schema."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    for col, default in OPTIONAL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default

    if df["id"].isnull().all():
        df["id"] = range(1, len(df) + 1)

    df["experience_years"] = pd.to_numeric(df["experience_years"], errors="coerce").fillna(0).astype(int)

    mask_empty_skills = df["skills"].isna() | (df["skills"].astype(str).str.strip() == "")
    if mask_empty_skills.any():
        df.loc[mask_empty_skills, "skills"] = df.loc[mask_empty_skills, "resume_text"].apply(
            lambda t: ", ".join(extract_skills(str(t)))
        )

    return df.to_dict(orient="records")


def _load_firestore_as_dataset() -> List[dict]:
    """Load from Firestore 'candidates' collection."""
    if not db:
        return []
    try:
        docs = db.collection("candidates").stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"⚠️ Firestore load failed: {e}")
        return []


def _save_dataset_to_firestore(dataset: List[dict]):
    """Save dataset to Firestore using batches."""
    if not db or not dataset:
        return
    try:
        coll_ref = db.collection("candidates")
        batch = db.batch()
        count = 0
        for i, item in enumerate(dataset):
            doc_id = str(item.get("id", i))
            doc_ref = coll_ref.document(doc_id)
            batch.set(doc_ref, item)
            count += 1
            if count % 400 == 0:
                batch.commit()
                batch = db.batch()
        if count % 400 != 0:
            batch.commit()
        print(f"✅ Successfully saved {len(dataset)} candidates to Firestore.")
    except Exception as e:
        print(f"❌ Failed to save to Firestore: {e}")


def _auto_load_dataset():
    """Try to load dataset from Firestore, then SQLite, then sample CSV, on startup."""
    global _dataset

    # 1. Try Firestore first
    firestore_data = _load_firestore_as_dataset()
    if firestore_data:
        _dataset = firestore_data
        print(f"✅ Auto-loaded {len(_dataset):,} candidates from Firestore.")
        return

    # 2. Try SQLite first
    try:
        db_path = "data/candidates.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(
                "SELECT id, name, email, phone, category, experience_years, "
                "education_degree, education_institution, skills, resume_text FROM candidates",
                conn
            )
            conn.close()
            if not df.empty:
                _dataset = df.to_dict(orient="records")
                print(f"✅ Auto-loaded {len(_dataset):,} candidates from SQLite.")
                return
    except Exception as e:
        print(f"⚠️ SQLite load failed: {e}")

    # 2. Fall back to CSV files
    for csv_path in ["sample_dataset.csv", "data/candidates_dataset.csv"]:
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                for col, default in OPTIONAL_DEFAULTS.items():
                    if col not in df.columns:
                        df[col] = default
                df["experience_years"] = pd.to_numeric(df["experience_years"], errors="coerce").fillna(0).astype(int)
                _dataset = df.to_dict(orient="records")
                print(f"✅ Auto-loaded {len(_dataset):,} candidates from {csv_path}.")
                return
            except Exception as e:
                print(f"⚠️ CSV load failed ({csv_path}): {e}")

    print("⚠️ No dataset auto-loaded — upload one via the UI.")

# Auto-load on startup
_auto_load_dataset()


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/upload-dataset")
async def upload_dataset(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accept a CSV file, validate it, store it globally."""
    global _dataset

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    contents = await file.read()

    # Try multiple encodings
    df = None
    for encoding in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
        try:
            df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
            break
        except Exception:
            continue

    if df is None:
        raise HTTPException(status_code=400, detail="Failed to parse CSV. Make sure it is a valid CSV file.")

    # Show the actual columns in error for debugging
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"CSV is missing required columns: {missing}. Your CSV has: {list(df.columns)}"
        )

    try:
        _dataset = _normalize_df(df)
        background_tasks.add_task(_save_dataset_to_firestore, _dataset)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "success": True,
        "total": len(_dataset),
        "columns": list(df.columns),
        "message": f"Successfully loaded {len(_dataset):,} candidates."
    }


@app.get("/api/dataset-info")
async def dataset_info():
    """Return stats about the currently loaded dataset."""
    global _dataset

    if not _dataset:
        _dataset = _load_sqlite_as_dataset()

    if not _dataset:
        return {"loaded": False, "total": 0}

    df = pd.DataFrame(_dataset)

    categories = {}
    if "category" in df.columns:
        categories = df["category"].value_counts().to_dict()

    avg_exp = 0
    if "experience_years" in df.columns:
        avg_exp = round(float(df["experience_years"].mean()), 1)

    exp_bands = {}
    if "experience_years" in df.columns:
        bins = [0, 2, 5, 8, 12, 50]
        labels = ["0-2 yrs", "3-5 yrs", "6-8 yrs", "9-12 yrs", "13+ yrs"]
        df["exp_band"] = pd.cut(df["experience_years"], bins=bins, labels=labels)
        exp_bands = df["exp_band"].value_counts().reindex(labels).fillna(0).astype(int).to_dict()

    return {
        "loaded": True,
        "total": len(_dataset),
        "avg_exp": avg_exp,
        "categories": categories,
        "exp_bands": exp_bands,
        "source": "sqlite" if not _dataset else "csv"
    }


class ScreenRequest(BaseModel):
    job_description: str
    algorithm: str = "hybrid"
    filter_category: str = "All"
    min_exp: int = 0
    max_results: int = 10


@app.post("/api/screen")
async def screen_candidates(req: ScreenRequest):
    """Screen candidates against a job description."""
    global _dataset

    if not _dataset:
        _dataset = _load_sqlite_as_dataset()

    if not _dataset:
        raise HTTPException(status_code=400, detail="No dataset loaded. Please upload a CSV first.")

    if not req.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    # Filter candidates
    candidates = [
        c for c in _dataset
        if int(c.get("experience_years", 0)) >= req.min_exp
        and (req.filter_category == "All" or c.get("category") == req.filter_category)
    ]

    if not candidates:
        return {"results": [], "total_screened": 0, "used_bert": False, "time_seconds": 0}

    t_start = time.time()
    results, used_bert = _matcher.screen_candidates(
        req.job_description, candidates,
        algorithm=req.algorithm,
        max_results=req.max_results      # ⚡ ML predictions only for top N
    )
    t_end = time.time()

    top = results[:req.max_results]

    # Extract skill gap for top candidates
    jd_skills = set(extract_skills(req.job_description))
    for c in top:
        cand_skills = set(extract_skills(str(c.get("resume_text", ""))))
        c["matched_skills"] = sorted(jd_skills & cand_skills)
        c["missing_skills"] = sorted(jd_skills - cand_skills)
        # Remove bulky resume_text from response
        c.pop("resume_text", None)

    response = {
        "results": top,
        "total_screened": len(candidates),
        "used_bert": used_bert,
        "time_seconds": round(t_end - t_start, 2),
    }

    if db:
        import uuid
        from datetime import datetime
        try:
            doc_id = "SCR-" + str(uuid.uuid4())[:8].upper()
            db.collection("screening_history").document(doc_id).set({
                "job_description": req.job_description,
                "filters": {
                    "algorithm": req.algorithm,
                    "category": req.filter_category,
                    "min_exp": req.min_exp
                },
                "total_screened": len(candidates),
                "top_candidates": top,
                "created_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to log screening: {e}")

    return response


class ResumeRequest(BaseModel):
    resume_text: str
    job_description: Optional[str] = ""


@app.post("/api/analyze-resume")
async def analyze_resume(req: ResumeRequest):
    """Analyze a single resume text."""
    if not req.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")

    parsed = parse_resume_sections(req.resume_text)
    rf_cat, rf_conf, gb_cat, gb_conf = _matcher.predict_category(req.resume_text)

    result = {
        "parsed": parsed,
        "rf_category": rf_cat,
        "rf_confidence": round(rf_conf * 100, 1),
        "gb_category": gb_cat,
        "gb_confidence": round(gb_conf * 100, 1),
        "match_scores": None,
    }

    if req.job_description.strip():
        tfidf_sim = _matcher.calculate_tfidf_similarity(req.job_description, [req.resume_text])[0]
        bert_scores, used_bert = _matcher.calculate_bert_similarity(req.job_description, [req.resume_text])
        bert_sim = bert_scores[0]
        keyword_score = _matcher.calculate_keyword_score(req.job_description, [req.resume_text])[0]
        hybrid = (0.5 * (bert_sim if used_bert else tfidf_sim) + 0.5 * keyword_score) * 100

        jd_skills = set(extract_skills(req.job_description))
        cand_skills = set(extract_skills(req.resume_text))

        result["match_scores"] = {
            "hybrid": round(hybrid, 1),
            "semantic": round((bert_sim if used_bert else tfidf_sim) * 100, 1),
            "keyword": round(keyword_score * 100, 1),
            "used_bert": used_bert,
            "matched_skills": sorted(jd_skills & cand_skills),
            "missing_skills": sorted(jd_skills - cand_skills),
        }

        if hybrid >= 75:
            result["recommendation"] = "Highly Recommended"
        elif hybrid >= 50:
            result["recommendation"] = "Consider for Interview"
        else:
            result["recommendation"] = "Not a Fit"

    if db:
        import uuid
        from datetime import datetime
        try:
            doc_id = "RES-" + str(uuid.uuid4())[:8].upper()
            db.collection("resume_analyses").document(doc_id).set({
                "parsed": result["parsed"],
                "category": result["rf_category"] if result["rf_confidence"] >= result["gb_confidence"] else result["gb_category"],
                "match_scores": result.get("match_scores"),
                "recommendation": result.get("recommendation"),
                "created_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to log resume analysis: {e}")

    return result


@app.get("/api/model-metrics")
async def model_metrics():
    """Return saved ML model metrics."""
    metrics_path = "models/metrics.json"
    if not os.path.exists(metrics_path):
        return {"available": False}
    with open(metrics_path, "r") as f:
        data = json.load(f)
    data["available"] = True
    return data


# ─────────────────────────────────────────────
# ADVANCED AI FEATURE ENDPOINTS
# ─────────────────────────────────────────────

_IQ_BANK = {
    "Python": [
        "Explain the difference between `@staticmethod` and `@classmethod` in Python.",
        "How do Python generators work, and what are their advantages over regular functions?",
        "What are context managers? Create a custom one using `__enter__` and `__exit__`.",
        "Explain Python's GIL and its impact on multi-threaded applications.",
        "How would you profile and optimize a slow Python function processing large datasets?"
    ],
    "Machine Learning": [
        "Explain the bias-variance tradeoff with a concrete real-world example.",
        "How do you handle class imbalance in a binary classification problem?",
        "What is cross-validation and why is it essential for model evaluation?",
        "Compare Random Forest vs Gradient Boosting — when would you prefer each?",
        "How do you prevent overfitting in a deep neural network?"
    ],
    "SQL": [
        "Explain the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN.",
        "What is a window function? Give an example using RANK() or ROW_NUMBER().",
        "How would you optimize a slow SQL query on a table with millions of rows?",
        "Explain the difference between WHERE and HAVING clauses.",
        "What are database indexes and how do they improve query performance?"
    ],
    "NLP": [
        "Explain the architecture of the BERT transformer model.",
        "What is the difference between word2vec, GloVe, and BERT embeddings?",
        "How would you approach building a named entity recognition (NER) system?",
        "What is attention mechanism and why is it important in transformers?",
        "How do you evaluate the quality of a text summarization model?"
    ],
    "React": [
        "Explain the virtual DOM and how React uses it for performance optimization.",
        "What are React hooks? Explain `useState`, `useEffect`, and `useCallback`.",
        "How do you manage global state in a large React application?",
        "Explain the concept of component lifecycle in React.",
        "What is the difference between controlled and uncontrolled components?"
    ],
    "Docker": [
        "Explain the difference between Docker images and Docker containers.",
        "What is a Dockerfile and what are the key instructions?",
        "How do you optimize a Docker image to reduce its size?",
        "Explain Docker Compose and when you would use it.",
        "What are the security best practices when running Docker in production?"
    ],
    "AWS": [
        "Explain the key differences between EC2, ECS, and Lambda.",
        "What is an S3 bucket and what are its storage classes?",
        "How would you design a highly available architecture on AWS?",
        "Explain IAM roles and policies and why they matter for security.",
        "What is AWS CloudFormation and how does it enable Infrastructure as Code?"
    ],
    "SEO": [
        "What is the difference between on-page and off-page SEO?",
        "How do Core Web Vitals affect search engine rankings?",
        "Explain E-A-T in SEO and why Google considers it important.",
        "What tools do you use for keyword research and competitor analysis?",
        "How would you recover a website that was hit by a Google algorithmic penalty?"
    ],
    "Financial Analysis": [
        "Explain the three major financial statements and how they interconnect.",
        "How do you perform a discounted cash flow (DCF) valuation?",
        "What is EBITDA and why is it commonly used in financial analysis?",
        "Explain the difference between liquidity and solvency ratios.",
        "How would you identify red flags in a company's financial statements?"
    ],
    "Product Management": [
        "How do you prioritize features on a product roadmap with limited resources?",
        "Describe your process for writing a product requirements document (PRD).",
        "How do you measure the success of a newly launched feature?",
        "Give an example of a difficult stakeholder trade-off decision you navigated.",
        "How do you balance immediate user needs with long-term business strategy?"
    ],
    "Agile": [
        "Explain the key ceremonies in a Scrum sprint.",
        "What is the difference between Scrum and Kanban methodologies?",
        "How do you handle a situation where a sprint goal is at risk of not being met?",
        "What are the roles in a Scrum team and their core responsibilities?",
        "How do you estimate user story points effectively?"
    ],
    "Data Science & AI": [
        "Walk us through your end-to-end machine learning pipeline for a real project.",
        "How do you handle missing data in a dataset with 30%+ null values?",
        "What metrics would you use to evaluate a recommendation system?",
        "Explain PCA and when you would apply dimensionality reduction.",
        "Describe a project where you deployed a model to production and monitored it."
    ]
}


class ATSRequest(BaseModel):
    resume_text: str
    job_description: Optional[str] = ""


@app.post("/api/ats-score")
async def ats_score_endpoint(req: ATSRequest):
    """Calculate ATS (Applicant Tracking System) compatibility score."""
    text = req.resume_text
    text_lower = text.lower()
    breakdown = {}

    # 1. Contact Info (10 pts)
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
    has_phone = bool(re.search(r'\+?\d[\d\-\(\)\s]{7,}\d', text))
    c_score = (5 if has_email else 0) + (5 if has_phone else 0)
    breakdown["Contact Information"] = {
        "score": c_score, "max": 10,
        "status": "Complete" if c_score == 10 else "Missing info",
        "ok": c_score == 10,
        "tip": "Email and phone are required for ATS parsing."
    }

    # 2. Section Headers (15 pts)
    sections = ["experience", "education", "skills", "summary", "certifications", "projects"]
    found = [s for s in sections if s in text_lower]
    s_score = min(len(found) * 3, 15)
    breakdown["Section Structure"] = {
        "score": s_score, "max": 15,
        "status": f"{len(found)}/{len(sections)} sections found",
        "ok": s_score >= 12,
        "tip": f"Found: {', '.join(found) if found else 'None'}. Add missing standard sections."
    }

    # 3. Keyword Match (25 pts)
    if req.job_description and req.job_description.strip():
        jd_skills = set(extract_skills(req.job_description))
        resume_skills = set(extract_skills(text))
        if jd_skills:
            matched = jd_skills & resume_skills
            ratio = len(matched) / len(jd_skills)
            kw_score = round(ratio * 25)
            kw_status = f"{len(matched)}/{len(jd_skills)} keywords matched"
            kw_ok = ratio > 0.5
        else:
            kw_score, kw_status, kw_ok = 15, "No JD skills detected", True
    else:
        kw_score, kw_status, kw_ok = 15, "No JD provided", True
    breakdown["Keyword Relevance"] = {
        "score": kw_score, "max": 25,
        "status": kw_status, "ok": kw_ok,
        "tip": "Include more skills and keywords matching the job description."
    }

    # 4. Action Verbs (15 pts)
    action_verbs = ["managed", "developed", "created", "implemented", "led", "built", "designed",
                    "analyzed", "improved", "increased", "reduced", "achieved", "delivered",
                    "optimized", "launched", "coordinated", "established", "spearheaded"]
    found_verbs = [v for v in action_verbs if v in text_lower]
    av_score = min(len(found_verbs) * 2, 15)
    breakdown["Action Verbs"] = {
        "score": av_score, "max": 15,
        "status": f"{len(found_verbs)} strong verbs found",
        "ok": av_score >= 8,
        "tip": "Use strong action verbs: Spearheaded, Optimized, Delivered, Architected."
    }

    # 5. Quantified Achievements (20 pts)
    metrics = re.findall(r'\b\d+[%+]?\b', text)
    qa_score = min(len(metrics) * 2, 20)
    breakdown["Quantified Results"] = {
        "score": qa_score, "max": 20,
        "status": f"{len(metrics)} quantified metrics",
        "ok": qa_score >= 10,
        "tip": "Add numbers: 'Improved performance by 40%', 'Managed team of 8 engineers'."
    }

    # 6. Resume Length (15 pts)
    word_count = len(text.split())
    if 350 <= word_count <= 900:
        len_score, len_status, len_ok = 15, f"{word_count} words (ideal)", True
    elif 200 <= word_count < 350 or 900 < word_count <= 1200:
        len_score, len_status, len_ok = 10, f"{word_count} words (acceptable)", True
    else:
        len_score, len_status, len_ok = 5, f"{word_count} words (too {'short' if word_count < 200 else 'long'})", False
    breakdown["Resume Length"] = {
        "score": len_score, "max": 15,
        "status": len_status, "ok": len_ok,
        "tip": "Optimal length: 350-900 words (1-2 pages)."
    }

    total = sum(v["score"] for v in breakdown.values())
    max_total = sum(v["max"] for v in breakdown.values())
    percentage = round(total / max_total * 100, 1)

    if percentage >= 85: grade, grade_color = "A+", "#10b981"
    elif percentage >= 75: grade, grade_color = "A", "#00f5ff"
    elif percentage >= 65: grade, grade_color = "B", "#7c3aed"
    elif percentage >= 50: grade, grade_color = "C", "#fbbf24"
    else: grade, grade_color = "D", "#ef4444"

    response = {
        "ats_score": total, "max_score": max_total,
        "percentage": percentage, "grade": grade, "grade_color": grade_color,
        "breakdown": breakdown,
        "recommendation": "Excellent ATS compatibility! This resume will pass most ATS filters." if percentage >= 75
                          else "Good, but minor improvements recommended before submission." if percentage >= 55
                          else "Significant improvements needed — most ATS systems may filter this resume."
    }

    if db:
        import uuid
        from datetime import datetime
        try:
            doc_id = "ATS-" + str(uuid.uuid4())[:8].upper()
            db.collection("ats_scores").document(doc_id).set({
                "score_percentage": percentage,
                "grade": grade,
                "job_description_provided": bool(req.job_description),
                "breakdown_summary": {k: v["score"] for k, v in breakdown.items()},
                "created_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to log ATS score: {e}")

    return response


@app.post("/api/interview-questions")
async def interview_questions_endpoint(req: ResumeRequest):
    """Generate targeted interview questions based on resume skills."""
    skills = extract_skills(req.resume_text)
    jd_skills = extract_skills(req.job_description) if req.job_description else []
    priority_skills = [s for s in skills if s in jd_skills] + [s for s in skills if s not in jd_skills]

    questions_out = []
    used_cats = set()

    for skill in priority_skills:
        sk = skill.lower()
        for cat_key, qs in _IQ_BANK.items():
            cat_lower = cat_key.lower()
            if cat_key not in used_cats and (
                cat_lower in sk or sk in cat_lower or
                any(w in sk for w in cat_lower.split() if len(w) > 3)
            ):
                parsed = parse_resume_sections(req.resume_text)
                exp = parsed.get("experience_years", 2)
                difficulty = "Senior" if exp >= 5 else "Mid-Level" if exp >= 2 else "Junior"
                questions_out.append({
                    "category": cat_key,
                    "skill_matched": skill,
                    "difficulty": difficulty,
                    "questions": qs[:3]
                })
                used_cats.add(cat_key)
                if len(questions_out) >= 6:
                    break
        if len(questions_out) >= 6:
            break

    if not questions_out:
        questions_out = [{
            "category": "General Competency",
            "skill_matched": "General",
            "difficulty": "General",
            "questions": [
                "Tell me about your most challenging project and how you overcame the obstacles.",
                "Where do you see yourself in 5 years, and how does this role fit that vision?",
                "Describe a time you disagreed with a team member. How did you resolve it?"
            ]
        }]

    response = {
        "questions": questions_out,
        "total_questions": sum(len(q["questions"]) for q in questions_out),
        "skills_analyzed": len(skills)
    }

    if db:
        import uuid
        from datetime import datetime
        try:
            doc_id = "INT-" + str(uuid.uuid4())[:8].upper()
            db.collection("interview_questions").document(doc_id).set({
                "skills_analyzed": len(skills),
                "total_questions": response["total_questions"],
                "categories": [q["category"] for q in questions_out],
                "created_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to log interview questions: {e}")

    return response


@app.post("/api/fraud-detect")
async def fraud_detect_endpoint(req: ResumeRequest):
    """Detect potential fraud and anomaly indicators in a resume."""
    global _dataset
    text = req.resume_text
    text_lower = text.lower()
    flags = []
    risk_score = 0

    all_resume_skills = extract_skills(text)
    word_count = max(len(text.split()), 1)

    skill_density = len(all_resume_skills) / word_count
    if skill_density > 0.08:
        flags.append({"type": "Keyword Stuffing", "severity": "HIGH",
                      "icon": "🔴",
                      "detail": f"Unusually high skill density ({skill_density*100:.1f}% of words are skills). Possible keyword stuffing for ATS."})
        risk_score += 35

    exp_matches = re.findall(r'(\d+)\+?\s*years?', text_lower)
    if exp_matches:
        max_exp = max((int(x) for x in exp_matches if int(x) <= 50), default=0)
        if max_exp > 20:
            flags.append({"type": "Experience Inflation", "severity": "MEDIUM",
                          "icon": "🟡",
                          "detail": f"Claims {max_exp}+ years of experience. Verify employment dates carefully."})
            risk_score += 20

    superlatives = ["best", "expert level", "world-class", "exceptional", "always exceeds",
                    "top performer", "never failed", "perfect", "unparalleled"]
    found_sup = [s for s in superlatives if s in text_lower]
    if len(found_sup) >= 3:
        flags.append({"type": "Excessive Self-Promotion", "severity": "LOW",
                      "icon": "🟡",
                      "detail": f"Contains {len(found_sup)} excessive self-promotion phrases: {', '.join(found_sup[:3])}"})
        risk_score += 10

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match and _dataset:
        email = email_match.group(0).lower()
        duplicates = [c for c in _dataset if str(c.get("email", "")).lower() == email]
        if len(duplicates) > 1:
            flags.append({"type": "Duplicate Resume Detected", "severity": "HIGH",
                          "icon": "🔴",
                          "detail": f"Email {email} appears {len(duplicates)} times in the database. Possible duplicate submission."})
            risk_score += 40

    if word_count < 100:
        flags.append({"type": "Incomplete Resume", "severity": "MEDIUM",
                      "icon": "🟡",
                      "detail": f"Resume is very short ({word_count} words). Likely incomplete or a placeholder."})
        risk_score += 15

    risk_score = min(risk_score, 100)
    if risk_score >= 50: risk_level, risk_color = "HIGH RISK", "#ef4444"
    elif risk_score >= 25: risk_level, risk_color = "MEDIUM RISK", "#fbbf24"
    else: risk_level, risk_color = "LOW RISK", "#10b981"

    response = {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "flags": flags,
        "flags_count": len(flags),
        "is_suspicious": risk_score >= 40,
        "recommendation": "Manual review strongly recommended before proceeding." if risk_score >= 40
                          else "Some concerns detected — verify key claims independently." if risk_score >= 20
                          else "No significant fraud indicators. Resume appears authentic."
    }

    if db:
        import uuid
        from datetime import datetime
        try:
            doc_id = "FRD-" + str(uuid.uuid4())[:8].upper()
            db.collection("fraud_reports").document(doc_id).set({
                "risk_score": risk_score,
                "risk_level": risk_level,
                "flags_count": len(flags),
                "flags": [f["type"] for f in flags],
                "created_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to log fraud detection: {e}")

    return response


@app.post("/api/resume-summary")
async def resume_summary_endpoint(req: ResumeRequest):
    """Generate an AI-powered candidate profile summary."""
    parsed = parse_resume_sections(req.resume_text)
    rf_cat, rf_conf, gb_cat, gb_conf = _matcher.predict_category(req.resume_text)
    skills = parsed["skills"][:6]
    category = rf_cat if rf_conf >= gb_conf else gb_cat
    conf = round(max(rf_conf, gb_conf) * 100, 1)

    skill_str = ", ".join(skills[:3]) if skills else "various technical areas"
    exp = parsed["experience_years"]
    level = "Senior" if exp >= 7 else "Mid-Level" if exp >= 3 else "Junior"

    summary = (
        f"{parsed['name']} is a {level} {category} professional with {exp} years of hands-on experience. "
        f"Their core technical expertise spans {skill_str}. "
    )
    if parsed["education"] and parsed["education"] != "Undergraduate Degree":
        summary += f"Academically, they hold a {parsed['education']}. "
    if req.job_description and req.job_description.strip():
        jd_sk = set(extract_skills(req.job_description))
        matched = set(extract_skills(req.resume_text)) & jd_sk
        if matched:
            summary += f"For this specific role, they demonstrate strong alignment in {', '.join(list(matched)[:3])}."
        else:
            summary += "Their profile shows potential for growth in the required skill areas."
    else:
        summary += f"Overall a well-rounded {category} professional ready for impactful contributions."

    strengths = []
    if exp >= 5: strengths.append(f"{exp} years of extensive experience")
    if len(skills) >= 5: strengths.append("Broad multi-skill technical profile")
    if parsed["education"] != "Undergraduate Degree": strengths.append("Strong academic credentials")
    if exp < 3: strengths.append("Motivated early-career professional")
    if not strengths: strengths.append("Solid foundational skill set")

    return {
        "summary": summary,
        "candidate_name": parsed["name"],
        "experience_years": exp,
        "level": level,
        "domain": category,
        "ml_confidence": conf,
        "top_skills": skills,
        "strengths": strengths,
        "education": parsed["education"]
    }


class ExplainRequest(BaseModel):
    resume_text: str
    job_description: str


@app.post("/api/explain")
async def explain_recommendation_endpoint(req: ExplainRequest):
    """Provide Explainable AI (XAI) reasoning for a candidate recommendation."""
    jd_skills = set(extract_skills(req.job_description))
    cand_skills = set(extract_skills(req.resume_text))
    matched = jd_skills & cand_skills
    missing = jd_skills - cand_skills
    parsed = parse_resume_sections(req.resume_text)

    tfidf_score = float(_matcher.calculate_tfidf_similarity(req.job_description, [req.resume_text])[0])
    kw_score = float(_matcher.calculate_keyword_score(req.job_description, [req.resume_text])[0])
    hybrid = (0.5 * tfidf_score + 0.5 * kw_score) * 100

    factors = []
    if matched:
        factors.append({
            "factor": "Skill Alignment", "impact": "POSITIVE",
            "weight": round(kw_score * 40, 1),
            "icon": "✅",
            "detail": f"{len(matched)} of {len(jd_skills)} required skills matched: {', '.join(list(matched)[:4])}"
        })
    if tfidf_score > 0.25:
        factors.append({
            "factor": "Semantic Relevance", "impact": "POSITIVE",
            "weight": round(tfidf_score * 35, 1),
            "icon": "✅",
            "detail": f"Resume content is semantically aligned with the job description ({tfidf_score*100:.1f}% similarity)."
        })
    if parsed["experience_years"] >= 3:
        factors.append({
            "factor": "Work Experience", "impact": "POSITIVE",
            "weight": min(parsed["experience_years"] * 2, 15),
            "icon": "✅",
            "detail": f"{parsed['experience_years']} years of professional experience detected."
        })
    if missing:
        factors.append({
            "factor": "Missing Required Skills", "impact": "NEGATIVE",
            "weight": round((len(missing) / max(len(jd_skills), 1)) * 25, 1),
            "icon": "❌",
            "detail": f"{len(missing)} required skills absent: {', '.join(list(missing)[:4])}"
        })
    if parsed["experience_years"] < 2:
        factors.append({
            "factor": "Limited Experience", "impact": "NEGATIVE",
            "weight": 10.0, "icon": "⚠️",
            "detail": f"Only {parsed['experience_years']} year(s) of experience detected."
        })

    if hybrid >= 75: verdict, verdict_color = "Highly Recommended", "#10b981"
    elif hybrid >= 50: verdict, verdict_color = "Consider for Interview", "#fbbf24"
    else: verdict, verdict_color = "Not Recommended", "#ef4444"

    return {
        "hybrid_score": round(hybrid, 1),
        "verdict": verdict, "verdict_color": verdict_color,
        "verdict_reason": "Strong alignment across skills, semantic relevance, and experience." if hybrid >= 75
                          else "Reasonable fit — skill gaps exist but core competency present." if hybrid >= 50
                          else "Significant mismatch in required skills and domain experience.",
        "factors": factors,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "skill_coverage": round(len(matched)/max(len(jd_skills),1)*100, 1),
        "semantic_score": round(tfidf_score * 100, 1),
        "keyword_score": round(kw_score * 100, 1)
    }


class NotifyRequest(BaseModel):
    candidates: List[dict]
    job_title: str
    sender_name: Optional[str] = "ResumeAI HR Team"


@app.post("/api/notify-candidates")
async def notify_candidates_endpoint(req: NotifyRequest):
    """Simulate sending email notifications to shortlisted candidates."""
    sent, failed = [], []
    for c in req.candidates:
        if c.get("email") and "@" in str(c["email"]):
            sent.append({
                "name": c.get("name", "Candidate"),
                "email": c["email"],
                "status": "Sent",
                "score": c.get("score", "—"),
                "message": f"Dear {c.get('name','Candidate')}, congratulations! You have been shortlisted for '{req.job_title}'. Our team will contact you within 2-3 business days."
            })
        else:
            failed.append({"name": c.get("name", "Unknown"), "reason": "No valid email address"})
    return {
        "sent_count": len(sent), "failed_count": len(failed),
        "sent": sent, "failed": failed,
        "job_title": req.job_title,
        "message": f"Successfully notified {len(sent)} candidates for '{req.job_title}'."
    }


@app.get("/api/advanced-analytics")
async def advanced_analytics_endpoint():
    """Return advanced HR analytics from the loaded dataset."""
    global _dataset
    if not _dataset:
        _dataset = _load_sqlite_as_dataset()
    if not _dataset:
        return {"available": False}

    df = pd.DataFrame(_dataset)

    all_skills_flat = []
    for record in _dataset:
        skills_raw = str(record.get("skills", ""))
        all_skills_flat.extend([s.strip() for s in skills_raw.split(",") if s.strip()])
    top_skills = dict(Counter(all_skills_flat).most_common(12))

    exp_dist = {}
    if "experience_years" in df.columns:
        exp_dist = {str(k): int(v) for k, v in df["experience_years"].value_counts().sort_index().items()}

    cat_exp = {}
    if "category" in df.columns and "experience_years" in df.columns:
        cat_exp = {k: round(float(v), 1) for k, v in df.groupby("category")["experience_years"].mean().items()}

    total = len(_dataset)
    return {
        "available": True,
        "total_candidates": total,
        "top_skills": top_skills,
        "experience_distribution": exp_dist,
        "category_avg_experience": cat_exp,
        "hiring_funnel": {
            "Total Applied": total,
            "ATS Screened": round(total * 0.72),
            "Shortlisted": round(total * 0.18),
            "Interviewed": round(total * 0.08),
            "Hired": round(total * 0.03)
        },
        "acceptance_rate": round(total * 0.03 / max(total, 1) * 100, 1),
        "avg_time_to_hire": "12 days",
        "cost_per_hire": "$1,240"
    }


@app.post("/api/job-recommendations")
async def job_recommendations_endpoint(req: ResumeRequest):
    """Recommend alternative job titles for a candidate."""
    rf_cat, rf_conf, gb_cat, gb_conf = _matcher.predict_category(req.resume_text)
    parsed = parse_resume_sections(req.resume_text)
    exp = parsed["experience_years"]
    category = rf_cat if rf_conf >= gb_conf else gb_cat

    JOB_MAP = {
        "Software Engineering": [
            {"title": "Backend Software Engineer", "match": 92, "companies": ["Google", "Meta", "Amazon"]},
            {"title": "Full-Stack Developer", "match": 87, "companies": ["Shopify", "Stripe", "Vercel"]},
            {"title": "Cloud Infrastructure Engineer", "match": 80, "companies": ["AWS", "GCP", "Azure"]},
            {"title": "DevOps / Site Reliability Engineer", "match": 74, "companies": ["HashiCorp", "Datadog", "PagerDuty"]},
        ],
        "Data Science & AI": [
            {"title": "Machine Learning Engineer", "match": 91, "companies": ["OpenAI", "DeepMind", "Hugging Face"]},
            {"title": "Data Scientist", "match": 88, "companies": ["Netflix", "Uber", "Airbnb"]},
            {"title": "AI Research Scientist", "match": 79, "companies": ["Google Brain", "FAIR", "Microsoft Research"]},
            {"title": "Data Analyst", "match": 74, "companies": ["Tableau", "Palantir", "Snowflake"]},
        ],
        "Product Management": [
            {"title": "Senior Product Manager", "match": 90, "companies": ["Apple", "Notion", "Figma"]},
            {"title": "Growth Product Manager", "match": 85, "companies": ["Slack", "Dropbox", "Duolingo"]},
            {"title": "Technical Product Manager", "match": 78, "companies": ["Atlassian", "Jira", "GitHub"]},
            {"title": "Product Analyst", "match": 72, "companies": ["Amplitude", "Mixpanel", "Segment"]},
        ],
        "Marketing & Sales": [
            {"title": "Digital Marketing Manager", "match": 89, "companies": ["HubSpot", "Salesforce", "Mailchimp"]},
            {"title": "Growth Hacker", "match": 83, "companies": ["Intercom", "Buffer", "Hootsuite"]},
            {"title": "Brand Strategist", "match": 77, "companies": ["Ogilvy", "WPP", "Publicis"]},
            {"title": "B2B Sales Executive", "match": 73, "companies": ["Oracle", "SAP", "Workday"]},
        ],
        "Finance & Accounting": [
            {"title": "Senior Financial Analyst", "match": 91, "companies": ["Goldman Sachs", "JPMorgan", "BlackRock"]},
            {"title": "Investment Banking Analyst", "match": 85, "companies": ["Morgan Stanley", "Deutsche Bank", "UBS"]},
            {"title": "FP&A Manager", "match": 80, "companies": ["Apple", "Microsoft", "Meta"]},
            {"title": "Risk Analyst", "match": 74, "companies": ["Fidelity", "Vanguard", "TIAA"]},
        ]
    }

    recs = JOB_MAP.get(category, JOB_MAP["Software Engineering"])
    adjusted = []
    for job in recs:
        adj = min(job["match"] + (exp * 0.5), 99)
        level = "Senior" if exp >= 5 else "Mid-Level" if exp >= 3 else "Junior"
        adjusted.append({**job, "match": round(adj), "level": level})

    response = {
        "candidate_category": category,
        "recommendations": adjusted,
        "experience_years": exp,
        "ml_confidence": round(max(rf_conf, gb_conf) * 100, 1)
    }

    if db:
        import uuid
        from datetime import datetime
        try:
            doc_id = "JOB-" + str(uuid.uuid4())[:8].upper()
            db.collection("job_recommendations").document(doc_id).set({
                "candidate_category": category,
                "experience_years": exp,
                "top_recommendation": adjusted[0]["title"] if adjusted else None,
                "created_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to log job recommendation: {e}")

    return response


@app.post("/api/detect-language")
async def detect_language_endpoint(req: ResumeRequest):
    """Detect the language of a resume for multi-language processing."""
    text = req.resume_text.lower()
    lang_hints = {
        "Spanish":    ["experiencia", "habilidades", "educación", "trabajo", "empresa"],
        "French":     ["expérience", "compétences", "formation", "entreprise", "travail"],
        "German":     ["erfahrung", "fähigkeiten", "bildung", "kenntnisse", "unternehmen"],
        "Portuguese": ["experiência", "habilidades", "educação", "empresa", "anos"],
        "Arabic":     ["خبرة", "مهارات", "تعليم", "عمل"],
        "Hindi":      ["अनुभव", "कौशल", "शिक्षा"],
        "Chinese":    ["经验", "技能", "教育"],
    }
    detected, confidence = "English", 95.0
    for lang, hints in lang_hints.items():
        matches = sum(1 for h in hints if h in text)
        if matches >= 2:
            detected = lang
            confidence = round(min(60 + matches * 10, 95), 1)
            break
    return {
        "language": detected,
        "confidence": confidence,
        "is_english": detected == "English",
        "translation_needed": detected != "English",
        "flag": {"English": "🇺🇸", "Spanish": "🇪🇸", "French": "🇫🇷", "German": "🇩🇪",
                 "Portuguese": "🇵🇹", "Arabic": "🇸🇦", "Hindi": "🇮🇳", "Chinese": "🇨🇳"}.get(detected, "🌐"),
        "processing_note": "Resume is in English — full NLP processing available." if detected == "English"
                           else f"Resume appears to be in {detected}. Translation recommended for best results."
    }


# ─────────────────────────────────────────────
# MODULE 3 — Recommend to HR Endpoint
# ─────────────────────────────────────────────

class HRCandidateItem(BaseModel):
    rank: int
    name: str
    email: str
    score: float
    experience_years: int
    category: str
    education: Optional[str] = "Not Specified"
    recommendation: Optional[str] = "—"
    matched_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []
    note: Optional[str] = ""


class HRRecommendRequest(BaseModel):
    candidates: List[HRCandidateItem]
    job_title: str
    job_description: Optional[str] = ""


@app.post("/api/recommend-to-hr")
async def recommend_to_hr(req: HRRecommendRequest):
    """
    Module 3: Submit a curated HR shortlist for HR review.
    Generates a structured recommendation report with stats
    and action items for the recruiting team.
    """
    import hashlib
    from datetime import datetime

    if not req.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided in the shortlist.")

    # Generate a unique report ID
    payload_str = f"{req.job_title}{','.join(c.name for c in req.candidates)}{datetime.now().isoformat()}"
    report_id = "HR-" + hashlib.md5(payload_str.encode()).hexdigest()[:8].upper()

    # Compute summary stats
    scores = [c.score for c in req.candidates]
    avg_score    = round(sum(scores) / len(scores), 1)
    highest      = max(scores)
    lowest       = min(scores)
    highly_rec   = [c for c in req.candidates if c.recommendation == "Highly Recommended"]
    consider_rec = [c for c in req.candidates if c.recommendation == "Consider for Interview"]
    avg_exp      = round(sum(c.experience_years for c in req.candidates) / len(req.candidates), 1)

    # Build action items
    next_steps = [
        f"📅 Schedule initial screening calls with {len(highly_rec)} Highly Recommended candidate(s): " +
        ", ".join(c.name for c in highly_rec[:3]) if highly_rec else "No highly recommended candidates in this batch.",

        f"📋 Secondary review recommended for {len(consider_rec)} candidate(s) marked 'Consider for Interview'." if consider_rec else
        "All candidates are clearly categorized — no secondary review needed.",

        f"📧 Send interview invites to top {min(len(req.candidates), 3)} candidates within 2 business days.",

        f"📝 Review recruiter notes attached to {sum(1 for c in req.candidates if c.note)} candidate profile(s).",

        f"🎯 Position: '{req.job_title}' | Average match score: {avg_score}% | Highest: {highest}% | Avg experience: {avg_exp} yrs.",
    ]

    report_data = {
        "success": True,
        "report_id": report_id,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "job_title": req.job_title,
        "total_candidates": len(req.candidates),
        "avg_match_score": avg_score,
        "highest_score": highest,
        "lowest_score": lowest,
        "highly_recommended_count": len(highly_rec),
        "consider_count": len(consider_rec),
        "avg_experience_years": avg_exp,
        "candidates": [c.dict() for c in req.candidates],
        "next_steps": next_steps,
        "message": f"{len(req.candidates)} candidate(s) successfully submitted to HR for '{req.job_title}'. Report ID: {report_id}.",
        "hr_status": "SUBMITTED"
    }

    if db:
        try:
            db.collection("hr_reports").document(report_id).set(report_data)
            print(f"✅ Saved HR Report {report_id} to Firestore.")
        except Exception as e:
            print(f"❌ Failed to save HR Report to Firestore: {e}")

    return report_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
