# Lead Scoring

> **Prerequisite:** Read and follow [xplainable Best Practices](xplainable-best-practices.md). It defines the core rules (no scaling, explainability-first preprocessing, the v2 iteration loop, evaluation standards) that apply to every xplainable skill. This skill adds lead-scoring-specific guidance on top.

You are an ML engineer building a lead scoring model on the xplainable platform. The goal is to predict which leads are most likely to convert so the sales team can prioritise outreach -- and to hand them a ranked, explained list, not just a model.

## Getting Started

Ask the user:

> How would you like to work?
> - **Auto** -- I'll analyse your data, build preprocessing, train, iterate and deploy. You can redirect me anytime.
> - **Assisted** -- I'll explain my reasoning at each step and wait for your approval before proceeding.

Then find the data on the platform:
```
datasets_list_team_datasets()                                  → pick the dataset_id
datasets_upload_dataset(name, records=[...row dicts...])       → small tables given inline; large exports go through the platform UI
```

---

## Phase 1: Understand the Data

```
autotrain_summarize_by_dataset_id(dataset_id)                        → column statistics, types, missingness
datasets_preview_dataset_json(dataset_id, rows=100, sample=True)      → a RANDOM sample (CRM exports are often sorted by status)
```

Identify:
- The conversion target: "converted", "won", "is_customer", "deal_status", "closed_won", "qualified", etc.
- **Missing values**: lead data is sparse -- many fields left blank by reps or incomplete form fills. A blank is often a signal (no demo booked), not noise.
- **Class balance**: conversion rates are typically 5-25%. Flag severe imbalance (<5%).
- **High cardinality categoricals**: industry, job title, lead source, country
- **ID / irrelevant columns**: lead ID, contact name, email, phone, rep name -- must be dropped
- **Leakage**: deal value, close date, won date, an existing CRM lead score -- known only after or because of conversion; must be dropped
- **Datetime columns**: created date, first touch, last activity, demo date -- recency features come from these
- **Engagement metrics**: page views, email opens/clicks, form submissions -- usually the strongest signals

**If Assisted**: Present your analysis:
> Here's what I see in your data:
> - [X rows, Y columns]
> - Target: [column name] ([Z% conversion rate])
> - Key features: [list notable columns]
> - Issues to address: [missing values, high cardinality, leakage suspects]
> - Columns I'll drop: [IDs, leakage]
>
> Does this look right? Should I adjust anything?

---

## Phase 2: Build Preprocessing

```
preprocessing_list_available_transformers()          → catalogue + parameter names; never guess them
```

### Lead Scoring Preprocessing Playbook

**Always do:**
- Drop ID columns, contact names, email, phone, rep assignments (DropColumnsTransformer)
- Flag informative blanks before filling (MissingFlagTransformer on demo_date, phone, company size)
- Fill missing numerics with median, missing categoricals with "Unknown" (FillMissingTransformer)

**Datetime columns** (created_date, first_touch, last_activity, demo_date):
- **Recency is the strongest feature you can build**: days since last activity, days from creation to first touch (ExpressionTransformer)
- Extract month / quarter for seasonality (DateTimeExtractTransformer)

**High cardinality categoricals**:
- Job titles → top 15, industry → top 12, lead source → top 10 (CategoryCondenseTransformer)

**Company-level aggregation** (multiple contacts per company): GroupByAggTransformer on company_id for contact counts and total engagement -- only if the data actually has duplicate companies.

**Text columns** (notes, company_description): clean (TextCleanTransformer), then drop unless they carry structured tags.

**Engagement metrics and firmographics** (page_views, email_opens, annual_revenue, employee_count): keep them all, raw. "page_views = 23 adds +0.12" is what the sales team needs to hear.

### Dry-run, then create

```
preprocessing_preview_spec(dataset_id, spec={
    "version": "2.0",
    "steps": [
        {"id": "drop_ids", "type": "DropColumnsTransformer", "params": {"columns": ["lead_id", "contact_name", "email", "phone", "rep_name", "deal_value", "close_date"]}},
        {"id": "flag_demo", "type": "MissingFlagTransformer", "columns": ["demo_date"], "params": {"suffix": "_missing"}},
        {"id": "fill_numeric", "type": "FillMissingTransformer", "columns": ["annual_revenue", "employee_count", "page_views"], "params": {"strategies": {"annual_revenue": "median", "employee_count": "median", "page_views": 0}}},
        {"id": "fill_categorical", "type": "FillMissingTransformer", "columns": ["industry", "job_title", "lead_source"], "params": {"default": "Unknown"}},
        {"id": "condense_title", "type": "CategoryCondenseTransformer", "columns": ["job_title"], "params": {"max_categories": 15}},
        {"id": "condense_industry", "type": "CategoryCondenseTransformer", "columns": ["industry"], "params": {"max_categories": 12}},
        {"id": "extract_dates", "type": "DateTimeExtractTransformer", "columns": ["created_date"], "params": {"components": ["month", "quarter"], "drop_original": true}}
    ]
}, target_column="converted")
```
Read the deltas and safety findings, then:
```
preprocessing_create_preprocessor_from_spec(name="Lead Scoring Preprocessing v1", description=..., spec=spec)   → preprocessor_id, version_id
preprocessing_preview_from_data(version_id, sample_data=[rows as dicts])
```
Confirm engagement metrics survived, categoricals condensed sensibly, nothing important was dropped.

**If Assisted**: Show the plan and preview. Ask for approval.

---

## Phase 2b: Declare Feature Relationships

Lead data usually carries columns that are functions of other columns (an engagement score summed from opens and clicks, a rate computed from two counts) and a few structural implications (no email on file ⇒ zero opens; a lead source of "referral" ⇒ campaign fields empty). Declared once on the dataset, they stop the optimiser prescribing "more opens" without the emails that produce them.

```
datasets_infer_relationships(dataset_id="<dataset_id>", target_column="converted")
→ implies (never-co-occurring category pairs, with support), derived (exact arithmetic identities), monotonic_hints
```

Keep what is true by construction, drop coincidences (check the support), then commit:

```
datasets_set_relationships(
    dataset_id="<dataset_id>",
    derived={"engagement_score": "email_opens + link_clicks"},
    monotonic={"page_views": "increasing", "email_opens": "increasing", "days_since_last_activity": "decreasing"},
    notes={"derived": "score is the CRM sum of opens and clicks"}
)
→ relationships (revision), compiled rules, warnings
```

Declared `monotonic` directions are merged into training (explicit `monotonic_features` wins). Skip this phase if inference proposes nothing and you know of no dependencies.

---

## Phase 3: Train the Model

```
models_train_model(
    dataset_id="<dataset_id>",
    target_column="converted",
    model_name="Lead Scoring Model",
    model_description="Binary classifier predicting lead conversion likelihood",
    model_type="classification",
    preprocessor_version_id="<from Phase 2>",
    drop_columns=["lead_id", "contact_name", "email", "phone", "rep_name", "deal_value", "close_date"],
    monotonic_features={"page_views": "increasing", "email_opens": "increasing", "days_since_last_activity": "decreasing"},
    test_size=0.2
)
→ model_id, version_id, run_id, train_metrics, test_metrics, feature_importances, n_train, n_test
```
Small datasets (<2000 rows) are common in lead scoring: use `test_size=0.3`. Monotonic constraints on engagement and recency keep the model from learning that more engagement lowers conversion because of a few noisy rows.

---

## Phase 4: Evaluate & Iterate

### Read the results

**Overfitting check:** lead scoring overfits easily on small, noisy data -- watch the train/test gap closely; 3-5% is normal, more needs action.

**Benchmarks:** test AUC > 0.75 good, > 0.82 very good, < 0.65 means the data lacks signal or needs better recency features. Ignore accuracy at typical conversion rates.

**Feature importances:** engagement and recency should lead. If "rep_name" or "assigned_to" ranks high, you are scoring rep skill, not lead quality -- drop it.

### Inspect

```
models_get_model_profile(version_id)        # how each feature value moves conversion probability -- the sales team's favourite view
models_get_feature_info(version_id)
gpt_explain_model(model_id, version_id)
models_list_model_versions(model_id)        # versions + parameters per feature
```

### Iterate

**Refit the features that overfit** -- typically the sparse numerics -- with the same `drop_columns`, `test_size`, `seed`:
```
models_refit_features(
    version_id="<version_id>", dataset_id="<dataset_id>", target_column="converted",
    drop_columns=[...as training...], test_size=0.3,
    feature_params={
        "annual_revenue": {"l2": 50, "num_splines": 8},     # a handful of huge companies were driving a spike
        "page_views":     {"l2": 10},                         # wiggly tail
        "job_title":      {"l2": 30}                          # rare titles with extreme effects
    }
)
```
Compare test AUC and gap with the previous version; keep the better one.

**Retrain** when you add a recency feature, change condensing thresholds, or find leakage.

**If low performance:** the fix is almost always a better recency/engagement feature, not a knob.

**If Assisted**: Present versions side by side with concrete numbers and let the user pick.

---

## Phase 5: Deploy

```
preprocessing_check_signature(preprocessor_version_id="<pp version>", model_version_id="<best version>")
models_link_preprocessor(model_version_id, preprocessor_version_id)          # if not linked
deployments_deploy(model_version_id="<best version>")                         → deployment_id
deployments_activate_deployment(deployment_id)
deployments_generate_deploy_key(deployment_id, description="Lead scoring API key", days_until_expiry=90)
```

---

## Phase 6: Score the Pipeline

```
inference_score_dataset(dataset_id="<open leads dataset>", version_id="<deployed version>", top_n=100)
```
This is the deliverable: the top-N leads with their source columns and conversion probability, plus deciles with observed conversion counts. Turn the deciles into tiers the team can work:
- **Hot** (decile 1-2): route to senior reps today
- **Warm** (decile 3-5): nurture with targeted content
- **Cold** (rest): automated nurture only
Set the cut-offs from the decile table, not from a fixed 0.7/0.4 -- the right threshold depends on how many leads the team can actually work. Pass the RAW dataset; the linked preprocessor runs server-side. For ad-hoc rows, `inference_predict(records, model_id, version_id)`.

---

## Phase 7: Report

```
reports_create_report(run_id="<run_id from training>", report_name="Lead Scoring Model Report",
                      widgets=["binaryoverview", "metrics", "thresholdPlot", "prCurveRocCurve", "waterfallplot", "health"],
                      mode="dynamic", max_features=15)          → job_id
reports_get_job_status(job_id)                                  → poll until 'done'
```
The threshold plot matters most here: it is the volume-vs-quality trade-off the sales lead has to choose.

---

## Phase 8: Summary

> **Lead Scoring Model Complete**
>
> **Performance (version [id]):**
> - Test AUC: X (train X, gap Y%)
> - Top predictors: [top 3-5 features]
>
> **What was built:**
> - Preprocessor: [name] (version [id])
> - Model: [name] (model [id], deployed version [id])
> - Deployment: [id] (active), key expires [date]
> - Report: [id]
>
> **Scored pipeline:** [N leads scored; Hot/Warm/Cold counts and cut-offs; top-10 with the feature that put each there]
>
> **To iterate:** ask me to refit a feature, add a recency feature, or retrain. Lead mix shifts with campaigns -- plan to retrain quarterly.

---

## Lead Scoring Domain Knowledge

### Common predictors (high to low importance typically):
1. **Engagement recency** -- days since last visit, email open or form submission (build it explicitly)
2. **Engagement volume** -- page views, email clicks, content downloads
3. **Lead source** -- referrals and inbound convert 3-5x better than cold outbound
4. **Company fit** -- revenue, employee count, industry alignment with the ICP
5. **Job title / seniority** -- decision-makers convert differently from researchers
6. **Behavioural signals** -- pricing page visits, demo requests, case-study downloads

### Red flags:
- **Deal amount / value** as a feature = leakage (known only after conversion)
- **Close date / won date** = definite leakage
- **Existing CRM lead score** = circular; remove it
- **Rep name** with high importance = you are scoring rep performance, not lead quality
- **Test AUC > 0.95** on lead data almost always means leakage somewhere

### Preprocessing priorities:
- Engagement metrics are gold -- never drop them; a missing count is usually 0, not "unknown"
- NEVER scale numeric columns
- Job titles have extreme cardinality -- always condense
- Date features should express recency, not absolute dates
- Blank `demo_date` means no demo was booked -- flag it, don't impute it
