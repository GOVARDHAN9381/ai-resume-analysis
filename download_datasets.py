import pandas as pd
from datasets import load_dataset
import os

print("Downloading dataset 1: sandeeppanem/resume-json-extraction-5k ...")
ds1 = load_dataset("sandeeppanem/resume-json-extraction-5k", split="train")
df1 = ds1.to_pandas()
df1.to_csv("dataset_1_resumes_5k.csv", index=False)
print(f"Saved dataset 1 with {len(df1)} rows to dataset_1_resumes_5k.csv")

print("\nDownloading dataset 2: MikePfunk28/resume-training-dataset ...")
try:
    ds2 = load_dataset("MikePfunk28/resume-training-dataset", split="train")
    df2 = ds2.to_pandas()
    # Let's take just the first 5000 to keep the file size reasonable
    df2_5k = df2.head(5000)
    df2_5k.to_csv("dataset_2_resumes_5k.csv", index=False)
    print(f"Saved dataset 2 with {len(df2_5k)} rows to dataset_2_resumes_5k.csv")
except Exception as e:
    print(f"Failed to download dataset 2: {e}")

print("\nFinished downloading datasets.")
