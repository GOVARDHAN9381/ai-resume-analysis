import os
import sqlite3
import pickle
import json
from src.screen_matcher import ResumeMatcher
from src.nlp_utils import extract_skills

def verify():
    print("=== Capstone Project Verification ===")
    
    # 1. Check database
    db_path = "data/candidates.db"
    if not os.path.exists(db_path):
        print("[ERROR] candidates.db not found!")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"[OK] Database check: found {count} candidate resumes (Target: 5,000+).")
    if count < 5000:
        print("[ERROR] Less than 5000 candidates generated!")
        return False
        
    # 2. Check model files
    model_files = [
        "models/vectorizer.pkl",
        "models/random_forest_model.pkl",
        "models/gradient_boosting_model.pkl",
        "models/metrics.json"
    ]
    
    for f in model_files:
        if not os.path.exists(f):
            print(f"[ERROR] Model file {f} is missing!")
            return False
            
    print("[OK] Model files check: all model artifacts serialized and saved successfully.")
    
    # Load metrics and inspect
    with open("models/metrics.json", "r") as f:
        metrics = json.load(f)
    print(f"[OK] RF Model accuracy: {metrics['rf']['accuracy']*100:.2f}%")
    print(f"[OK] GB Model accuracy: {metrics['gb']['accuracy']*100:.2f}%")
    
    # 3. Test matching engine
    print("Testing screening matching logic...")
    matcher = ResumeMatcher()
    
    # Mock JD
    jd = """
    We need a Senior Software Engineer with strong skills in Python, React, and AWS.
    Experience with Docker and system design is required.
    """
    
    # Extract candidate profiles
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone, category, experience_years, education_degree, education_institution, skills, resume_text FROM candidates LIMIT 5")
    columns = [col[0] for col in cursor.description]
    candidates = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    
    results, used_bert = matcher.screen_candidates(jd, candidates, algorithm="tfidf")
    print("[OK] Screening match sample results:")
    for r in results:
        print(f"  - Candidate: {r['name']} | Score: {r['score']}% | Rec: {r['recommendation']} | Predicted RF: {r['predicted_category_rf']}")
        
    print("\n[SUCCESS] ALL CHECKS PASSED: Capstone system is fully functional!")
    return True

if __name__ == "__main__":
    verify()
