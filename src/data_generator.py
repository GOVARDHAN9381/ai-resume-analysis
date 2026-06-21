import os
import sqlite3
import random

# Seed for reproducibility
random.seed(42)

# Define categories and skill pools
CATEGORIES = [
    "Software Engineering",
    "Data Science & AI",
    "Product Management",
    "Marketing & Sales",
    "Finance & Accounting"
]

SKILLS_POOL = {
    "Software Engineering": [
        "Python", "Java", "C++", "TypeScript", "React", "Node.js", "Go", "Docker", 
        "Kubernetes", "AWS", "Git", "SQL", "CI/CD", "Microservices", "System Design", 
        "REST APIs", "Redis", "GraphQL", "NoSQL", "Linux", "HTML/CSS", "Django"
    ],
    "Data Science & AI": [
        "Python", "R", "SQL", "TensorFlow", "PyTorch", "Scikit-Learn", "Pandas", 
        "NumPy", "NLP", "BERT", "Machine Learning", "Deep Learning", "Apache Spark", 
        "Tableau", "Data Mining", "LLMs", "Computer Vision", "Statistics", "Matplotlib", 
        "Hadoop", "Data Pipelines", "Feature Engineering"
    ],
    "Product Management": [
        "Product Roadmap", "Agile", "Scrum", "Jira", "User Research", "Product Analytics", 
        "A/B Testing", "SQL", "Market Analysis", "Stakeholder Management", "Figma", 
        "SaaS", "Go-to-Market", "PRDs", "Metrics", "KPIs", "User Personas", 
        "Customer Discovery", "Confluence", "Data-driven Decisions"
    ],
    "Marketing & Sales": [
        "SEO", "SEM", "Google Analytics", "Content Strategy", "Social Media Marketing", 
        "CRM", "HubSpot", "Copywriting", "Email Campaigns", "B2B Sales", "Lead Generation", 
        "Public Relations", "Brand Management", "Market Research", "Digital Advertising", 
        "Conversion Rate Optimization", "Salesforce", "Content Creation"
    ],
    "Finance & Accounting": [
        "Financial Analysis", "Excel (Advanced)", "VBA", "QuickBooks", "GAAP", 
        "Auditing", "Tax Planning", "Portfolio Management", "Budgeting", "Risk Assessment", 
        "Valuation", "SQL", "SAP", "Forecasting", "Financial Modeling", "Corporate Finance", 
        "General Ledger", "Balance Sheets", "Reconciliation"
    ]
}

# Names database
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", 
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa", 
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley", 
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle", 
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", 
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon", 
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy", 
    "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna", 
    "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma", 
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Alexander", 
    "Debra", "Frank", "Rachel", "Patrick", "Carolyn", "Raymond", "Janet", "Jack", "Maria"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", 
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", 
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", 
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", 
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", 
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", 
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy", 
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey"
]

UNIVERSITIES = [
    "MIT", "Stanford University", "UC Berkeley", "Carnegie Mellon University", 
    "Harvard University", "University of Toronto", "Oxford University", 
    "IIT Bombay", "National University of Singapore", "ETH Zurich", 
    "Boston University", "New York University", "Georgia Tech", 
    "University of Michigan", "UT Austin", "Cornell University"
]

DEGREES = {
    "Bachelor": ["BS in Computer Science", "BS in Data Science", "BBA in Finance", "BS in Marketing", "BBA in Business", "BS in Information Technology"],
    "Master": ["MS in Computer Science", "MS in Data Science & Analytics", "MBA", "MS in Finance", "MS in Marketing Analytics", "MS in Software Engineering"],
    "PhD": ["PhD in Computer Science", "PhD in Statistics", "PhD in Machine Learning", "PhD in Economics"]
}

# Domain-specific templates to generate realistic resumes
TEMPLATES = {
    "Software Engineering": {
        "summaries": [
            "Innovative Software Engineer with {exp} years of experience specializing in building scalable web applications and distributed systems.",
            "Results-driven Developer with a strong foundation in software design patterns, microservices architecture, and cloud operations. Experienced in leading agile developer teams.",
            "Full-Stack Developer with {exp}+ years of background in design, development, and deployment of complex software architectures. Passionate about clean code and automation."
        ],
        "roles": ["Software Engineer", "Senior Software Engineer", "Full Stack Developer", "Backend Engineer", "Cloud Engineer"],
        "achievements": [
            "Architected and deployed microservices using {skill1} and {skill2}, reducing server latency by {num}%.",
            "Designed and implemented high-throughput REST APIs with {skill1}, handling over {num}k daily active users.",
            "Led migration of legacy systems to {skill1} on {skill2}, improving deployment efficiency by {num}%.",
            "Refactored codebases using {skill1}, improving test coverage from 60% to {num}%.",
            "Collaborated with cross-functional teams to integrate {skill1} with SQL/NoSQL databases, saving database overhead by {num}%."
        ]
    },
    "Data Science & AI": {
        "summaries": [
            "Data Scientist with {exp} years of experience turning complex datasets into actionable business insights. Highly skilled in {skill1} and {skill2}.",
            "Machine Learning Engineer specializing in building, training, and deploying predictive models. Proficient in deep learning and NLP architectures.",
            "Analytical and detail-oriented Data Professional with {exp}+ years of expertise in predictive analytics, statistics, and machine learning pipelines."
        ],
        "roles": ["Data Scientist", "Machine Learning Engineer", "Data Analyst", "AI Researcher", "Data Engineer"],
        "achievements": [
            "Developed predictive models using {skill1} and {skill2} that improved forecasting accuracy by {num}%.",
            "Built end-to-end NLP pipelines using {skill1} and BERT, reducing text processing time by {num}%.",
            "Designed and optimized recommendation algorithms using {skill1}, resulting in a {num}% increase in user engagement.",
            "Created data pipelines using {skill1} and Spark, processing {num} GB of unstructured data daily.",
            "Implemented an automated anomaly detection system using {skill1}, saving {num} hours of manual audit work weekly."
        ]
    },
    "Product Management": {
        "summaries": [
            "Product Manager with {exp} years of experience managing SaaS products from concept to launch. Strong focus on user-centric design and agile execution.",
            "Technical Product Manager with a track record of driving cross-functional teams to deliver high-impact features using {skill1} and analytics.",
            "Dynamic PM skilled in product roadmap execution, stakeholder alignment, and data-driven product strategy. Experienced in {skill1}."
        ],
        "roles": ["Product Manager", "Associate Product Manager", "Technical Product Manager", "Product Owner", "Senior PM"],
        "achievements": [
            "Defined the product strategy and roadmap for a new SaaS product, achieving ${num}k ARR within the first year.",
            "Managed cross-functional teams of {num} engineers and designers using Agile and Scrum methodologies.",
            "Conducted {num}+ customer interviews and user research sessions, translating feedback into successful PRDs.",
            "Optimized onboarding funnel using {skill1} and A/B testing, boosting user conversion by {num}%.",
            "Collaborated with marketing to execute go-to-market strategies, growing user base by {num}% quarter-over-quarter."
        ]
    },
    "Marketing & Sales": {
        "summaries": [
            "Results-driven Marketer with {exp} years of experience designing and executing comprehensive digital campaigns that drive conversion.",
            "Growth Marketing specialist with expertise in {skill1}, lead generation, and customer acquisition. Skilled in using CRM systems.",
            "Sales professional with a proven track record of exceeding quotas, managing high-value client relations, and leveraging data for market growth."
        ],
        "roles": ["Marketing Manager", "Growth Specialist", "B2B Sales Representative", "Digital Marketing Specialist", "Account Executive"],
        "achievements": [
            "Managed a monthly ad budget of ${num}k, optimizing campaigns to reduce CPA by {num}%.",
            "Designed and executed SEO and content strategy using {skill1}, increasing organic traffic by {num}%.",
            "Led CRM integration and email campaigns on {skill1}, increasing sales lead pipeline by {num}%.",
            "Negotiated and closed enterprise deals, generating ${num}k in new revenue in Q3.",
            "Spearheaded social media marketing campaigns, growing brand followers by {num}% and engagement rates by {num}%."
        ]
    },
    "Finance & Accounting": {
        "summaries": [
            "Detail-oriented Financial Analyst with {exp} years of experience in corporate finance, financial modeling, and risk mitigation.",
            "Certified Accountant with extensive background in GAAP compliance, auditing, and corporate budgeting. Proficient in {skill1}.",
            "Finance specialist skilled in portfolio management, corporate valuation, and strategic forecasting using Excel, SQL, and Python."
        ],
        "roles": ["Financial Analyst", "Senior Accountant", "Finance Manager", "Auditor", "Investment Analyst"],
        "achievements": [
            "Built financial models using {skill1} to forecast company cash flows, reducing forecast error to under {num}%.",
            "Managed annual budget of ${num}k, identifying cost-saving opportunities of {num}% across departments.",
            "Led GAAP auditing for {num} corporate clients, ensuring 100% compliance and zero material findings.",
            "Automated reporting workflows using {skill1} and Excel VBA, saving {num} hours of manual work per month.",
            "Conducted asset valuation and risk assessment, advising senior leadership on a ${num}M acquisition deal."
        ]
    }
}

def generate_resume(category, name, skills, exp):
    # Select templates
    temp = TEMPLATES[category]
    summary = random.choice(temp["summaries"]).format(exp=exp, skill1=skills[0], skill2=skills[1] if len(skills) > 1 else skills[0])
    
    # Generate experience section
    exp_text = []
    num_jobs = min(3, max(1, exp // 3))
    curr_year = 2026
    for i in range(num_jobs):
        role = random.choice(temp["roles"])
        if i == 0:
            role = "Senior " + role if exp > 6 else role
        duration = f"{curr_year - (i+1)*3} - {curr_year - i*3}"
        comp = f"Company {chr(65+i)}"
        
        ach_list = []
        for _ in range(2):
            ach = random.choice(temp["achievements"]).format(
                skill1=random.choice(skills),
                skill2=random.choice(skills),
                num=random.randint(15, 85)
            )
            ach_list.append(f"- {ach}")
        
        exp_text.append(f"{role} at {comp} ({duration})\n" + "\n".join(ach_list))
    
    # Generate education
    uni = random.choice(UNIVERSITIES)
    deg_level = "Bachelor"
    if exp > 8:
        deg_level = random.choice(["Master", "PhD"])
    elif exp > 4:
        deg_level = random.choice(["Bachelor", "Master"])
    edu = random.choice(DEGREES[deg_level])
    
    # Combine into a professional-looking layout
    resume_parts = [
        f"NAME: {name}",
        f"CONTACT: {name.lower().replace(' ', '')}@email.com | +1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        f"OBJECTIVE\n{summary}",
        "EXPERIENCE\n" + "\n\n".join(exp_text),
        f"EDUCATION\n{edu} - {uni}",
        "SKILLS\n" + ", ".join(skills)
    ]
    
    return "\n\n".join(resume_parts), edu, uni

def main():
    # Ensure directories exist
    os.makedirs("data", exist_ok=True)
    
    db_path = "data/candidates.db"
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create candidates table
    cursor.execute("""
        DROP TABLE IF EXISTS candidates
    """)
    cursor.execute("""
        CREATE TABLE candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            category TEXT NOT NULL,
            experience_years INTEGER NOT NULL,
            education_degree TEXT NOT NULL,
            education_institution TEXT NOT NULL,
            skills TEXT NOT NULL,
            resume_text TEXT NOT NULL
        )
    """)
    
    print("Generating 5,000+ candidate profiles...")
    
    candidates = []
    total_records = 5200  # Generate slightly more than 5,000 to be safe
    
    for i in range(total_records):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        
        category = random.choice(CATEGORIES)
        exp = random.randint(1, 18)
        
        # Pick 5-8 random skills from the pool for this category
        skills_available = SKILLS_POOL[category]
        num_skills = random.randint(5, 8)
        candidate_skills = random.sample(skills_available, min(num_skills, len(skills_available)))
        
        resume_text, edu, uni = generate_resume(category, name, candidate_skills, exp)
        email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@example.com"
        phone = f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        candidates.append((
            name,
            email,
            phone,
            category,
            exp,
            edu,
            uni,
            ", ".join(candidate_skills),
            resume_text
        ))
        
        if (i + 1) % 1000 == 0:
            print(f"Generated {i + 1} profiles...")
            
    # Bulk insert
    cursor.executemany("""
        INSERT INTO candidates (
            name, email, phone, category, experience_years, 
            education_degree, education_institution, skills, resume_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, candidates)
    
    conn.commit()
    
    # Check count
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]
    print(f"Successfully inserted {count} candidates into database at {db_path}!")
    
    conn.close()

if __name__ == "__main__":
    main()
