"""Build the committed telco-churn eval fixture (500-row seeded sample).

Source: IBM Telco Customer Churn (public sample dataset).
"""
from pathlib import Path

import pandas as pd

URL = ("https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
       "master/data/Telco-Customer-Churn.csv")
OUT = "evals/scenarios/fixtures/telco_churn_500.csv"

# Read TotalCharges as str to preserve values byte-for-byte (incl. blanks).
df = pd.read_csv(URL, dtype={"TotalCharges": str})
# TotalCharges has blank strings in the raw data — force-include ALL such rows
# so the fixture keeps its messy-data property; data prep is part of what the
# agent under eval is supposed to handle. Fill to 500 with a seeded sample of
# the rest, then shuffle so the blank rows aren't clustered.
blank = df[df["TotalCharges"].str.strip() == ""]
rest = df.drop(blank.index).sample(n=500 - len(blank), random_state=42)
sample = pd.concat([blank, rest]).sample(frac=1, random_state=42).reset_index(drop=True)
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
sample.to_csv(OUT, index=False)
print(f"wrote {OUT}: {sample.shape}")
