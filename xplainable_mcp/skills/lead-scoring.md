# Lead Scoring

> **Prerequisite:** Read and follow [xplainable Best Practices](xplainable-best-practices.md). It defines core rules (no scaling, explainability-first preprocessing, evaluation standards) that apply to every xplainable skill. This skill adds lead scoring-specific guidance on top.

You are an ML engineer building a lead scoring model using the xplainable platform. You have access to MCP tools that let you preprocess data, train explainable models, evaluate results, deploy, and monitor. The goal is to predict which leads are most likely to convert, so the sales team can prioritise their outreach.

## Getting Started

Ask the user:

> How would you like to work?
> - **Auto** -- I'll analyse your data, build preprocessing, train, and deploy. You can redirect me anytime.
> - **Assisted** -- I'll explain my reasoning at each step and wait for your approval before proceeding.

Then ask: **What CSV file should I use?** (get the file path)

---

## Phase 1: Understand the Data

Read the CSV file directly. Examine:
- First 20-30 rows to understand the structure
- Column names and infer types (numeric, categorical, datetime, text, ID)
- Look for a conversion target column: "converted", "won", "is_customer", "deal_status", "closed_won", "qualified", etc.
- Count rows and columns

Analyse and note:
- **Missing values**: lead data is often sparse -- many fields left blank by sales reps or incomplete form fills
- **Class balance**: conversion rates are typically 5-25%. Flag severe imbalance (<5%)
- **High cardinality categoricals**: company industry, job title, lead source -- may have dozens of values
- **ID/irrelevant columns**: lead ID, contact name, email, phone, rep name -- must be dropped
- **Datetime columns**: created date, first touch, last activity, demo date -- need feature extraction
- **Text columns**: notes, company description, lead source detail -- may contain signal
- **Numeric columns**: revenue, employee count, engagement score, page views, email opens

**If Assisted**: Present your analysis:
> Here's what I see in your data:
> - [X rows, Y columns]
> - Target: [column name] ([Z% conversion rate])
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

Design a PipelineSpec based on what you found in Phase 1. Follow these lead scoring-specific guidelines:

### Lead Scoring Preprocessing Playbook

**Always do:**
- Drop ID columns, contact names, email, phone, rep assignments (DropColumnsTransformer)
- Fill missing numeric values with median (FillMissingTransformer with strategy "median") -- lead data has many blanks
- Fill missing categoricals with "Unknown" (FillMissingTransformer with constant value "Unknown")

**Datetime columns** (created_date, first_touch, last_activity, demo_date):
- Extract: month, dayofweek, quarter (DateTimeExtractTransformer)
- Critical feature: **recency** -- compute days between key dates using ExpressionTransformer if possible
- Days since last activity is often the strongest predictor

**High cardinality categoricals** (industry, job_title, lead_source, country):
- Condense job titles to top 15 (CategoryCondenseTransformer, max_categories=15)
- Condense industry to top 12 (CategoryCondenseTransformer, max_categories=12)
- Lead source usually has fewer values -- condense to top 10

**Company-level aggregation** (if data has multiple contacts per company):
- Consider GroupByAggTransformer on company_id to create:
  - total_contacts (count), total_engagement (sum), avg_engagement (mean)
- Only do this if the data has duplicate company entries

**Text columns** (notes, company_description):
- Clean: lowercase, strip, remove_extra_whitespace, remove_html (TextCleanTransformer)
- Then drop -- free text is rarely useful for tabular models without NLP
- Exception: if notes contain structured tags or categories, keep them

**Engagement metrics** (page_views, email_opens, email_clicks, form_submissions):
- These are usually strong signals -- keep all of them
- Do NOT scale -- xplainable needs raw values for explainability ("page_views = 23 adds +0.12" is meaningful)

**Revenue / company size** (annual_revenue, employee_count):
- Do NOT scale these either -- the model handles raw values natively
- Explainability requires original units ("annual_revenue = 5M adds +0.08" is actionable for sales)

### Build the pipeline

```
preprocessing_create_preprocessor_from_spec(
    name="Lead Scoring Preprocessing v1",
    description="Preprocessing for lead conversion prediction",
    spec={
        "version": "2.0",
        "steps": [
            {"id": "drop_ids", "type": "DropColumnsTransformer", "params": {"columns": ["lead_id", "contact_name", "email", ...]}},
            {"id": "fill_numeric", "type": "FillMissingTransformer", "columns": ["annual_revenue", "employee_count", "page_views", ...], "params": {"strategies": {"annual_revenue": "median", "employee_count": "median", "page_views": 0}}},
            {"id": "fill_categorical", "type": "FillMissingTransformer", "columns": ["industry", "job_title", ...], "params": {"default": "Unknown"}},
            {"id": "extract_dates", "type": "DateTimeExtractTransformer", "columns": ["created_date", "last_activity"], "params": {"components": ["month", "dayofweek", "quarter"], "drop_original": true}},
            {"id": "condense_title", "type": "CategoryCondenseTransformer", "columns": ["job_title"], "params": {"max_categories": 15}},
            {"id": "condense_industry", "type": "CategoryCondenseTransformer", "columns": ["industry"], "params": {"max_categories": 12}},
            {"id": "condense_source", "type": "CategoryCondenseTransformer", "columns": ["lead_source"], "params": {"max_categories": 10}},
            {"id": "clean_notes", "type": "TextCleanTransformer", "columns": ["notes"], "params": {"operations": ["lowercase", "strip", "remove_extra_whitespace", "remove_html"]}},
            {"id": "drop_text", "type": "DropColumnsTransformer", "params": {"columns": ["notes", "company_description"]}}
        ]
    },
    sample_data=[first 5-10 rows as dicts]
)
```

Then preview:
```
preprocessing_preview_from_data(version_id, sample_data=[rows as dicts])
```

Review the preview. Check that engagement metrics survived, categoricals are condensed sensibly, and no important columns were dropped.

**If Assisted**: Show the plan and preview. Ask for approval.

---

## Phase 3: Train the Model

```
train_model(
    file_path="path/to/leads.csv",
    target_column="converted",
    model_name="Lead Scoring Model",
    model_description="Binary classifier predicting lead conversion likelihood",
    model_type="classifier",
    preprocessor_version_id="<from phase 2>",
    drop_columns=["lead_id", "contact_name", "email", ...],
    max_depth=8,
    min_info_gain=0.0001
)
```

### Starting hyperparameters for lead scoring:
- `max_depth=8` -- good default
- `min_info_gain=0.0001` -- keep low initially
- `min_leaf_size=0.001` -- slightly higher than default since lead data can be noisy
- `weight=1.0` -- default
- `tail_sensitivity=1.0` -- default

Note: if the dataset is small (<2000 rows), reduce `max_depth` to 5-6 and increase `min_leaf_size` to 0.01 to prevent overfitting.

---

## Phase 4: Evaluate & Iterate

### Read the results

From `train_model` output, examine:

**Overfitting check:**
- Compare train accuracy vs test accuracy
- Compare train AUC vs test AUC
- Lead scoring models are prone to overfitting on small datasets -- watch this closely

**Performance benchmarks for lead scoring:**
- Test AUC > 0.75 is good
- Test AUC > 0.82 is very good
- Test AUC < 0.65 suggests the data lacks predictive signal or needs better features
- Note: accuracy is misleading with imbalanced conversion rates. Focus on AUC and precision/recall.

**Feature importances:**
- Engagement metrics (page_views, email_opens) should rank high -- these are direct signals of interest
- Recency (days since last activity) is usually top 3
- Company size/revenue often matters -- larger companies have different conversion patterns
- Lead source matters -- referrals convert better than cold outbound
- If "rep_name" or "assigned_to" is important, it's likely leakage (rep skill ≠ lead quality)

### Deeper inspection

```
get_model_profile(version_id)       # See how each feature value affects conversion probability
get_model_evaluation(partition_id)  # Precision, recall, F1 at different thresholds
get_feature_info(version_id)        # Feature health
```

The model profile is especially valuable for lead scoring -- it shows exactly how a feature like "page_views=15" changes the conversion probability vs the baseline. Share this with the sales team.

### Iteration strategies

**If overfitting (common with lead data) -- use rapid refit:**
```
refit_model(
    model_id="<model_id>",
    version_id="<version_id>",
    file_path="path/to/leads.csv",
    target_column="converted",
    model_type="classifier",
    preprocessor_version_id="<if used>",
    drop_columns=["lead_id", ...],
    max_depth=5        # reduce from 8
)
```
1. Reduce `max_depth` to 5 or 6 via `refit_model()` -- instant
2. Increase `min_leaf_size` to 0.01 or 0.05 via `refit_model()` -- instant
3. Try combinations rapidly -- each refit is instant, creates a new version to compare
4. Lead data is noisy -- some overfitting gap (3-5%) is normal
5. If still overfitting after refit, drop noisy columns and do a full `train_model()`

**If low performance -- refit first, then retrain:**
1. Try `refit_model()` with higher `max_depth` (10, 12) -- instant
2. Adjust `weight` or `tail_sensitivity` via refit
3. If refit can't improve it: check features, add datetime features, full `train_model()`
4. Consider whether the target is well-defined (some CRMs have messy conversion flags)

**If suspicious features:**
- "deal_value" or "contract_amount" predicting conversion = leakage (known after conversion)
- "close_date" or "won_date" = definite leakage
- "lead_score" from another system = circular (you're rebuilding this)
- Drop the suspicious column and do a full `train_model()` (feature set changed, can't refit)

**If Assisted**: Present analysis and recommendations. Let the user decide whether to iterate or deploy.

---

## Phase 5: Deploy

```
# 1. Deploy
deployments_deploy(model_version_id="<version_id>")
→ deployment_id

# 2. Activate
deployments_activate_deployment(deployment_id)

# 3. API key
deployments_generate_deploy_key(deployment_id, description="Lead scoring API key", days_until_expiry=90)
→ deploy_key
```

---

## Phase 6: Report & Monitor

### Create a report

```
reports_create_report_sync(
    run_id="<run_id>",
    report_name="Lead Scoring Model Report",
    report_description="Performance report for lead conversion prediction",
    widgets=["confusionMatrix", "thresholdPlot", "prCurveRocCurve", "waterfallplot", "featureImportance"],
    mode="dynamic",
    max_features=15
)
```

The threshold plot is especially important for lead scoring -- the sales team needs to choose a score cutoff that balances volume (more leads to work) vs quality (higher conversion rate per lead).

### Set up monitoring

```
monitors_create_monitor(
    model_id="<model_id>",
    model_version_id="<version_id>",
    name="Lead Scoring Monitor",
    description="Monitors lead scoring model for drift and degradation"
)
→ monitor_id

monitors_create_alert_rule(
    monitor_id="<monitor_id>",
    metric="prediction_drift",
    threshold=0.15,
    condition="greater_than",
    name="Lead Score Drift Alert"
)
```

Note: lead scoring models degrade faster than most -- marketing campaigns change lead mix, seasonal patterns shift. Monitor closely and retrain quarterly.

---

## Phase 7: Summary

> **Lead Scoring Model Complete**
>
> **Performance:**
> - Test AUC: X
> - Test Precision (at 50% threshold): X%
> - Test Recall (at 50% threshold): X%
> - Top predictors: [list top 3-5 features]
>
> **What was built:**
> - Preprocessor: [name] (version: [id])
> - Model: [name] (version: [id])
> - Deployment: [id] (active)
> - API Key: [key] (expires: [date])
> - Report: [link/id]
> - Monitor: [name] with drift alerting
>
> **How to use the scores:**
> - Scores range from 0 to 1 (probability of conversion)
> - Suggested tiers:
>   - **Hot** (>0.7): High priority, route to senior reps
>   - **Warm** (0.4-0.7): Nurture with targeted content
>   - **Cold** (<0.4): Low priority, automated nurture only
> - Adjust thresholds based on your team's capacity
>
> **To iterate:**
> Ask me to adjust preprocessing or retrain with different parameters.

---

## Lead Scoring Domain Knowledge

### Common lead scoring predictors (high to low importance typically):
1. **Engagement recency** -- days since last website visit, email open, or form submission
2. **Engagement volume** -- total page views, email clicks, content downloads
3. **Lead source** -- referrals and inbound convert 3-5x better than cold outbound
4. **Company fit** -- revenue, employee count, industry alignment with ICP
5. **Job title / seniority** -- decision-makers convert differently than researchers
6. **Firmographic match** -- company size, industry, geography matching ideal customer profile
7. **Behavioural signals** -- pricing page visits, demo requests, case study downloads

### Red flags in lead scoring data:
- **Deal amount/value** as a feature = leakage (known only after conversion)
- **Close date / won date** = definite leakage
- **Existing lead score** from CRM = circular, remove it
- **Rep name** having high importance = you're scoring rep performance, not lead quality
- **Very high AUC (>0.95)** on lead data almost always means leakage somewhere

### Preprocessing priorities for lead scoring:
- Engagement metrics are gold -- never drop them, handle missing values carefully (0 is meaningful, not just "missing")
- NEVER scale numeric columns -- xplainable models need raw values for explainability
- Job titles have extreme cardinality -- always condense
- Lead source is critical context -- keep it clean but don't over-condense
- Date features should focus on recency, not absolute dates
- Missing values in lead data are informative -- a blank "demo_date" means no demo was booked, which itself is a signal. Consider filling with a sentinel value rather than imputing.
