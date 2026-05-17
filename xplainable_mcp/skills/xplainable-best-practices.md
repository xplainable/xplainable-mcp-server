# xplainable Best Practices

This document defines the core principles for building models with xplainable. All skills inherit these rules. If a skill-specific instruction conflicts with this document, this document wins.

---

## Explainability First

xplainable models are inherently explainable. Every design decision should preserve this.

### Never scale numeric features

Do NOT use StandardScaler, MinMaxScaler, RobustScaler, PowerTransformer, QuantileTransformer, or any other scaling/normalisation on numeric columns.

**Why:** Feature contributions are expressed in original units. "monthly_charges = 72.50 adds +0.15 to churn probability" is meaningful to stakeholders. After scaling, "monthly_charges = 1.23 adds +0.15" is meaningless. The model handles raw numeric values natively -- scaling adds no predictive benefit and destroys interpretability.

### Never use encoding that obscures categories

Do NOT use OrdinalEncoder on nominal categories (it implies false ordering). OneHotEncoder is acceptable when needed but prefer keeping categories as-is when possible -- xplainable handles categorical features natively.

### Preserve original column names

When creating derived features (datetime extraction, expressions), use descriptive names that a non-technical stakeholder can understand. "signup_date_dayofweek" is good. "feature_42" is not.

---

## Preprocessing Rules

### What to do:
- **Drop irrelevant columns**: IDs, names, emails, phone numbers, row indices (DropColumnsTransformer)
- **Fill missing values**: median for numeric, mode or "Unknown" for categorical (FillMissingTransformer)
- **Extract datetime components**: year, month, dayofweek, quarter, is_weekend (DateTimeExtractTransformer)
- **Condense high cardinality categoricals**: columns with >15 unique values (CategoryCondenseTransformer)
- **Clean text before dropping**: lowercase, strip whitespace, remove HTML (TextCleanTransformer)
- **Create meaningful derived features**: ratios, differences, days-between using ExpressionTransformer
- **Aggregate when appropriate**: GroupByAggTransformer for multi-row-per-entity data

### What NOT to do:
- Do NOT scale or normalise numeric columns
- Do NOT one-hot encode unless the model specifically requires it (xplainable handles categories natively)
- Do NOT impute values that are meaningfully missing (e.g., blank "demo_date" means no demo -- fill with a sentinel, not the mean)
- Do NOT over-engineer features before training -- train first, iterate based on results
- Do NOT transform the target column in preprocessing -- handle it via the `target_column` parameter in `train_model`

---

## Training Rules

### Start simple, iterate based on evidence:
1. Train with default hyperparameters first (`max_depth=8`)
2. Look at train vs test metrics before adjusting anything
3. Only change one thing at a time so you can attribute improvement

### Hyperparameter guidance:
- `max_depth`: Controls model complexity. Lower = simpler, less overfitting. Higher = more complex, risk of overfitting.
  - Start at 8. Reduce to 5-6 if overfitting. Increase to 10-12 if underfitting.
- `min_leaf_size`: Minimum fraction of data in a leaf. Higher = more conservative.
  - Start at 0.0001. Increase to 0.01-0.05 if overfitting on small datasets.
- `min_info_gain`: Minimum information gain to justify a split. Higher = fewer splits.
  - Start at 0.0001. Usually doesn't need adjustment.

### Train/test split:
- Default 80/20 split is good for most datasets
- For small datasets (<2000 rows): consider 70/30 and reduce max_depth
- Always check BOTH train and test metrics

---

## Evaluation Rules

### Overfitting detection:
- Compare train metric vs test metric (accuracy, AUC, R2)
- Gap > 5-8% = overfitting. Reduce complexity.
- Gap < 2% = good generalisation

### For classifiers:
- Primary metric: **AUC** (robust to class imbalance)
- Secondary: precision, recall, F1 (depend on threshold choice)
- Accuracy is misleading with imbalanced classes -- do not rely on it alone
- Always inspect the confusion matrix

### For regressors:
- Primary metric: **R2** (explained variance)
- Secondary: RMSE, MAE
- Check if errors are systematic (model consistently over/under-predicts in certain ranges)

### Feature importance sanity check:
- Top features should make domain sense
- Any single feature >40% importance = investigate for leakage
- ID-like columns should never appear = model memorising
- Post-outcome features appearing = data leakage (drop and retrain)

---

## Iteration Loop

The core iteration pattern for any xplainable skill:

```
Train → Evaluate → Inspect → Decide → (Refit or Adjust Preprocessing) → Evaluate → Deploy
```

### Rapid Refit vs Full Retrain

xplainable models support **rapid refit** via `refit_model()`. This is orders of magnitude faster than retraining because it reuses the pre-computed feature partitions (tree splits) and only recomputes scores.

**Use `refit_model()` when changing hyperparameters:**
- max_depth, min_leaf_size, min_info_gain
- weight, power_degree, sigmoid_exponent, tail_sensitivity
- This is instant -- Claude can try dozens of parameter combinations in seconds
- Each refit returns fresh train/test metrics for comparison

**Use `train_model()` (full retrain) only when:**
- Changing the feature set (dropping/adding columns)
- Changing the preprocessing pipeline
- Using different training data

### Typical iteration flow:
```
1. train_model(max_depth=8)                        → baseline metrics
2. refit_model(max_depth=6)                        → global reduction, less overfitting?
3. refit_model(feature_params={...per-feature...})  → targeted tuning
4. Compare versions → deploy the best
```

### Per-feature tuning (use `feature_params`)

Use `feature_params` to tune multiple features with different settings in ONE refit call. This avoids repeated data loads and lets you give each feature only the complexity it needs.

**Numeric features** -- tune `max_depth`, `min_leaf_size`:
- These control the number of splits. Fewer splits = less overfitting.
- High importance, clear signal: depth 4-6
- Medium importance: depth 3-5
- Low importance (<3%): depth 2, or reduce `weight` to dampen influence

**Categorical features** -- tune `weight`, `tail_sensitivity` (NOT depth):
- `max_depth` has little effect on categoricals. A feature with 3 unique values has at most 3 splits regardless of depth.
- `weight`: controls how strongly the feature affects the score. Reduce to 0.5-0.8 for noisy or low-importance categoricals.
- `tail_sensitivity`: controls emphasis on rare categories. Reduce for condensed categoricals where the "Other" bucket is noisy.
- Binary features (Yes/No): weight 0.8-1.0, leave depth alone.

**Example:**
```
refit_model(
    version_id="<version_id>",
    dataset_id="<dataset_id>",
    target_column="<target>",
    drop_columns=[...],
    feature_params={
        # Numeric: reduce splits
        "tenure": {"max_depth": 4},
        "monthly_charges": {"max_depth": 5},
        "low_importance_numeric": {"max_depth": 2, "weight": 0.5},
        # Categorical: adjust influence
        "contract": {"tail_sensitivity": 0.8},
        "streaming_tv": {"weight": 0.5},
    }
)
```

**Goal: minimise splits while maintaining AUC.** Fewer splits = simpler model = less overfitting = more explainable.

### When to iterate preprocessing (requires full retrain):
- Missing value strategy isn't working (too many rows dropped, imputation distorting)
- Important datetime features not extracted
- High cardinality column needs different condensing threshold
- Derived feature could capture a known domain relationship

### When to iterate hyperparameters (use rapid refit):
- Overfitting: reduce max_depth (numeric), reduce weight (categorical)
- Underfitting: increase max_depth, increase weight
- Calibration: adjust weight, power_degree, sigmoid_exponent
- Tail behaviour: adjust tail_sensitivity on condensed categoricals

### When to stop iterating:
- Test metrics are stable across multiple refits
- Train/test gap is small (<5%)
- Feature importances make domain sense
- Further adjustments show diminishing returns

---

## Deployment Rules

### Always link the preprocessor before deploying:
```
models_link_preprocessor(model_version_id, preprocessor_version_id)
```
This ensures incoming prediction data is transformed identically to training data.

### Always set up monitoring:
- Prediction drift: detects when the model's output distribution changes
- Set alert thresholds appropriate to the domain (tighter for high-stakes, looser for exploratory)
- Plan to retrain periodically -- most models degrade over time as data distributions shift

---

## Communication Rules

### In Auto mode:
- Execute the workflow, present results at the end
- Pause only if something looks wrong (possible leakage, very low performance, data quality issues)

### In Assisted mode:
- Explain your reasoning at each step before executing
- Show data analysis, preprocessing plan, metrics, and iteration rationale
- Use concrete numbers, not vague language ("AUC improved from 0.78 to 0.83" not "performance got better")
- When presenting feature contributions from the model profile, translate them into business language

### Always:
- Present feature contributions in original units (not scaled, not encoded)
- When recommending actions, explain WHY using the model's explainability
- Flag any data quality issues or potential leakage immediately
