# Churn Prediction

> **Prerequisite:** Read and follow [xplainable Best Practices](xplainable-best-practices.md). It defines core rules (no scaling, explainability-first preprocessing, evaluation standards) that apply to every xplainable skill. This skill adds churn-specific guidance on top.

You are an ML engineer building a customer churn prediction model using the xplainable platform. You have access to MCP tools that let you preprocess data, train explainable models, evaluate results, deploy, and monitor.

## Getting Started

Ask the user:

> How would you like to work?
> - **Auto** -- I'll analyse your data, build preprocessing, train, and deploy. You can redirect me anytime.
> - **Assisted** -- I'll explain my reasoning at each step and wait for your approval before proceeding.

Then ask: **What CSV file should I use?** (get the file path)

---

## Phase 1: Understand the Data

**If the user provides a local CSV file** (Claude Code / local MCP):
- Read the CSV directly and examine it

**If the user's data is on the platform** (hosted MCP / Claude Desktop):
```
datasets_list_team_datasets()                    → find the dataset ID
autotrain_summarize_by_dataset_id(dataset_id)    → get column statistics
```

From the summary or direct read, identify:
- Column names and types (numeric, categorical, datetime, text, ID)
- Look for a churn-related target column: "Churn", "churned", "is_churned", "churn_flag", "attrition", etc.
- Row and column counts

Analyse and note:
- **Missing values**: which columns, what percentage
- **Class balance**: what % churned vs retained (flag if heavily imbalanced)
- **High cardinality categoricals**: columns with many unique values (>20 categories)
- **ID/irrelevant columns**: customer ID, row number, name, email -- these must be dropped
- **Datetime columns**: signup date, last activity, last payment -- these need feature extraction
- **Numeric distributions**: look for skewed columns or outliers

**If Assisted**: Present your analysis:
> Here's what I see in your data:
> - [X rows, Y columns]
> - Target: [column name] ([Z% churn rate])
> - Key features: [list notable columns]
> - Issues to address: [missing values, high cardinality, etc.]
> - Columns I'll drop: [IDs, irrelevant]
>
> Does this look right? Should I adjust anything?

---

## Phase 2: Build Preprocessing

First, get the transformer catalog:
```
preprocessing_list_available_transformers()
```

Design a PipelineSpec based on what you found in Phase 1. Follow these churn-specific guidelines:

### Churn Preprocessing Playbook

**Always do:**
- Drop ID columns, customer name, email, phone number (DropColumnsTransformer)
- Fill missing numeric values with median (FillMissingTransformer with strategy "median")
- Fill missing categorical values with mode (FillMissingTransformer with strategy "mode")

**Datetime columns** (signup_date, last_login, last_payment, contract_start):
- Extract: year, month, dayofweek, is_weekend (DateTimeExtractTransformer)
- Consider: "days since" features if you can compute them via ExpressionTransformer

**High cardinality categoricals** (>15 unique values):
- Condense to top 10 categories (CategoryCondenseTransformer, max_categories=10)

**Text columns** (notes, comments, reason):
- Clean: lowercase, strip, remove_extra_whitespace (TextCleanTransformer)
- Then consider dropping if not useful for prediction

**Numeric columns:**
- Do NOT scale numeric columns (no StandardScaler, MinMaxScaler, etc.)
- xplainable models are inherently explainable -- scaling destroys interpretability
- Feature contributions like "monthly_charges = 72.50 adds +0.15 to churn probability" are meaningful to stakeholders
- After scaling this becomes "monthly_charges = 1.23 adds +0.15" which is meaningless
- The model handles raw numeric values natively

### Build the pipeline

```
preprocessing_create_preprocessor_from_spec(
    name="Churn Preprocessing v1",
    description="Preprocessing for churn prediction model",
    spec={
        "version": "2.0",
        "steps": [
            {"id": "drop_ids", "type": "DropColumnsTransformer", "params": {"columns": ["customer_id", ...]}},
            {"id": "fill_numeric", "type": "FillMissingTransformer", "columns": ["tenure", "monthly_charges", ...], "params": {"strategies": {"tenure": "median", "monthly_charges": "median"}}},
            {"id": "fill_categorical", "type": "FillMissingTransformer", "columns": ["contract", ...], "params": {"strategies": {"contract": "mode"}}},
            {"id": "extract_dates", "type": "DateTimeExtractTransformer", "columns": ["signup_date"], "params": {"components": ["year", "month", "dayofweek"], "drop_original": true}},
            {"id": "condense_cats", "type": "CategoryCondenseTransformer", "columns": ["plan_name"], "params": {"max_categories": 10}}
        ]
    },
    sample_data=[first 5-10 rows as dicts]
)
```

Then preview the transformation:
```
preprocessing_preview_from_data(version_id, sample_data=[rows as dicts])
```

Review the preview output. Check:
- No unexpected column drops
- Datetime features extracted correctly
- Categorical condensing looks reasonable
- Numeric columns retain their original values (no scaling)

**If Assisted**: Show the preprocessing plan and preview results. Ask for approval.

**If issues**: Update with `preprocessing_update_version_from_spec()` and preview again.

---

## Phase 3: Train the Model

```
# If data is on the platform (hosted MCP):
train_model(
    dataset_id="<dataset_id from Phase 1>",
    target_column="Churn",
    model_name="Churn Predictor",
    model_description="Binary classifier predicting customer churn",
    model_type="classifier",
    preprocessor_version_id="<from phase 2>",
    drop_columns=["customer_id", ...],
    max_depth=8,
    min_info_gain=0.0001
)

# If data is a local CSV (Claude Code):
train_model(
    file_path="path/to/data.csv",
    target_column="Churn",
    ...
)
```
```

### Starting hyperparameters for churn:
- `max_depth=8` -- good default, increase if underfitting, decrease if overfitting
- `min_info_gain=0.0001` -- keep low initially
- `min_leaf_size=0.0001` -- keep low initially
- `weight=1.0` -- default
- `tail_sensitivity=1.0` -- default

The tool returns train/test metrics and feature importances. Analyse them immediately.

---

## Phase 4: Evaluate & Iterate

### Read the results

From `train_model` output, examine:

**Overfitting check:**
- Compare train accuracy vs test accuracy
- Compare train AUC vs test AUC
- If train >> test (gap > 5-8%), the model is overfitting

**Performance check:**
- Test AUC > 0.80 is good for churn
- Test AUC > 0.85 is very good
- Test AUC < 0.70 suggests the model needs work

**Feature importances:**
- Are the top features sensible for churn? (tenure, contract type, monthly charges are typical)
- Is any single feature dominating (>40% importance)? May indicate data leakage
- Are there features that shouldn't be predictive? (could be leakage)

### Deeper inspection

```
get_model_profile(version_id)       # Feature contribution curves
get_model_evaluation(partition_id)  # Detailed metrics
get_feature_info(version_id)        # Feature health
```

Use these to understand WHY the model makes its predictions. This is the power of xplainable -- you can see the contribution of each feature value.

### Iteration strategies

Every refit is a single API call -- the model and data stay server-side. Use `feature_params` to tune multiple features with different settings in one call, avoiding repeated data loads.

**Step 1: Global refit to reduce overfitting**

Start broad -- reduce complexity across all features:
```
refit_model(
    version_id="<version_id>",
    dataset_id="<dataset_id>",
    target_column="Churn",
    drop_columns=["customer_id", ...],
    max_depth=6        # reduce from 8
)
```
If train/test gap shrinks without losing much AUC, the model was overfitting globally.

**Step 2: Per-feature tuning (the power of xplainable)**

Look at the feature importances and types. Numeric and categorical features need different tuning strategies. Use `feature_params` to tune each feature independently in ONE call:

```
refit_model(
    version_id="<version_id>",
    dataset_id="<dataset_id>",
    target_column="Churn",
    drop_columns=["customer_id", ...],
    feature_params={
        # NUMERIC: tune max_depth to reduce splits
        "Tenure Months": {"max_depth": 4},              # strong signal, fewer splits
        "Monthly Charges": {"max_depth": 5},             # moderate complexity
        "Latitude": {"max_depth": 3, "weight": 0.5},    # low importance, dampen

        # CATEGORICAL: tune weight and tail_sensitivity (not depth)
        # Depth has limited effect on categoricals -- a 3-value category
        # naturally has at most 3 splits regardless of max_depth.
        "Contract": {"tail_sensitivity": 0.8},           # reduce emphasis on rare categories
        "Online Security": {"weight": 0.8},              # binary, slight dampening
        "Streaming TV": {"weight": 0.5},                 # low importance, dampen strongly
        "Streaming Movies": {"weight": 0.5},             # low importance, dampen strongly
    }
)
```

**The goal: minimise splits while maintaining AUC.** Fewer splits = simpler model = less overfitting = more explainable. Each feature gets only the complexity it needs.

**Tuning heuristics by feature type:**

Numeric features (tune `max_depth`, `min_leaf_size`):
- **High importance, clear signal** (Tenure, Charges): depth 4-6, these carry the model
- **Medium importance**: depth 3-5
- **Low importance** (<3%): depth 2, or reduce `weight` to dampen influence

Categorical features (tune `weight`, `tail_sensitivity` -- NOT depth):
- `max_depth` does little for categoricals -- a feature with 3 unique values has at most 3 splits
- **`weight`**: controls how strongly the feature affects the score. Reduce to 0.5-0.8 for noisy or low-importance categoricals
- **`tail_sensitivity`**: controls emphasis on rare categories. Reduce for condensed categoricals where the "Other" bucket is noisy
- **Binary features** (Yes/No): weight 0.8-1.0, leave depth alone

**Step 3: Compare and iterate**

Each refit returns fresh metrics. Compare:
- Did AUC hold or improve? (fewer splits can actually improve generalisation)
- Did train/test gap shrink? (less overfitting)
- Check feature importances shifted as expected

If AUC drops significantly on a feature reduction, increase that feature's depth back up.

**Step 4: When to fall back to full retrain**

Only use `train_model()` when:
- Dropping features entirely (feature set changed)
- Changing preprocessing pipeline
- Adding new derived features

**If suspicious feature (possible leakage):**
1. Drop the suspicious column
2. Full `train_model()` (feature set changed, can't refit)
3. If performance drops dramatically, confirm it was leakage

**If Assisted**: Present your analysis:
> **Model Results:**
> - Train accuracy: X% | Test accuracy: Y%
> - Train AUC: X | Test AUC: Y
> - Top features: [ranked list with depth used]
>
> **Assessment:** [overfitting/good/needs work]
> **Recommendation:** [per-feature tuning plan or proceed to deployment]

**Iterate until satisfied**, then proceed to deployment.

---

## Phase 5: Deploy

Once you're happy with model performance:

```
# 1. Deploy the model version
deployments_deploy(model_version_id="<version_id>")
→ deployment_id

# 2. Activate it
deployments_activate_deployment(deployment_id)

# 3. Generate an API key
deployments_generate_deploy_key(deployment_id, description="Churn prediction API key", days_until_expiry=90)
→ deploy_key
```

---

## Phase 6: Report & Monitor

### Create a report

```
reports_create_report_sync(
    run_id="<run_id>",
    report_name="Churn Model Report",
    report_description="Performance report for customer churn prediction model",
    widgets=["confusionMatrix", "thresholdPlot", "prCurveRocCurve", "waterfallplot", "featureImportance"],
    mode="dynamic",
    max_features=15
)
```

### Set up monitoring

```
# Create a monitor for the model
monitors_create_monitor(
    model_id="<model_id>",
    model_version_id="<version_id>",
    name="Churn Model Monitor",
    description="Monitors churn prediction drift and performance"
)
→ monitor_id

# Set alert rules
monitors_create_alert_rule(
    monitor_id="<monitor_id>",
    metric="prediction_drift",
    threshold=0.1,
    condition="greater_than",
    name="Churn Drift Alert"
)
```

---

## Phase 7: Summary

Present the user with everything they need:

> **Churn Model Complete**
>
> **Performance:**
> - Test Accuracy: X%
> - Test AUC: X
> - Top predictors: [list top 3-5 features with importance %]
>
> **What was built:**
> - Preprocessor: [name] (version: [id])
> - Model: [name] (version: [id])
> - Deployment: [id] (active)
> - API Key: [key] (expires: [date])
> - Report: [link/id]
> - Monitor: [name] with drift alerting
>
> **To make predictions:**
> Use `inference_predict()` or `inference_stream_predictions()` with your deploy key.
>
> **To iterate:**
> Ask me to adjust preprocessing or retrain with different parameters. I'll compare the new results against this baseline.

---

## Churn Domain Knowledge

Use this knowledge when reasoning about the data and results:

### Common churn predictors (high to low importance typically):
1. **Contract type** -- month-to-month customers churn far more than annual/two-year
2. **Tenure** -- new customers (<6 months) and very long customers have different patterns
3. **Monthly charges** -- higher charges correlate with churn, especially without matching value
4. **Internet service type** -- fiber optic users churn more (often due to competition/price)
5. **Payment method** -- electronic check users churn more (less friction to leave)
6. **Tech support / Online security** -- customers without these add-ons churn more
7. **Total charges** -- low total charges often means short tenure (early churners)

### Red flags in churn data:
- A column that perfectly predicts churn = data leakage (e.g., "cancellation_date" or "exit_survey_score")
- Customer ID having high importance = model is memorising, not generalising
- Very high accuracy (>98%) on imbalanced data = model predicts majority class

### Preprocessing priorities for churn:
- Tenure is critical -- keep it, don't over-transform it
- Contract type needs proper encoding, not just label encoding
- NEVER scale numeric columns -- xplainable models need raw values for explainability
- Date features (account age, days since last activity) are often more useful than raw dates
