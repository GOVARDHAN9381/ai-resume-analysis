-- Schema creation for ResumeAI Supabase migration

-- 1. candidates table
CREATE TABLE IF NOT EXISTS candidates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    category TEXT,
    experience_years INTEGER,
    education_degree TEXT,
    education_institution TEXT,
    skills TEXT,
    resume_text TEXT
);

-- 2. screening_history table
CREATE TABLE IF NOT EXISTS screening_history (
    id TEXT PRIMARY KEY,
    job_description TEXT,
    filters JSONB,
    total_screened INTEGER,
    top_candidates JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. resume_analyses table
CREATE TABLE IF NOT EXISTS resume_analyses (
    id TEXT PRIMARY KEY,
    parsed JSONB,
    category TEXT,
    match_scores JSONB,
    recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. ats_scores table
CREATE TABLE IF NOT EXISTS ats_scores (
    id TEXT PRIMARY KEY,
    score_percentage NUMERIC,
    grade TEXT,
    job_description_provided BOOLEAN,
    breakdown_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. interview_questions table
CREATE TABLE IF NOT EXISTS interview_questions (
    id TEXT PRIMARY KEY,
    skills_analyzed INTEGER,
    total_questions INTEGER,
    categories JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. fraud_reports table
CREATE TABLE IF NOT EXISTS fraud_reports (
    id TEXT PRIMARY KEY,
    risk_score NUMERIC,
    risk_level TEXT,
    flags_count INTEGER,
    flags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. job_recommendations table
CREATE TABLE IF NOT EXISTS job_recommendations (
    id TEXT PRIMARY KEY,
    candidate_category TEXT,
    experience_years INTEGER,
    top_recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. hr_reports table
CREATE TABLE IF NOT EXISTS hr_reports (
    report_id TEXT PRIMARY KEY,
    success BOOLEAN,
    submitted_at TEXT,
    job_title TEXT,
    total_candidates INTEGER,
    avg_match_score NUMERIC,
    highest_score NUMERIC,
    lowest_score NUMERIC,
    highly_recommended_count INTEGER,
    consider_count INTEGER,
    avg_experience_years NUMERIC,
    candidates JSONB,
    next_steps JSONB,
    message TEXT,
    hr_status TEXT
);
