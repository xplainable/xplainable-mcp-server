# xplainable Best Practices

This document defines the core principles for building models with xplainable through the MCP tools. All skills inherit these rules. If a skill-specific instruction conflicts with this document, this document wins.

Every model you train through these tools is an **XGM (v2) model**: an additive model of per-feature shape functions (Gaussian-basis splines for numeric features, per-level effects for categorical features, plus a few automatically selected pairwise interactions). Two consequences shape everything below:

- There are **no training hyperparameters**. `models_train_model` takes data, features, preprocessing and constraints — nothing else. You improve a model by changing what it sees (features, preprocessing), what it must respect (monotonic constraints), and, after training, by refitting individual features with `models_refit_features`.
- Every feature's effect is a curve you can read (`models_get_model_profile`). Preserve that.

---

## Explainability First

### Never scale numeric features

Do NOT use StandardScaler, MinMaxScaler, RobustScaler, PowerTransformer, QuantileTransformer, or any other scaling/normalisation on numeric columns.

**Why:** Feature contributions are expressed in original units. "monthly_charges = 72.50 adds +0.15 to churn probability" is meaningful to stakeholders. After scaling, "monthly_charges = 1.23 adds +0.15" is meaningless. The model handles raw numeric values natively -- scaling adds no predictive benefit and destroys interpretability.

### Never use encoding that obscures categories

Do NOT ordinal-encode nominal categories (it implies false ordering). Do NOT one-hot encode -- the model handles categorical features natively, one effect per level.

### Preserve original column names

When creating derived features (datetime extraction, expressions), use descriptive names that a non-technical stakeholder can understand. "signup_date_dayofweek" is good. "feature_42" is not.

---

## Preprocessing Rules

Preprocessing is a **PipelineSpec**: `{"version": "2.0", "steps": [{"id", "type", "columns", "params"}, ...]}`. Get the catalogue and parameter names from `preprocessing_list_available_transformers()` -- never guess parameters.

### What to do:
- **Drop irrelevant columns**: IDs, names, emails, phone numbers, row indices (DropColumnsTransformer)
- **Fill missing values**: median for numeric, mode or "Unknown" for categorical (FillMissingTransformer, `strategies` per column)
- **Flag informative missingness** before filling when a blank means something (MissingFlagTransformer)
- **Extract datetime components**: year, month, dayofweek, quarter (DateTimeExtractTransformer, `components`)
- **Condense high cardinality categoricals**: columns with >15 unique values (CategoryCondenseTransformer, `max_categories`)
- **Clean text before dropping**: lowercase, strip whitespace, remove HTML (TextCleanTransformer, `operations`)
- **Create meaningful derived features**: ratios, differences, days-between (ExpressionTransformer, `expression` + `output_column`; wrap column names containing spaces in backticks)
- **Aggregate when appropriate**: GroupByAggTransformer for multi-row-per-entity data

### Dry-run before creating

`preprocessing_preview_spec(dataset_id, spec, target_column)` runs the spec against the real dataset **without persisting anything** and reports per-step column deltas plus safety findings (steps that collapse rows, steps that touch the target). Use it first; only then `preprocessing_create_preprocessor_from_spec`. To revise, `preprocessing_add_version_from_spec` on the same preprocessor rather than creating a new one.

### What NOT to do:
- Do NOT scale or normalise numeric columns
- Do NOT one-hot encode
- Do NOT impute values that are meaningfully missing (a blank "demo_date" means no demo -- flag it or fill with a sentinel, not the median)
- Do NOT touch the target column in preprocessing -- it is selected via `target_column` in `models_train_model`
- Do NOT over-engineer before the first model -- train, read the results, then iterate

---

## Training Rules

`models_train_model(dataset_id, target_column, model_name, model_type, preprocessor_version_id, drop_columns, monotonic_features, test_size, seed)`

- `model_type` is `"classification"` or `"regression"`.
- Training is synchronous and server-side (a minute or two on real data). It returns `model_id`, `version_id`, `run_id`, `train_metrics`, `test_metrics`, `feature_importances`, `n_train`, `n_test`. Keep the `run_id` -- reports hang off it.
- **What you control at train time**: the feature set (`drop_columns` / `feature_columns`), the preprocessor, monotonic constraints, and the split (`test_size`, `seed`). Nothing else. There is no `max_depth`.

### Monotonic constraints

`monotonic_features={"Tenure": "decreasing", "Monthly Charges": "increasing"}` forces a numeric feature's effect to move in one direction. Use them when the domain relationship is known and a model that violated it would be wrong, not just surprising -- price should not lower churn, tenure should not raise it. They are hard constraints (a monotone QP), so they also stop the optimiser prescribing nonsense like "raise the price to reduce churn". Constraints on non-numeric features are ignored.

### Start simple, iterate based on evidence:
1. Train with all sensible features and the constraints you are sure of.
2. Read train vs test metrics and the importances **before** changing anything.
3. Change one thing at a time so you can attribute the improvement.
4. Keep `seed` and `test_size` fixed across iterations so metrics are comparable.

### Train/test split:
- Default 80/20 is right for most datasets. For small datasets (<2000 rows) use 70/30.
- Always check BOTH train and test metrics.

---

## Evaluation Rules

### Overfitting detection:
- Compare train metric vs test metric (AUC, R2)
- Gap > 5-8% = overfitting. Simplify: stronger `l2` or fewer `num_splines` on the wiggliest high-importance features (see Iteration), or drop noisy features.
- Gap < 2% = good generalisation

### For classifiers:
- Primary metric: **AUC** (robust to class imbalance)
- Secondary: precision, recall, F1 (depend on threshold choice)
- Accuracy is misleading with imbalanced classes -- do not rely on it alone
- Probabilities are calibrated on a holdout at train time. Check they are usable, not just ranked: `inference_score_dataset` returns deciles with observed positive counts -- decile 1 should carry far more positives than decile 10, and probabilities should not pile up on a handful of values.

### For regressors:
- Primary metric: **R2** (explained variance)
- Secondary: RMSE, MAE
- Check if errors are systematic (consistently over/under-predicting in certain ranges)

### Feature importance sanity check:
- Top features should make domain sense
- Any single feature >40% importance = investigate for leakage
- ID-like columns should never appear = model memorising
- Post-outcome features appearing = data leakage (drop and retrain)
- Keys shaped `a_&_b` are automatically selected interactions -- read them as "the effect of a depends on b"

---

## Iteration Loop

```
Train → Evaluate → Inspect → Decide → (Refit features  |  Retrain) → Evaluate → Deploy
```

### Inspect

- `models_get_feature_info(version_id)` -- per-feature health (missingness, cardinality, drift-prone columns)
- `models_get_model_profile(version_id)` -- the shape of every feature's effect; look for wiggles that are noise, not signal, and for directions that contradict the domain
- `gpt_explain_model(model_id, version_id)` -- a narrative digest of importances and profile
- `models_list_model_versions(model_id)` -- every version with its `parameters`: `{feature: {model_class, num_splines, l2, d2, spacing, monotonic, ...}}`. **Read these before changing them.**

### Refit features vs retrain

**`models_refit_features(version_id, dataset_id, target_column, feature_params, drop_columns, test_size, seed)`** re-solves the named features against the residual of everything else and produces a **new version** with fresh train/test metrics, importances and profile. Everything you do not name is untouched. Pass the same `drop_columns`, `test_size` and `seed` you trained with so the metrics are comparable. It costs roughly half a training run (probabilities are recalibrated), not seconds.

`feature_params` is `{feature: {knob: value}}`. Knobs:

| Feature type | Knob | Effect | Reach for it when |
|---|---|---|---|
| numeric | `l2` | shrinkage toward zero effect | the feature overfits (wiggly, high importance, big train/test gap) -- raise it (x5 to x50) |
| numeric | `num_splines` | number of basis functions | the curve is jagged with no domain reason -- lower it (default 20; try 8-12) |
| numeric | `d2` | second-derivative (smoothness) penalty | you want the curve smoother without flattening it |
| numeric | `spacing` | spacing penalty | rarely -- leave alone |
| numeric | `monotonic` | `"increasing"` / `"decreasing"` / `null` | the domain direction is known and the profile violates it (or to remove a constraint) |
| numeric | `monotonic_penalty` | strength of the monotone constraint | rarely -- leave alone |
| categorical | `l2` | shrinkage of level effects | rare levels get extreme effects (noisy "Other" buckets, tiny categories) |

Interaction features (`a_&_b`) cannot be refitted; refit their component features instead.

**Use `models_refit_features` when** a specific feature's curve is the problem: overfitting, noise, a wrong direction, an extreme rare category.

**Use `models_train_model` again when** the feature set, preprocessing, target or training constraints change, or the data changed.

### Typical iteration flow:
```
1. models_train_model(...)                                          → baseline, note version_id + run_id
2. models_get_model_profile / models_get_feature_info               → which curves look wrong?
3. models_list_model_versions(model_id)                             → current knobs per feature
4. models_refit_features(version_id, ..., feature_params={
       "Tenure Months":   {"l2": 20, "monotonic": "decreasing"},
       "Monthly Charges": {"l2": 10, "monotonic": "increasing"},
       "City":            {"l2": 50}})                              → new version; compare test AUC and gap
5. Repeat with one change at a time, or retrain if the fix is a feature/preprocessing change
6. Deploy the best version
```

### When to stop iterating:
- Test metrics are stable across versions
- Train/test gap is small (<5%)
- Feature importances and profile curves make domain sense
- Further changes show diminishing returns

---

## Deployment Rules

### Confirm the preprocessor travels with the model:
```
preprocessing_check_signature(preprocessor_version_id, model_version_id)   → {"signatures_match": true}
models_link_preprocessor(model_version_id, preprocessor_version_id)        # if not already linked
```
Inference applies the linked preprocessor to incoming raw rows, so predictions see exactly the transform the model was trained on.

### Deploy, activate, key:
```
deployments_deploy(model_version_id)              → deployment_id
deployments_activate_deployment(deployment_id)
deployments_generate_deploy_key(deployment_id, description=..., days_until_expiry=90)
```

### Monitoring:
There are no monitoring tools on this surface; drift alerts are configured in the platform UI. Recommend a retrain cadence (quarterly for most business data, faster when the input mix changes) and say why.

---

## Communication Rules

### In Auto mode:
- Execute the workflow, present results at the end
- Pause only if something looks wrong (possible leakage, very low performance, data quality issues)

### In Assisted mode:
- Explain your reasoning at each step before executing
- Show data analysis, preprocessing plan, metrics, and iteration rationale
- Use concrete numbers ("AUC improved from 0.78 to 0.83", not "performance got better")
- Translate profile curves into business language

### Always:
- Present feature contributions in original units (not scaled, not encoded)
- When recommending actions, explain WHY using the model's explainability
- Flag any data quality issue or potential leakage immediately
- Say which version_id every number came from
