import re
import string

# Stop words fallback list in case nltk is not initialized
STOP_WORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
    'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
    'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
    "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
    'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
    'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't",
    'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"
}

# Try loading from NLTK if possible
try:
    import nltk
    from nltk.corpus import stopwords
    # Try downloading if not present, otherwise fallback
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    STOP_WORDS = set(stopwords.words('english'))
except Exception:
    pass

# Skills dictionary across domains
SKILLS_DICT = {
    "Software Engineering": [
        "python", "java", "c++", "typescript", "react", "node.js", "go", "docker", 
        "kubernetes", "aws", "git", "sql", "ci/cd", "microservices", "system design", 
        "rest apis", "redis", "graphql", "nosql", "linux", "html/css", "django"
    ],
    "Data Science & AI": [
        "python", "r", "sql", "tensorflow", "pytorch", "scikit-learn", "pandas", 
        "numpy", "nlp", "bert", "machine learning", "deep learning", "apache spark", 
        "tableau", "data mining", "llms", "computer vision", "statistics", "matplotlib", 
        "hadoop", "data pipelines", "feature engineering"
    ],
    "Product Management": [
        "product roadmap", "agile", "scrum", "jira", "user research", "product analytics", 
        "a/b testing", "sql", "market analysis", "stakeholder management", "figma", 
        "saas", "go-to-market", "prds", "metrics", "kpis", "user personas", 
        "customer discovery", "confluence", "data-driven decisions"
    ],
    "Marketing & Sales": [
        "seo", "sem", "google analytics", "content strategy", "social media marketing", 
        "crm", "hubspot", "copywriting", "email campaigns", "b2b sales", "lead generation", 
        "public relations", "brand management", "market research", "digital advertising", 
        "conversion rate optimization", "salesforce", "content creation"
    ],
    "Finance & Accounting": [
        "financial analysis", "excel (advanced)", "vba", "quickbooks", "gaap", 
        "auditing", "tax planning", "portfolio management", "budgeting", "risk assessment", 
        "valuation", "sql", "sap", "forecasting", "financial modeling", "corporate finance", 
        "general ledger", "balance sheets", "reconciliation"
    ]
}

ALL_SKILLS = []
for cat_skills in SKILLS_DICT.values():
    ALL_SKILLS.extend(cat_skills)
ALL_SKILLS = sorted(list(set(ALL_SKILLS)), key=len, reverse=True)

# Pre-compile regex patterns for performance
SKILL_PATTERNS = []
for skill in ALL_SKILLS:
    escaped_skill = re.escape(skill)
    pattern = r'(?:^|[\s,.\-();/&])' + escaped_skill + r'(?:$|[\s,.\-();/&])'
    SKILL_PATTERNS.append((skill, re.compile(pattern)))

def clean_text(text):
    """
    Cleans raw text by removing punctuation, converting to lowercase, 
    and filtering out stop words.
    """
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Replace newlines/tabs with space
    text = re.sub(r'\s+', ' ', text)
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Tokenize and remove stop words
    words = text.split()
    cleaned_words = [w for w in words if w not in STOP_WORDS]
    
    return " ".join(cleaned_words)

def extract_skills(text):
    """
    Extracts known skills from raw text based on keyword matching with word boundaries.
    """
    if not text:
        return []
    text_lower = text.lower()
    found_skills = []
    
    for skill, compiled_pattern in SKILL_PATTERNS:
        if compiled_pattern.search(text_lower):
            found_skills.append(skill)
            
    # Return formatted list (capitalize appropriate skills for presentation)
    display_map = {}
    for cat, skills in SKILLS_DICT.items():
        for s in skills:
            display_map[s] = s.upper() if len(s) <= 4 else s.title()
            # Special manual mappings
            if s == "c++": display_map[s] = "C++"
            elif s == "react": display_map[s] = "React"
            elif s == "node.js": display_map[s] = "Node.js"
            elif s == "ci/cd": display_map[s] = "CI/CD"
            elif s == "rest apis": display_map[s] = "REST APIs"
            elif s == "nosql": display_map[s] = "NoSQL"
            elif s == "html/css": display_map[s] = "HTML/CSS"
            elif s == "nlp": display_map[s] = "NLP"
            elif s == "bert": display_map[s] = "BERT"
            elif s == "llms": display_map[s] = "LLMs"
            elif s == "saas": display_map[s] = "SaaS"
            elif s == "prds": display_map[s] = "PRDs"
            elif s == "kpis": display_map[s] = "KPIs"
            elif s == "seo": display_map[s] = "SEO"
            elif s == "sem": display_map[s] = "SEM"
            elif s == "crm": display_map[s] = "CRM"
            elif s == "b2b sales": display_map[s] = "B2B Sales"
            elif s == "vba": display_map[s] = "VBA"
            elif s == "gaap": display_map[s] = "GAAP"
            elif s == "sap": display_map[s] = "SAP"
            
    return sorted(list(set(display_map.get(s, s.title()) for s in found_skills)))

def parse_resume_sections(text):
    """
    Rudimentary parser to extract name, email, phone, education, and skills.
    """
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    phone_match = re.search(r'\+?\d[\d\-\(\)\s]{7,}\d', text)
    
    email = email_match.group(0) if email_match else "N/A"
    phone = phone_match.group(0) if phone_match else "N/A"
    
    # Extract name (usually on the first line)
    name = "Candidate"
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        if "name:" in line.lower():
            name = line.split(":", 1)[1].strip()
            break
        elif "contact:" in line.lower() or "objective" in line.lower() or "experience" in line.lower():
            break
        elif len(line) < 30 and not any(k in line.lower() for k in ["email", "phone", "contact", "@"]):
            name = line
            break
            
    # Parse education
    education = "Undergraduate Degree"
    for line in lines:
        if "education" in line.lower():
            idx = lines.index(line)
            if idx + 1 < len(lines):
                education = lines[idx + 1]
            break
        elif "bs in" in line.lower() or "ms in" in line.lower() or "phd in" in line.lower() or "mba" in line.lower():
            education = line
            break
            
    # Try to determine experience years from resume text
    exp_years = 2
    exp_matches = re.findall(r'(\d+)\+?\s*years?', text.lower())
    if exp_matches:
        exp_years = max(int(x) for x in exp_matches if int(x) <= 25)
        
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": extract_skills(text),
        "education": education,
        "experience_years": exp_years
    }
