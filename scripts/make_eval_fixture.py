"""Build the committed telco-churn eval fixture (500-row seeded sample).

Source: IBM Telco Customer Churn (public sample dataset).
"""
from pathlib import Path

import pandas as pd

URL = ("https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
       "master/data/Telco-Customer-Churn.csv")
OUT = "evals/scenarios/fixtures/telco_churn_500.csv"

df = pd.read_csv(URL)
# TotalCharges has blank strings in the raw data — keep them; data prep is
# part of what the agent under eval is supposed to handle.
sample = df.sample(n=500, random_state=42).reset_index(drop=True)
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
sample.to_csv(OUT, index=False)
print(f"wrote {OUT}: {sample.shape}")
