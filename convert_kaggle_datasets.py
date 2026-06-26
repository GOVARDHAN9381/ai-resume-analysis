"""
convert_kaggle_datasets.py
Converts both downloaded Kaggle datasets into upload-ready CSVs for ResumeAI.

Output:
  data/kaggle/upload_dataset1_kaggle_resumes.csv   — 2,484 real resumes (25 categories)
  data/kaggle/upload_dataset2_screening.csv        — 30,000 AI screening records
"""

import pandas as pd
import random
import re

random.seed(42)

FIRSTNAMES = [
    'James','Mary','John','Patricia','Robert','Jennifer','Michael','Linda',
    'William','Elizabeth','David','Barbara','Richard','Susan','Joseph','Jessica',
    'Priya','Arjun','Rahul','Ananya','Vikram','Sneha','Ravi','Pooja',
    'Alex','Jordan','Taylor','Morgan','Casey','Riley','Jamie','Drew'
]
LASTNAMES = [
    'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis',
    'Wilson','Anderson','Thomas','Taylor','Moore','Jackson','White','Harris',
    'Sharma','Patel','Kumar','Singh','Gupta','Reddy','Nair','Iyer',
    'Lopez','Nguyen','Lee','Kim','Chen','Wang','Zhang'
]

CAT_MAP = {
    'INFORMATION-TECHNOLOGY': 'Software Engineering',
    'INFORMATION TECHNOLOGY': 'Software Engineering',
    'IT': 'Software Engineering',
    'DATA-SCIENCE': 'Data Science & AI',
    'DATA SCIENCE': 'Data Science & AI',
    'DATASCIENCE': 'Data Science & AI',
    'FINANCE': 'Finance & Accounting',
    'ACCOUNTANT': 'Finance & Accounting',
    'BANKING': 'Finance & Accounting',
    'MARKETING': 'Marketing & Sales',
    'SALES': 'Marketing & Sales',
    'DIGITAL-MEDIA': 'Marketing & Sales',
    'PUBLIC-RELATIONS': 'Marketing & Sales',
    'BUSINESS-DEVELOPMENT': 'Product Management',
    'CONSULTANT': 'Product Management',
    'ENGINEERING': 'Software Engineering',
}

EDU_MAP = {
    'Bachelors': 'Bachelor of Science',
    'Masters': 'Master of Science',
    'PhD': 'PhD',
    'Associate': 'Associate Degree',
    'High School': 'High School Diploma',
}

SKILL_KWS = [
    'python','java','sql','r','excel','machine learning','deep learning','nlp',
    'tensorflow','pytorch','aws','docker','react','node.js','javascript','tableau',
    'power bi','hadoop','spark','kubernetes','c++','c#','git','agile','scrum',
    'sap','quickbooks','gaap','figma','photoshop','google analytics','seo','crm',
    'salesforce','hubspot','linux','mongodb','postgresql','flask','django','fastapi'
]


def fake_name():
    return f"{random.choice(FIRSTNAMES)} {random.choice(LASTNAMES)}"


def fake_email(name, idx):
    parts = name.lower().split()
    return f"{parts[0]}.{parts[-1]}{idx}@example.com"


def fake_phone():
    return f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"


def extract_email(text):
    m = re.search(r'[\w.\-]+@[\w.\-]+\.\w+', str(text))
    return m.group(0) if m else ''


def extract_phone(text):
    m = re.search(r'(\+?[\d][\d\s\-().]{7,}\d)', str(text))
    return m.group(0).strip() if m else 'N/A'


def extract_skills(text):
    found = [s for s in SKILL_KWS if s in text.lower()]
    return ', '.join(found[:10])


def extract_exp(text):
    m = re.search(r'(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)', text, re.IGNORECASE)
    return int(m.group(1)) if m else random.randint(1, 12)


def extract_edu(text):
    m = re.search(
        r'(Bachelor|Master|PhD|B\.S\.|M\.S\.|MBA|B\.A\.|M\.A\.|Associate)[^\n]{0,80}',
        text, re.IGNORECASE
    )
    return m.group(0).strip()[:80] if m else 'Not Specified'


def extract_inst(text):
    m = re.search(
        r'([\w\s]+(?:University|College|Institute|School)[^\n]{0,40})',
        text, re.IGNORECASE
    )
    return m.group(0).strip()[:80] if m else 'Not Specified'


def map_category(raw):
    key = raw.upper().replace(' ', '-')
    return CAT_MAP.get(key, CAT_MAP.get(raw.upper(), 'General'))


# ─────────────────────────────────────────────────────────────────────────────
# Dataset 1 — Kaggle Resume Dataset (2,484 real resumes, 25 categories)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("Dataset 1: Kaggle Resume Dataset (snehaanbhawal/resume-dataset)")
print("=" * 60)

df1 = pd.read_csv(r'data/kaggle/dataset1/Resume/Resume.csv')
print(f"  Loaded {len(df1)} rows | Columns: {list(df1.columns)}")

records1 = []
for idx, row in df1.iterrows():
    text = str(row['Resume_str'])
    name = fake_name()
    email_found = extract_email(text)
    email = email_found if email_found else fake_email(name, idx)

    records1.append({
        'name': name,
        'email': email,
        'phone': extract_phone(text),
        'category': map_category(str(row['Category'])),
        'experience_years': extract_exp(text),
        'education_degree': extract_edu(text),
        'education_institution': extract_inst(text),
        'skills': extract_skills(text),
        'resume_text': text[:4000],
    })

out1 = pd.DataFrame(records1)
out1.to_csv('data/kaggle/upload_dataset1_kaggle_resumes.csv', index=False)
print(f"  Saved {len(out1)} rows -> data/kaggle/upload_dataset1_kaggle_resumes.csv")
print("  Category breakdown:")
print(out1['category'].value_counts().to_string())


# ─────────────────────────────────────────────────────────────────────────────
# Dataset 2 — AI Screening Dataset (30,000 structured records)
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("Dataset 2: AI-Driven Resume Screening (sonalshinde123)")
print("=" * 60)

df2 = pd.read_csv(r'data/kaggle/dataset2/ai_resume_screening.csv')
print(f"  Loaded {len(df2)} rows | Columns: {list(df2.columns)}")

records2 = []
for idx, row in df2.iterrows():
    name = fake_name()
    email = fake_email(name, idx + 10000)
    edu_raw = str(row.get('education_level', ''))
    edu = EDU_MAP.get(edu_raw, edu_raw)
    exp = int(row.get('years_experience', random.randint(1, 10)))
    skill_score = row.get('skills_match_score', 'N/A')
    projects = row.get('project_count', 0)
    github = row.get('github_activity', 0)
    shortlisted = row.get('shortlisted', 'No')

    resume_text = (
        f"Candidate Profile\n\n"
        f"Experience: {exp} years of professional experience.\n"
        f"Education: {edu}.\n"
        f"Skills Match Score: {skill_score}%.\n"
        f"Projects Completed: {projects}.\n"
        f"GitHub Activity Score: {github}.\n"
        f"Shortlisting Status: {shortlisted}.\n"
    )

    records2.append({
        'name': name,
        'email': email,
        'phone': fake_phone(),
        'category': 'General',
        'experience_years': exp,
        'education_degree': edu,
        'education_institution': 'Not Specified',
        'skills': '',
        'resume_text': resume_text,
    })

out2 = pd.DataFrame(records2)
out2.to_csv('data/kaggle/upload_dataset2_screening.csv', index=False)
print(f"  Saved {len(out2)} rows -> data/kaggle/upload_dataset2_screening.csv")

print()
print("=" * 60)
print("DONE! Ready-to-upload files:")
print("  data/kaggle/upload_dataset1_kaggle_resumes.csv  (2,484 real resumes)")
print("  data/kaggle/upload_dataset2_screening.csv       (30,000 screening records)")
print()
print("Upload via your app UI: Upload Dataset tab -> choose either file above.")
print("=" * 60)
