"""
prepare_datasets.py
===================
Converts both raw dataset sources into upload-ready CSVs for ResumeAI.

Dataset 1: data/candidates_dataset.csv  (synthetically generated - already in correct format)
Dataset 2: dataset_1_resumes_5k.csv     (HuggingFace raw LLM format - needs JSON extraction)

Output files (ready to upload via the UI):
  upload_dataset1_synthetic.csv   — 5,200 synthetic candidates
  upload_dataset2_huggingface.csv — parsed real-world resumes
  upload_combined.csv             — both merged together
"""

import pandas as pd
import json
import re
import os
import random

random.seed(42)

# ──────────────────────────────────────────────────────────────────────────────
# DATASET 1: Synthetic (already structured — just clean & export)
# ──────────────────────────────────────────────────────────────────────────────

def prepare_dataset1():
    print("\n" + "="*60)
    print("DATASET 1: Synthetic Candidates (data/candidates_dataset.csv)")
    print("="*60)

    src = "data/candidates_dataset.csv"
    if not os.path.exists(src):
        print(f"  ❌ File not found: {src}")
        print("  → Run: python src/data_generator.py  to generate it first.")
        return None

    df = pd.read_csv(src)
    print(f"  ✅ Loaded {len(df):,} rows  |  Columns: {list(df.columns)}")

    # Ensure all required columns are present
    required = ["name", "email", "resume_text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  ❌ Missing required columns: {missing}")
        return None

    # Fill optional nulls
    df["phone"] = df.get("phone", "N/A").fillna("N/A")
    df["category"] = df.get("category", "General").fillna("General")
    df["experience_years"] = pd.to_numeric(df.get("experience_years", 0), errors="coerce").fillna(0).astype(int)
    df["education_degree"] = df.get("education_degree", "Not Specified").fillna("Not Specified")
    df["education_institution"] = df.get("education_institution", "Not Specified").fillna("Not Specified")
    df["skills"] = df.get("skills", "").fillna("")

    # Keep only the columns the app expects
    out_cols = ["name", "email", "phone", "category", "experience_years",
                "education_degree", "education_institution", "skills", "resume_text"]
    df_out = df[[c for c in out_cols if c in df.columns]]

    out_path = "upload_dataset1_synthetic.csv"
    df_out.to_csv(out_path, index=False)
    print(f"  ✅ Saved → {out_path}  ({len(df_out):,} candidates)")
    return df_out


# ──────────────────────────────────────────────────────────────────────────────
# DATASET 2: HuggingFace raw (dataset_1_resumes_5k.csv) — extract JSON + text
# ──────────────────────────────────────────────────────────────────────────────

def _extract_resume_text(raw: str) -> str:
    """Extract the raw resume text from the <|im_start|>user block."""
    try:
        match = re.search(r'<\|im_start\|>user\nResume:\n(.*?)<\|im_end\|>', raw, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return ""


def _extract_json_metadata(raw: str) -> dict:
    """Extract the JSON object from the <|im_start|>assistant block."""
    try:
        match = re.search(r'<\|im_start\|>assistant\n.*?(\{.*?\})\s*<\|im_end\|>', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass
    return {}


def _extract_email(text: str) -> str:
    m = re.search(r'[\w.\-]+@[\w.\-]+\.\w+', text)
    return m.group(0) if m else ""


def _extract_phone(text: str) -> str:
    m = re.search(r'(\+?\d[\d\s\-().]{7,}\d)', text)
    return m.group(0).strip() if m else "N/A"


def _infer_category(meta: dict, resume_text: str) -> str:
    """Map primary_domain from metadata to one of our 5 categories."""
    domain_map = {
        "software": "Software Engineering",
        "engineer": "Software Engineering",
        "developer": "Software Engineering",
        "it ": "Software Engineering",
        "data": "Data Science & AI",
        "machine learning": "Data Science & AI",
        "ai": "Data Science & AI",
        "analytics": "Data Science & AI",
        "product": "Product Management",
        "marketing": "Marketing & Sales",
        "sales": "Marketing & Sales",
        "finance": "Finance & Accounting",
        "accounting": "Finance & Accounting",
        "financial": "Finance & Accounting",
        "audit": "Finance & Accounting",
    }
    domain = (meta.get("primary_domain") or "").lower()
    resume_lower = resume_text[:500].lower()

    for key, cat in domain_map.items():
        if key in domain:
            return cat

    # Fallback: scan resume text
    for key, cat in domain_map.items():
        if key in resume_lower:
            return cat

    return "General"


FAKE_FIRSTNAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Drew",
                   "Avery", "Quinn", "Reese", "Blake", "Cameron", "Dana", "Lee", "Pat"]
FAKE_LASTNAMES = ["Smith", "Johnson", "Williams", "Brown", "Davis", "Wilson", "Moore",
                  "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Garcia"]


def _generate_fake_email(name: str, idx: int) -> str:
    parts = name.lower().split()
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[-1]}{idx}@example.com"
    return f"candidate{idx}@example.com"


def prepare_dataset2():
    print("\n" + "="*60)
    print("DATASET 2: HuggingFace Resumes (dataset_1_resumes_5k.csv)")
    print("="*60)

    src = "dataset_1_resumes_5k.csv"
    if not os.path.exists(src):
        print(f"  ❌ File not found: {src}")
        print("  → Run: python download_datasets.py  to download it first.")
        return None

    # The file has a single unnamed column with the raw LLM conversation
    raw_df = pd.read_csv(src, header=None, names=["raw"])
    print(f"  📄 Loaded {len(raw_df):,} raw rows — extracting structured data...")

    records = []
    skipped = 0

    for idx, row in raw_df.iterrows():
        raw = str(row["raw"])

        resume_text = _extract_resume_text(raw)
        if not resume_text or len(resume_text) < 100:
            skipped += 1
            continue

        meta = _extract_json_metadata(raw)

        # Build name
        name = ""
        if meta.get("current_title"):
            # Use a fake name since resume has no real name in this dataset
            fname = random.choice(FAKE_FIRSTNAMES)
            lname = random.choice(FAKE_LASTNAMES)
            name = f"{fname} {lname}"
        if not name:
            name = f"{random.choice(FAKE_FIRSTNAMES)} {random.choice(FAKE_LASTNAMES)}"

        email = _extract_email(resume_text)
        if not email:
            email = _generate_fake_email(name, idx)

        phone = _extract_phone(resume_text)
        category = _infer_category(meta, resume_text)

        exp_years = meta.get("years_experience", 0)
        try:
            exp_years = int(exp_years) if exp_years else 0
        except (ValueError, TypeError):
            exp_years = 0

        # Skills from metadata
        skills_list = []
        if meta.get("core_skills"):
            skills_list += meta["core_skills"]
        if meta.get("secondary_skills"):
            skills_list += meta["secondary_skills"]
        if meta.get("tools"):
            tools = meta["tools"]
            if isinstance(tools, list):
                skills_list += tools
            elif isinstance(tools, str):
                skills_list.append(tools)
        skills = ", ".join(skills_list[:12]) if skills_list else ""

        # Education — try to extract from resume text
        edu_match = re.search(
            r'(Bachelor|Master|PhD|B\.S\.|M\.S\.|MBA|B\.A\.|M\.A\.|Associate)[^\n]{0,80}',
            resume_text, re.IGNORECASE
        )
        education_degree = edu_match.group(0).strip()[:80] if edu_match else "Not Specified"

        # Institution — look for "University", "College", "Institute" near education line
        inst_match = re.search(
            r'([\w\s]+(?:University|College|Institute|School)[^\n]{0,40})',
            resume_text, re.IGNORECASE
        )
        education_institution = inst_match.group(0).strip()[:80] if inst_match else "Not Specified"

        records.append({
            "name": name,
            "email": email,
            "phone": phone,
            "category": category,
            "experience_years": exp_years,
            "education_degree": education_degree,
            "education_institution": education_institution,
            "skills": skills,
            "resume_text": resume_text[:4000],  # cap at 4000 chars for upload speed
        })

        if (idx + 1) % 500 == 0:
            print(f"    Processed {idx + 1:,} rows...")

    print(f"  ✅ Extracted {len(records):,} valid resumes  |  Skipped {skipped:,} malformed rows")

    if not records:
        print("  ❌ No records extracted. Check the raw file format.")
        return None

    df_out = pd.DataFrame(records)
    out_path = "upload_dataset2_huggingface.csv"
    df_out.to_csv(out_path, index=False)
    print(f"  ✅ Saved → {out_path}  ({len(df_out):,} candidates)")
    return df_out


# ──────────────────────────────────────────────────────────────────────────────
# COMBINE BOTH
# ──────────────────────────────────────────────────────────────────────────────

def combine(df1, df2):
    print("\n" + "="*60)
    print("COMBINED DATASET")
    print("="*60)

    frames = [f for f in [df1, df2] if f is not None]
    if not frames:
        print("  ❌ No datasets to combine.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["email"]).reset_index(drop=True)

    out_path = "upload_combined.csv"
    combined.to_csv(out_path, index=False)
    print(f"  ✅ Saved → {out_path}  ({len(combined):,} total unique candidates)")
    print(f"\n  Category breakdown:")
    print(combined["category"].value_counts().to_string())


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀 ResumeAI — Dataset Preparation Script")
    print("   Preparing upload-ready CSVs for your project...\n")

    df1 = prepare_dataset1()
    df2 = prepare_dataset2()
    combine(df1, df2)

    print("\n" + "="*60)
    print("✅ DONE! Upload these files via the app UI:")
    print()
    if os.path.exists("upload_dataset1_synthetic.csv"):
        print("  📄 upload_dataset1_synthetic.csv  — 5,200 synthetic candidates")
    if os.path.exists("upload_dataset2_huggingface.csv"):
        print("  📄 upload_dataset2_huggingface.csv — real-world parsed resumes")
    if os.path.exists("upload_combined.csv"):
        print("  📄 upload_combined.csv             — both datasets merged")
    print()
    print("  Go to your app → 'Upload Dataset' → choose any of the above files.")
    print("="*60)
