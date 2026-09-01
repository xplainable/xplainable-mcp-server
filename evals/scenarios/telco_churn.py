"""Telco churn eval scenarios.

Prompts are {dataset_name} templates: the dataset wiring uploads the fixture
under a unique per-case name and formats the prompt with it (avoids name
collisions across k repeats).
"""
from evals.harness.models import Scenario, Stage

TELCO_FULL = Scenario(
    name="telco_churn_full",
    prompt=(
        "Analyse the '{dataset_name}' dataset: explore it, pick the right "
        "churn label, prepare the data and engineer useful features, persist "
        "that preprocessing, train a churn model on the prepared data, deploy "
        "it, score 20 held-out customers, create a report I can open, and "
        "then optimise retention offers for the 20 customers (budget-aware)."
    ),
    fixture="telco_churn_500.csv",
    expected_stages=list(Stage),
    immutable_features=["gender", "customerID", "tenure"],
    dataset_name="telco_eval",
)

TELCO_MINIMAL = Scenario(
    name="telco_churn_minimal",
    prompt=(
        "Train a churn model on the '{dataset_name}' dataset (prepare the "
        "data first), deploy it, and score 5 held-out customers."
    ),
    fixture="telco_churn_500.csv",
    expected_stages=[Stage.DATA_PREP, Stage.PERSIST_PREP, Stage.TRAIN,
                     Stage.DEPLOY, Stage.PREDICT],
    immutable_features=["gender", "customerID", "tenure"],
    dataset_name="telco_eval",
)

ALL = {s.name: s for s in (TELCO_FULL, TELCO_MINIMAL)}
