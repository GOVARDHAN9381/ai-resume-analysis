import time
import pandas as pd
from src.nlp_utils import extract_skills

print("Loading dataset...")
df = pd.read_csv("sample_dataset.csv")

print(f"Loaded {len(df)} rows. Running extract_skills on all of them...")

start = time.time()
df["skills"] = df["resume_text"].apply(lambda t: ", ".join(extract_skills(str(t))))
end = time.time()

print(f"Done in {end - start:.2f} seconds!")
