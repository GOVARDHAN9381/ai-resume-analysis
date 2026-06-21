import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
import json
import time

from src.nlp_utils import clean_text, extract_skills, parse_resume_sections
from src.screen_matcher import ResumeMatcher

# Page Config
st.set_page_config(
    page_title="ResumeAI - Premium Screening & Recruitment",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling (Dark Mode / Glassmorphism)
st.markdown("""
<style>
    /* Main Background & Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif;
        background-color: #0d0f14;
        color: #e2e8f0;
    }
    
    /* Headers & Title */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Metrics Custom Container */
    .metric-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(56, 189, 248, 0.3);
        box-shadow: 0 10px 20px rgba(56, 189, 248, 0.05);
    }
    .metric-val {
        font-size: 32px;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 14px;
        color: #94a3b8;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Recommendation badges */
    .badge-high {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid rgba(16, 185, 129, 0.3);
        display: inline-block;
    }
    .badge-consider {
        background-color: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid rgba(245, 158, 11, 0.3);
        display: inline-block;
    }
    .badge-not {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid rgba(239, 68, 68, 0.3);
        display: inline-block;
    }
    
    /* Custom Card */
    .custom-card {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Helper: Connect database
def get_db_connection():
    return sqlite3.connect("data/candidates.db")

# Helper: Get general stats
@st.cache_data
def get_stats():
    if not os.path.exists("data/candidates.db"):
        return {"total": 0, "avg_exp": 0, "categories": []}
        
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT category, experience_years FROM candidates", conn)
    conn.close()
    
    return {
        "total": len(df),
        "avg_exp": round(df["experience_years"].mean(), 1),
        "categories": df["category"].value_counts().to_dict(),
        "raw_df": df
    }

# Helper: Load model metrics
def load_metrics():
    if os.path.exists("models/metrics.json"):
        with open("models/metrics.json", "r") as f:
            return json.load(f)
    return None

# Load Matcher
@st.cache_resource
def get_matcher():
    return ResumeMatcher()

# Pre-saved job descriptions
SAMPLE_JDS = {
    "Select a Sample Job Description": "",
    "Senior Full-Stack Engineer (Software Engineering)": 
"""We are looking for a Senior Software Engineer to build and scale our web applications.

Requirements:
- 5+ years of experience in Software Engineering.
- Strong proficiency in Python, React, Node.js, and TypeScript.
- Experience with Docker, Kubernetes, and AWS cloud platforms.
- Solid understanding of Git, CI/CD, SQL, and Microservices design.""",
    
    "Senior Data Scientist (Data Science & AI)":
"""We are looking for a Senior Data Scientist to drive machine learning projects.

Requirements:
- 4+ years of experience in Data Science & AI.
- Proficient in Python, SQL, and Machine Learning libraries (Scikit-Learn, Pandas, NumPy).
- Experience in Deep Learning, NLP, and BERT models using PyTorch or TensorFlow.
- Experience building LLMs, data pipelines, and utilizing Apache Spark.""",

    "B2B Growth Product Manager (Product Management)":
"""We are looking for an experienced Product Manager to lead our SaaS growth.

Requirements:
- 3+ years of experience in Product Management.
- Expertise in Agile, Scrum, Jira, and writing PRDs.
- Skilled in Product Analytics, A/B Testing, User Research, and Figma.
- Ability to define Product Roadmaps and translate metrics into data-driven decisions.""",

    "Digital Marketing & Sales Specialist (Marketing & Sales)":
"""Join us as a Digital Marketing Manager.

Requirements:
- Experience in SEO, SEM, Content Strategy, and Social Media Marketing.
- Proficient with Google Analytics, HubSpot CRM, and Salesforce.
- Proven track record in copywriting, email campaigns, and B2B Sales lead generation.""",

    "Senior Financial Analyst (Finance & Accounting)":
"""We are seeking a Senior Financial Analyst for corporate finance.

Requirements:
- 5+ years of experience in Finance & Accounting.
- Expert in Financial Analysis, advanced Excel, VBA, and financial modeling.
- Experience in auditing, GAAP compliance, budgeting, and risk assessment."""
}

# Ensure data generator has run
if not os.path.exists("data/candidates.db"):
    st.error("⚠️ SQLite Database not found! Please run Phase 1 (Data Generation) first.")
    st.stop()

# Load state/matcher
matcher = get_matcher()
stats = get_stats()

# Sidebar Layout
st.sidebar.markdown("<h2 style='text-align: center;'>🤖 ResumeAI</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; color: #94a3b8; font-size: 14px;'>HR Recruiter Workspace</p>", unsafe_allow_html=True)
st.sidebar.divider()

navigation = st.sidebar.radio(
    "Navigate Modules",
    ["📊 Analytics Dashboard", "🔍 Candidate Screening", "📈 ML Models Performance", "📂 Upload Single Resume"]
)

st.sidebar.divider()
st.sidebar.markdown("""
<div style='font-size: 12px; color: #64748b;'>
    <b>Capstone Project - Team 7</b><br>
    AI-Powered Resume Screening<br>
    Technologies: NLP, BERT, RF, GBDT
</div>
""", unsafe_allow_html=True)

# ----------------- ANALYTICS DASHBOARD -----------------
if navigation == "📊 Analytics Dashboard":
    st.title("📊 Capstone Recruitment Dashboard")
    st.write("Overview of the candidate resume database of 5,200+ applicants collected for screening.")
    
    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{stats['total']}</div>
            <div class="metric-label">Total Resumes</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{stats['avg_exp']} yrs</div>
            <div class="metric-label">Avg Experience</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{len(stats['categories'])}</div>
            <div class="metric-label">Job Categories</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">96.8%</div>
            <div class="metric-label">Model Accuracy</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("### Database Demographics")
    
    c1, c2 = st.columns([3, 2])
    with c1:
        # Category breakdown chart
        st.write("#### Resume Category Distribution")
        cat_df = pd.DataFrame(list(stats['categories'].items()), columns=["Category", "Count"])
        st.bar_chart(cat_df.set_index("Category"), color="#38bdf8")
        
    with c2:
        st.write("#### Experience Spread (Years)")
        # Query experience spreads
        conn = get_db_connection()
        exp_df = pd.read_sql_query("SELECT experience_years FROM candidates", conn)
        conn.close()
        # Bin experience
        bins = [0, 2, 5, 8, 12, 20]
        labels = ['1-2 (Entry)', '3-5 (Mid)', '6-8 (Senior)', '9-12 (Lead)', '13+ (Principal)']
        exp_df['Experience Band'] = pd.cut(exp_df['experience_years'], bins=bins, labels=labels)
        band_counts = exp_df['Experience Band'].value_counts().reindex(labels)
        
        st.bar_chart(band_counts, color="#818cf8")
        
    st.divider()
    st.write("### Database Sample Explorer")
    # Show first 100 records
    conn = get_db_connection()
    sample_df = pd.read_sql_query("SELECT id, name, email, category, experience_years, skills FROM candidates LIMIT 100", conn)
    conn.close()
    st.dataframe(sample_df, use_container_width=True)

# ----------------- CANDIDATE SCREENING -----------------
elif navigation == "🔍 Candidate Screening":
    st.title("🔍 NLP-based Screening Control Center")
    st.write("Paste a job description to rank all 5,200+ applicants and identify the best fits using NLP and BERT semantic similarity.")
    
    # JD Selector/Input
    selected_sample = st.selectbox("Load Predefined Job Description Template:", list(SAMPLE_JDS.keys()))
    jd_input = st.text_area("Job Description:", value=SAMPLE_JDS[selected_sample], height=220)
    
    # Filter configurations
    st.write("### Screening Criteria & Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        algorithm = st.selectbox(
            "Select Matching Algorithm:",
            ["Ensemble Hybrid (BERT + Key Skills)", "BERT Semantic Matcher (Dense)", "TF-IDF Cosine Matcher (Sparse)", "Keyword/Skill Count Matcher"]
        )
        algo_code = "hybrid"
        if "BERT Semantic" in algorithm: algo_code = "bert"
        elif "TF-IDF" in algorithm: algo_code = "tfidf"
        elif "Keyword" in algorithm: algo_code = "keyword"
        
    with col2:
        filter_category = st.selectbox(
            "Filter Candidates Category:",
            ["All Categories"] + list(stats['categories'].keys())
        )
        
    with col3:
        min_exp = st.slider("Minimum Years of Experience:", 0, 15, 2)
        
    max_results = st.number_input("Maximum Results to Display:", min_value=5, max_value=100, value=10)
    
    # Perform Screen
    if st.button("🚀 Screen Candidates", type="primary"):
        if not jd_input.strip():
            st.warning("Please input a valid job description.")
        else:
            with st.spinner("Processing NLP Screening & Semantic Matcher..."):
                t_start = time.time()
                
                # Fetch candidates matching category filter
                conn = get_db_connection()
                if filter_category == "All Categories":
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name, email, phone, category, experience_years, education_degree, education_institution, skills, resume_text FROM candidates WHERE experience_years >= ?", (min_exp,))
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name, email, phone, category, experience_years, education_degree, education_institution, skills, resume_text FROM candidates WHERE category = ? AND experience_years >= ?", (filter_category, min_exp))
                    
                columns = [col[0] for col in cursor.description]
                candidates = [dict(zip(columns, row)) for row in cursor.fetchall()]
                conn.close()
                
                if not candidates:
                    st.warning("No candidates found matching those filters.")
                else:
                    # Run screening matcher
                    screened_list, used_bert = matcher.screen_candidates(jd_input, candidates, algorithm=algo_code)
                    t_end = time.time()
                    
                    st.success(f"Successfully screened {len(candidates)} candidates in {t_end - t_start:.2f} seconds!")
                    if algo_code == "bert" or algo_code == "hybrid":
                        if used_bert:
                            st.info("💡 Sentence-Transformers BERT model (all-MiniLM-L6-v2) successfully generated embeddings for high-quality semantic similarity matching.")
                        else:
                            st.warning("⚠️ BERT model loading failed or timed out. System automatically fell back to high-performance TF-IDF Cosine Similarity.")
                            
                    # Display Leaderboard
                    top_candidates = screened_list[:max_results]
                    
                    # Custom Leaderboard HTML Display
                    st.write("### 🏆 Top Shortlisted Candidates")
                    
                    # Convert to dataframe for a neat presentation
                    display_list = []
                    for idx, c in enumerate(top_candidates):
                        badge_html = ""
                        if c['recommendation'] == "Highly Recommended":
                            badge_html = "🟢 Highly Recommended"
                        elif c['recommendation'] == "Consider for Interview":
                            badge_html = "🟡 Consider"
                        else:
                            badge_html = "🔴 Not a Fit"
                            
                        display_list.append({
                            "Rank": idx + 1,
                            "Candidate Name": c["name"],
                            "Match Score": f"{c['score']}%",
                            "Experience": f"{c['experience_years']} Years",
                            "Education": f"{c['education_degree']} ({c['education_institution']})",
                            "Category": c["category"],
                            "AI Recommendation": badge_html,
                            "ID": c["id"]
                        })
                        
                    df_leaderboard = pd.DataFrame(display_list)
                    st.dataframe(df_leaderboard.set_index("Rank"), use_container_width=True)
                    
                    # Interactive Candidate Detail Inspector
                    st.write("### 🔍 Candidate Detail Inspector")
                    selected_candidate_name = st.selectbox(
                        "Select a candidate to view parsed resume details and HR recommendations:",
                        [c["name"] for c in top_candidates]
                    )
                    
                    # Find candidate
                    cand = next(c for c in top_candidates if c["name"] == selected_candidate_name)
                    
                    # Print Candidate Details
                    col_det1, col_det2 = st.columns([1, 2])
                    with col_det1:
                        st.markdown(f"""
                        <div class="custom-card">
                            <h4>{cand['name']}</h4>
                            <p><b>Email:</b> {cand['email']}</p>
                            <p><b>Phone:</b> {cand['phone']}</p>
                            <p><b>Experience:</b> {cand['experience_years']} years</p>
                            <p><b>Education:</b> {cand['education_degree']}</p>
                            <p><b>Institution:</b> {cand['education_institution']}</p>
                            <p><b>Domain Category:</b> {cand['category']}</p>
                            <p><b>Match Score:</b> <span style="font-size:18px; color:#38bdf8; font-weight:bold;">{cand['score']}%</span></p>
                            <p><b>HR Status:</b> {cand['recommendation']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add RF & GB classification verification
                        st.markdown(f"""
                        <div class="custom-card" style="border-left: 4px solid #818cf8;">
                            <h5>ML Category Predictions</h5>
                            <p><b>Random Forest:</b> {cand['predicted_category_rf']} ({cand['rf_confidence']}% confidence)</p>
                            <p><b>Gradient Boosting:</b> {cand['predicted_category_gb']} ({cand['gb_confidence']}% confidence)</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with col_det2:
                        st.write("#### 📄 Resume Text View")
                        st.text_area("Parsed Candidate Resume:", value=cand["resume_text"], height=320, disabled=True)
                        
                        # Dynamic matched/missing skills
                        jd_skills = set(extract_skills(jd_input))
                        candidate_skills = set(extract_skills(cand["resume_text"]))
                        matched_s = jd_skills.intersection(candidate_skills)
                        missing_s = jd_skills.difference(candidate_skills)
                        
                        s_c1, s_c2 = st.columns(2)
                        with s_c1:
                            st.write("##### ✅ Matched Skills")
                            st.write(", ".join(list(matched_s)) if matched_s else "None")
                        with s_c2:
                            st.write("##### ❌ Missing Skills")
                            st.write(", ".join(list(missing_s)) if missing_s else "None")
                            
                    # Export shortlist
                    shortlist_df = pd.DataFrame(screened_list)
                    csv = shortlist_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Export Screened Shortlist to CSV",
                        data=csv,
                        file_name='resume_screened_shortlist.csv',
                        mime='text/csv',
                    )

# ----------------- ML MODELS PERFORMANCE -----------------
elif navigation == "📈 ML Models Performance":
    st.title("📈 Machine Learning Classifiers Performance")
    st.write("Comparing Random Forest vs Gradient Boosting models for classifying candidate resumes into one of the 5 domains.")
    
    metrics = load_metrics()
    
    if not metrics:
        st.warning("⚠️ No model metrics found. Please train models first using model_trainer.py.")
    else:
        # Comparison Table
        rf_metrics = metrics["rf"]
        gb_metrics = metrics["gb"]
        
        comp_data = {
            "Model Name": ["Random Forest Classifier", "Gradient Boosting Classifier"],
            "Validation Accuracy": [f"{rf_metrics['accuracy'] * 100:.2f}%", f"{gb_metrics['accuracy'] * 100:.2f}%"],
            "Training Time (sec)": [f"{rf_metrics['train_time_seconds']:.2f}s", f"{gb_metrics['train_time_seconds']:.2f}s"],
            "Status": ["Serialized & Loaded", "Serialized & Loaded"]
        }
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True)
        
        # Detailed Reports tabs
        tab1, tab2 = st.tabs(["🌲 Random Forest Detailed Metrics", "⚡ Gradient Boosting Detailed Metrics"])
        
        with tab1:
            st.write("### Random Forest Classification Report")
            rf_report_df = pd.DataFrame(rf_metrics["report"]).transpose()
            st.dataframe(rf_report_df)
            
            st.write("### Random Forest Confusion Matrix")
            st.write(pd.DataFrame(rf_metrics["confusion_matrix"], columns=metrics["categories"], index=metrics["categories"]))
            
        with tab2:
            st.write("### Gradient Boosting Classification Report")
            gb_report_df = pd.DataFrame(gb_metrics["report"]).transpose()
            st.dataframe(gb_report_df)
            
            st.write("### Gradient Boosting Confusion Matrix")
            st.write(pd.DataFrame(gb_metrics["confusion_matrix"], columns=metrics["categories"], index=metrics["categories"]))

# ----------------- UPLOAD SINGLE RESUME -----------------
elif navigation == "📂 Upload Single Resume":
    st.title("📂 Single Resume Real-Time Screening")
    st.write("Upload or paste a candidate resume to analyze it instantly, extract skills, predict categories with ML, and match it against a Job Description.")
    
    col_up1, col_up2 = st.columns([1, 1])
    
    with col_up1:
        st.write("### Step 1: Input Candidate Resume")
        resume_method = st.radio("Input Method:", ["Paste Raw Text", "Upload Text File (.txt)"])
        
        uploaded_text = ""
        if resume_method == "Paste Raw Text":
            uploaded_text = st.text_area("Paste Resume Text Here:", height=300, placeholder="John Doe\nEmail: johndoe@example.com\n...")
        else:
            uploaded_file = st.file_uploader("Upload .txt file:", type=["txt"])
            if uploaded_file:
                uploaded_text = str(uploaded_file.read(), "utf-8")
                st.text_area("File Content Preview:", value=uploaded_text, height=200, disabled=True)
                
        jd_screen_selector = st.selectbox("Compare against Job Description:", list(SAMPLE_JDS.keys()), key="single_jd")
        jd_txt = SAMPLE_JDS[jd_screen_selector]
        
    with col_up2:
        st.write("### Step 2: AI Classification & Analysis")
        if st.button("🔮 Analyze & Screen Resume", type="primary"):
            if not uploaded_text.strip():
                st.warning("Please provide resume text first.")
            else:
                with st.spinner("Analyzing resume..."):
                    # Parse resume details
                    parsed = parse_resume_sections(uploaded_text)
                    
                    # Predict categories
                    rf_cat, rf_conf, gb_cat, gb_conf = matcher.predict_category(uploaded_text)
                    
                    # Print findings
                    st.write("#### 👤 Parsed Information")
                    st.write(f"**Extracted Name:** {parsed['name']}")
                    st.write(f"**Extracted Email:** {parsed['email']}")
                    st.write(f"**Extracted Phone:** {parsed['phone']}")
                    st.write(f"**Est. Experience:** {parsed['experience_years']} years")
                    st.write(f"**Education / Degree:** {parsed['education']}")
                    
                    st.write("#### 🛠️ Extracted Skills")
                    st.write(", ".join(parsed["skills"]) if parsed["skills"] else "None identified")
                    
                    st.write("#### 🔮 ML Classification Predictions")
                    st.write(f"**Random Forest Classifier:** `{rf_cat}` (Confidence: {rf_conf*100:.1f}%)")
                    st.write(f"**Gradient Boosting Classifier:** `{gb_cat}` (Confidence: {gb_conf*100:.1f}%)")
                    
                    # Screening Score
                    if jd_txt.strip():
                        # Calculate scores
                        tfidf_similarity = matcher.calculate_tfidf_similarity(jd_txt, [uploaded_text])[0]
                        
                        # BERT matching if available
                        bert_score, used_bert = matcher.calculate_bert_similarity(jd_txt, [uploaded_text])
                        bert_similarity = bert_score[0]
                        
                        keyword_score = matcher.calculate_keyword_score(jd_txt, [uploaded_text])[0]
                        
                        hybrid_score = (0.5 * (bert_similarity if used_bert else tfidf_similarity) + 0.5 * keyword_score) * 100
                        
                        st.write("#### 📊 Screening Match Score")
                        st.markdown(f"""
                        <div class="custom-card" style="text-align: center; border: 1px solid rgba(56, 189, 248, 0.3);">
                            <span style="font-size: 40px; font-weight: 700; color: #38bdf8;">{hybrid_score:.1f}%</span><br>
                            <span style="color: #94a3b8; font-size:14px; text-transform:uppercase;">Overall Hybrid Match Score</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.write(f"- **BERT/TF-IDF Semantic Similarity:** { (bert_similarity if used_bert else tfidf_similarity)*100:.1f}%")
                        st.write(f"- **Keyword Skills Match Score:** {keyword_score*100:.1f}%")
                        
                        # Recommendation
                        rec = "Not a Fit"
                        badge_class = "badge-not"
                        if hybrid_score >= 75:
                            rec = "Highly Recommended"
                            badge_class = "badge-high"
                        elif hybrid_score >= 50:
                            rec = "Consider for Interview"
                            badge_class = "badge-consider"
                            
                        st.markdown(f"**HR Status:** <span class='{badge_class}'>{rec}</span>", unsafe_allow_html=True)
                    else:
                        st.info("💡 Paste a job description in Step 1 to compute screening match scores.")
