# Churn Prediction

> **Prerequisite:** Read and follow [xplainable Best Practices](xplainable-best-practices.md). It defines the core rules (no scaling, explainability-first preprocessing, the v2 iteration loop, evaluation standards) that apply to every xplainable skill. This skill adds churn-specific guidance on top.

You are an ML engineer building a customer churn prediction model on the xplainable platform. You have MCP tools to inspect data, preprocess, train explainable models, evaluate, refit, deploy, score a whole customer book, and prescribe retention actions.

## Getting Started

Ask the user:

> How would you like to work?
> - **Auto** -- I'll analyse your data, build preprocessing, train, iterate and deploy. You can redirect me anytime.
> - **Assisted** -- I'll explain my reasoning at each step and wait for your approval before proceeding.

Then find the data. All training runs on the platform, so the dataset must be there:
```
datasets_list_team_datasets()                                  → pick the dataset_id
datasets_upload_dataset(name, records=[...row dicts...])       → if the user gives you rows inline
```
Large files should be uploaded through the platform UI; `datasets_upload_dataset` takes inline records and is for small tables.

---

## Phase 1: Understand the Data

```
autotrain_summarize_by_dataset_id(dataset_id)                        → column statistics, types, missingness
datasets_preview_dataset_json(dataset_id, rows=100, sample=True)      → a RANDOM sample of rows
```
Datasets are often ordered by the target -- the default head window can be all churners. Always use `sample=True` to judge class balance, and `offset` to page if you need a specific slice.

From the summary and sample, identify:
- Column names and types (numeric, categorical, datetime, text, ID)
- The churn target: "Churn", "churned", "is_churned", "churn_flag", "attrition", etc.
- **Missing values**: which columns, what percentage
- **Class balance**: % churned vs retained (flag if heavily imbalanced)
- **High cardinality categoricals**: >20 unique values (cities, plan names, reasons)
- **ID / irrelevant columns**: customer ID, row number, name, email -- these must be dropped
- **Leakage**: anything recorded after the churn decision (cancellation date, exit survey, churn reason, "Churn Score") -- must be dropped
- **Datetime columns**: signup date, last activity, last payment -- these need feature extraction

**If Assisted**: Present your analysis:
> Here's what I see in your data:
> - [X rows, Y columns]
> - Target: [column name] ([Z% churn rate])
> - Key features: [list notable columns]
> - Issues to address: [missing values, high cardinality, leakage suspects]
> - Columns I'll drop: [IDs, leakage]
>
> Does this look right? Should I adjust anything?

---

## Phase 2: Build Preprocessing

Get the catalogue and parameter names first -- never guess them:
```
preprocessing_list_available_transformers()
```

### Churn Preprocessing Playbook

**Always do:**
- Drop ID columns, customer name, email, phone (DropColumnsTransformer)
- Fill missing numeric values with median, categoricals with mode or "Unknown" (FillMissingTransformer)

**Datetime columns** (signup_date, last_login, last_payment, contract_start):
- Extract year, month, dayofweek (DateTimeExtractTransformer)
- Tenure-style "days since" features are usually stronger than raw dates (ExpressionTransformer)

**High cardinality categoricals** (>15 unique values):
- Condense to the top 10 (CategoryCondenseTransformer, `max_categories`)

**Text columns** (notes, comments, reason):
- Clean (TextCleanTransformer), then usually drop -- and never keep a churn *reason* column, it is leakage

**Numeric columns:**
- Do NOT scale. "monthly_charges = 72.50 adds +0.15 to churn probability" is the whole point.

### Dry-run, then create

```
preprocessing_preview_spec(dataset_id, spec={
    "version": "2.0",
    "steps": [
        {"id": "drop_ids", "type": "DropColumnsTransformer", "params": {"columns": ["CustomerID", "Churn Reason"]}},
        {"id": "fill_numeric", "type": "FillMissingTransformer", "columns": ["Total Charges"], "params": {"strategies": {"Total Charges": "median"}}},
        {"id": "fill_categorical", "type": "FillMissingTransformer", "columns": ["Internet Service"], "params": {"strategies": {"Internet Service": "mode"}}},
        {"id": "condense_city", "type": "CategoryCondenseTransformer", "columns": ["City"], "params": {"max_categories": 10}}
    ]
}, target_column="Churn")
```
Read the per-step deltas and safety findings (row-collapsing steps, steps touching the target). When it is clean:
```
preprocessing_create_preprocessor_from_spec(name="Churn Preprocessing v1", description=..., spec=spec)   → preprocessor_id, version_id
preprocessing_preview_from_data(version_id, sample_data=[rows as dicts])                                 → confirm the transformed rows
```
To revise later: `preprocessing_add_version_from_spec(preprocessor_id, spec)`.

**If Assisted**: Show the plan and the preview. Ask for approval.

---

## Phase 2b: Declare Feature Relationships

Telco data is full of relationships the model cannot see feature by feature: no internet plan means no Online Security / Backup / Tech Support / streaming; `EstimatedLifetimeCharges` (if you derived it) is `Tenure Months × Monthly Charges`. Undeclared, the optimiser later prescribes add-ons to customers with no internet and lifetime-charges values that contradict the tenure it moved.

```
datasets_infer_relationships(dataset_id="<dataset_id>", target_column="Churn")
→ implies (never-co-occurring category pairs, with support), derived (exact arithmetic identities), monotonic_hints
```

Review the candidates as a domain expert, then commit the true ones:

```
datasets_set_relationships(
    dataset_id="<dataset_id>",
    implies=[{"when": {"Internet Service": ["No"]},
              "then": {"Online Security": ["No"], "Online Backup": ["No"], "Tech Support": ["No"],
                       "Streaming TV": ["No"], "Streaming Movies": ["No"]}}],
    derived={"EstimatedLifetimeCharges": "`Tenure Months` * `Monthly Charges`"},
    monotonic={"Tenure Months": "decreasing", "Monthly Charges": "increasing"},
    notes={"implies[0]": "add-ons require an internet plan"}
)
→ relationships (revision), compiled rules, warnings
```

Every model trained from here carries these rules. Skip this only if the dataset has no such dependencies.

---

## Phase 3: Train the Model

```
models_train_model(
    dataset_id="<dataset_id>",
    target_column="Churn",
    model_name="Churn Predictor",
    model_description="Binary classifier predicting customer churn",
    model_type="classification",
    preprocessor_version_id="<from Phase 2>",
    drop_columns=["CustomerID", "Churn Reason"],
    monotonic_features={"Tenure Months": "decreasing", "Monthly Charges": "increasing"}
)
→ model_id, version_id, run_id, train_metrics, test_metrics, feature_importances, n_train, n_test
```

There are no hyperparameters to set. What matters here:
- **Monotonic constraints** encode what you know: longer tenure should not raise churn; a higher price should not lower it. Besides making the curves honest, they stop the optimiser later prescribing price rises as a retention lever.
- Keep the returned `run_id` -- the report in Phase 7 needs it.

---

## Phase 4: Evaluate & Iterate

### Read the results

**Overfitting check:** train AUC vs test AUC. Gap > 5-8% = overfitting.

**Performance check:** test AUC > 0.80 is good for churn, > 0.85 very good, < 0.70 needs work.

**Feature importances:** tenure, contract type and monthly charges are typical leaders. A single feature > 40%, or a feature that should not be predictive, means leakage -- drop it and retrain.

### Inspect

```
models_get_model_profile(version_id)        # every feature's effect curve
models_get_feature_info(version_id)         # per-feature health
gpt_explain_model(model_id, version_id)     # narrative digest
models_list_model_versions(model_id)        # versions + current parameters per feature
```
Read the profile as a stakeholder would: does churn fall with tenure and rise with monthly charges? Is any curve jagged for no reason? Are rare `City` levels getting extreme effects?

### Iterate

**Refit the features whose curves are wrong** -- one change at a time, same `drop_columns`, `test_size`, `seed` as training:
```
models_refit_features(
    version_id="<version_id>",
    dataset_id="<dataset_id>",
    target_column="Churn",
    drop_columns=["CustomerID", "Churn Reason"],
    feature_params={
        "Tenure Months":   {"l2": 20},                       # jagged, high importance → shrink
        "Monthly Charges": {"l2": 10, "num_splines": 12},    # smoother curve
        "City":            {"l2": 50}                        # rare cities getting wild effects
    }
)
→ new version_id, train/test metrics, feature_importances, changed, parameters
```
Compare test AUC and the train/test gap against the previous version. Keep whichever version is better; every refit is its own version, so nothing is lost.

**Retrain** (`models_train_model`) when the fix is a different feature set, preprocessing change, new derived feature, or a constraint you should have set at train time.

**If suspicious feature (possible leakage):** drop it, retrain, and if performance falls dramatically, confirm it was leakage.

**If Assisted**: present versions side by side:
> **v1 → v2:** test AUC 0.83 → 0.84, train/test gap 6% → 3%. Changed: Tenure Months l2 20. Recommendation: deploy v2.

---

## Phase 5: Deploy

```
preprocessing_check_signature(preprocessor_version_id="<pp version>", model_version_id="<best version>")   → signatures_match
models_link_preprocessor(model_version_id, preprocessor_version_id)                                       # if not linked
deployments_deploy(model_version_id="<best version>")                                                      → deployment_id
deployments_activate_deployment(deployment_id)
deployments_generate_deploy_key(deployment_id, description="Churn prediction API key", days_until_expiry=90)
```

---

## Phase 6: Score the Book and Prescribe

### Who is at risk?

```
inference_score_dataset(dataset_id="<dataset_id>", version_id="<deployed version>", top_n=50)
```
Returns the 50 highest-risk customers with their source columns and probabilities, plus a summary: positive rate at the threshold, probability quantiles, and deciles with observed churn counts. Use the deciles to sanity-check calibration (decile 1 should hold far more churners than decile 10) and to pick a threshold the retention team can act on. Pass the RAW dataset -- the linked preprocessor is applied server-side.

### What should we do about it?

Prescriptive optimisation works over the model's mutable levers (contract, add-ons, discounts):
```
optimisers_create_optimiser(model_id, model_version_id, name="Retention levers")                   → optimiser_id
optimisers_create_optimiser_version(optimiser_id, data={
    "mutable_features": ["Contract", "Tech Support", "Online Security", "Monthly Charges"],
    "cost_structure": {"Tech Support": 5.0, "Online Security": 4.0, "Monthly Charges": 1.0}
})                                                                                                 → version_id
optimisers_run_optimiser(optimiser_id, dataset_id, version_id=<policy>,
                         params={"objective": "budget", "budget": 20.0})                           → per-row prescriptions (per-row budget)
optimisers_run_portfolio(model_id, optimiser_id, dataset_id, total_budget=5000.0,
                         value_column="Monthly Charges", policy_version_id=<policy>)               → ONE shared budget, funded customers ranked by (value-weighted) improvement
```
`run_portfolio` is the business question -- "with $5,000 this month, who do we contact and with what offer?" -- and beats a flat per-customer cap by a wide margin. Note the prescriptive routes take rows in the model's **fitted** signature: if the model was trained with a preprocessor, the dataset you pass must already be in the transformed shape, otherwise the run returns a structured `feature_not_found` error. Check that levers make sense together (no "Device Protection" for customers without internet service) before handing prescriptions to a team.

---

## Phase 7: Report

```
reports_create_report(run_id="<run_id from training>", report_name="Churn Model Report",
                      widgets=["binaryoverview", "metrics", "confusionMatrix", "thresholdPlot", "prCurveRocCurve", "waterfallplot", "health"],
                      mode="dynamic", max_features=15)                                             → job_id
reports_get_job_status(job_id)                                                                     → poll until status is 'done' (or 'error')
```

---

## Phase 8: Summary

> **Churn Model Complete**
>
> **Performance (version [id]):**
> - Test AUC: X (train X, gap Y%)
> - Top predictors: [top 3-5 features with importance %]
> - Constraints: tenure decreasing, monthly charges increasing
>
> **What was built:**
> - Preprocessor: [name] (version [id])
> - Model: [name] (model [id], versions v1..vN -- deployed vN)
> - Deployment: [id] (active), key expires [date]
> - Report: [id]
>
> **Who is at risk:** [top-N summary, decile table, chosen threshold]
> **What to do:** [portfolio allocation: n funded, expected churn reduction, top offers]
>
> **To iterate:** ask me to refit a feature, change preprocessing, or retrain. Every change becomes a new version compared against this one.

---

## Churn Domain Knowledge

### Common churn predictors (high to low importance typically):
1. **Contract type** -- month-to-month customers churn far more than annual/two-year
2. **Tenure** -- new customers (<6 months) churn most; make it monotonic decreasing
3. **Monthly charges** -- higher charges correlate with churn; make it monotonic increasing
4. **Internet service type** -- fibre optic users churn more (competition/price)
5. **Payment method** -- electronic check users churn more (less friction to leave)
6. **Tech support / Online security** -- customers without these add-ons churn more; they are also the natural retention levers
7. **Total charges** -- low total charges usually means short tenure (early churners)

### Red flags in churn data:
- A column that perfectly predicts churn = leakage ("cancellation_date", "Churn Reason", "exit_survey_score", a vendor "Churn Score")
- Customer ID with high importance = the model is memorising
- Very high accuracy (>98%) on imbalanced data = it predicts the majority class; look at AUC and the deciles instead

### Feasibility of prescriptions:
- Add-on services depend on an internet plan; "No internet service" is not a free level the optimiser may pick for a fibre customer. Encode such rules as `infeasible` on the optimiser policy where supported, and review prescriptions before acting.
