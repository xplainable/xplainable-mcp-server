# Design: Complete MCP Server for Full ML Workflow

## Context

The xplainable MCP server needs to support the full ML lifecycle driven entirely by Claude as the agent, with skills providing domain-specific guidance. No black-box orchestration (autotrain agentic pipeline) -- Claude reasons through every step with full visibility.

## Architecture

```
Claude Desktop / Claude Code
    │  (reads skill instructions)
    │
    ▼
Skills (markdown in project instructions)
    │  define workflow steps + domain guidance
    │
    ▼
MCP Tools (xplainable-mcp-server)
    │  execute individual operations
    │
    ├── Preprocessing tools  → xplainable-preprocessing (local)
    ├── Training tool        → xplainable library (local) + API upload
    ├── Model inspection     → xplainable API
    ├── Deployment tools     → xplainable API
    ├── Report tools         → xplainable API
    └── Monitor tools        → xplainable API
```

Zero dependency on the autotrain microservice. Training happens locally in the MCP server process using the xplainable library, then the fitted model is uploaded to the API as JSON.

## Mode Selection

Each skill starts with a mode choice:

- **Auto**: Claude runs the full pipeline, makes all decisions based on skill domain guidance. User can interrupt anytime.
- **Assisted**: Claude proposes each step, explains reasoning, waits for approval. Can iterate at any step.

## Workflow Phases

### Phase 1: Understand Data

Claude reads the CSV directly and reasons about it. No autotrain summarize needed.

**What Claude does (reasoning):**
- Reads first N rows of the CSV
- Identifies column types, missing values, distributions, cardinality
- Identifies the target column based on skill guidance
- Spots potential issues (class imbalance, high cardinality, datetime columns)

**MCP tools used:** None -- Claude has direct file access.

### Phase 2: Build Preprocessing

**MCP tools:**
- `preprocessing_list_available_transformers()` -- get transformer catalog
- `preprocessing_create_preprocessor_from_spec(name, desc, spec, sample_data)` -- create pipeline
- `preprocessing_preview_from_data(version_id, sample_data)` -- see before/after
- `preprocessing_update_version_from_spec(version_id, spec, sample_data)` -- iterate

**What Claude does (reasoning):**
- Designs PipelineSpec based on data analysis + skill domain knowledge + transformer catalog
- Reviews the preview, adjusts if needed

### Phase 3: Train

**MCP tools:**
- `train_model(file_path, target_column, model_name, model_description, ...)` -- NEW

**What the tool does internally:**
1. `pd.read_csv(file_path)`
2. If `preprocessor_version_id` provided: download fitted pipeline from API, transform data
3. Drop specified columns, split x/y on target_column
4. 80/20 train/test split
5. `XClassifier().fit(x_train, y_train)` (or XRegressor)
6. Evaluate on both train and test sets
7. `client.models.create_model(model, name, desc, x, y)` to upload
8. Return: model_id, version_id, train_metrics, test_metrics, feature_importances

### Phase 4: Evaluate & Iterate

**MCP tools:**
- `get_model_profile(model_id, version_id)` -- feature contribution curves
- `get_model_evaluation(version_id, partition_id)` -- detailed metrics
- `get_feature_info(version_id)` -- feature health/distributions

**What Claude does (reasoning):**
- Compares train vs test metrics (overfitting detection)
- Inspects feature contributions (identifies noisy/overfit features)
- Decides whether to iterate:
  - Adjust preprocessing (loop to Phase 2)
  - Change hyperparameters (loop to Phase 3)
  - Drop features (loop to Phase 3)
  - Accept and deploy (proceed to Phase 5)

### Phase 5: Deploy

**MCP tools:**
- `models_link_preprocessor(model_version_id, preprocessor_version_id)`
- `deployments_deploy(model_version_id)` -> deployment_id
- `deployments_activate_deployment(deployment_id)`
- `deployments_generate_deploy_key(deployment_id)` -> API key

### Phase 6: Report & Monitor

**MCP tools:**
- `reports_create_report_sync(run_id, report_name, widgets, ...)` -> report
- `monitors_create_monitor(...)` -> monitor_id
- `monitors_create_alert_rule(monitor_id, ...)` -> alert rule

### Phase 7: Summary

Claude presents: model metrics, deployment endpoint + API key, report link, monitor config, and instructions for making predictions.

## New MCP Tools Required

### 1. `train_model` (ModelsClient)

```python
@mcp_tool(category=MCPCategory.WRITE)
def train_model(
    self,
    file_path: str,
    target_column: str,
    model_name: str,
    model_description: str = "",
    model_type: str = "classifier",      # "classifier" or "regressor"
    preprocessor_version_id: Optional[str] = None,
    drop_columns: Optional[List[str]] = None,
    test_size: float = 0.2,
    max_depth: int = 8,
    min_info_gain: float = 0.0001,
    min_leaf_size: float = 0.0001,
    weight: float = 1.0,
    power_degree: float = 1.0,
    sigmoid_exponent: float = 0.0,
    tail_sensitivity: float = 1.0,
) -> dict:
```

Returns:
```python
{
    "model_id": "...",
    "version_id": "...",
    "model_type": "classifier",
    "train_metrics": {
        "accuracy": 0.92,
        "roc_auc": 0.95,
        "confusion_matrix": [[...], [...]],
        ...
    },
    "test_metrics": {
        "accuracy": 0.87,
        "roc_auc": 0.89,
        "confusion_matrix": [[...], [...]],
        ...
    },
    "feature_importances": [
        {"feature": "tenure", "importance": 0.23},
        {"feature": "monthly_charges", "importance": 0.18},
        ...
    ],
    "n_train": 5600,
    "n_test": 1400,
}
```

### 2. `get_model_profile` (ModelsClient)

```python
@mcp_tool(category=MCPCategory.READ)
def get_model_profile(self, version_id: str) -> dict:
```

### 3. `get_model_evaluation` (ModelsClient)

```python
@mcp_tool(category=MCPCategory.READ)
def get_model_evaluation(self, partition_id: str) -> dict:
```

### 4. `get_feature_info` (ModelsClient)

```python
@mcp_tool(category=MCPCategory.READ)
def get_feature_info(self, version_id: str) -> dict:
```

## Tools to Strip @mcp_tool (no longer needed for skills)

### Autotrain (strip all 9):
- summarize_dataset, generate_goals, generate_labels
- generate_feature_engineering, generate_insights, visualize_data
- start_autotrain, train_manual, check_training_status

### Agentic (strip all 13):
- start_run, get_run_state, get_pending_decision, submit_decision
- get_phases, cancel_run, skip_phase, resume_run
- send_chat, get_chat_history, retrain
- get_preprocessing_dag, get_column_lineage

## Skill Delivery

### Repository structure:
```
xplainable/xplainable-skills
├── README.md                          # Setup: install MCP server + add skill
├── skills/
│   ├── churn-prediction.md            # First skill
│   └── binary-classification.md       # Generic (extracted from churn)
└── sample-data/
    └── telco_churn.csv
```

### One-liner install (stretch goal):
```bash
npx xplainable-mcp-setup
```

### Skill content structure:
1. Mode selection prompt (auto vs assisted)
2. Phase-by-phase instructions for Claude
3. Domain-specific guidance (what to look for, preprocessing recommendations)
4. Iteration guidance (overfitting detection, feature selection heuristics)

## Final Tool Surface

After stripping autotrain + agentic and adding new tools:

| Service | Tools | Notes |
|---------|-------|-------|
| Models | 5 + 4 new = 9 | +train_model, +get_model_profile, +get_model_evaluation, +get_feature_info |
| Preprocessing | 12 | Unchanged from Phase 1-2 implementation |
| Deployments | 10 | Unchanged |
| Datasets | 7 | Unchanged |
| Monitors | 10 | Unchanged |
| Reports | 3 | Unchanged |
| Inference | 2 | Unchanged |
| GPT | 3 | Unchanged |
| Misc | 7 | Unchanged |
| Runs | 2 | Unchanged |
| Autotrain | 0 | All 9 stripped |
| Agentic | 0 | All 13 stripped |
| **Total** | **65** | Down from 85, more focused |

## Verification

1. Train a churn model end-to-end using only MCP tools
2. Verify train/test metric split detects overfitting when max_depth is too high
3. Verify preprocessing iteration (change spec, retrain, compare metrics)
4. Verify deployment + prediction works
5. Test with Claude Desktop using the churn skill
