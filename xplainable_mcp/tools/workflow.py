"""
Workflow service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp
from ..server import get_client, XP_ICON

logger = logging.getLogger(__name__)


# Workflow Tools
# ============================================

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_create_report(run_id: str, report_name: str, goal: str = ''):
    """
    Generate a shareable report for a training run.
    
    Starts the platform's report wizard (LLM-written widgets and
    narrative) for the training run and waits for it to finish —
    typically under a minute, up to five. run_id is the training run
    id (from workflow_train_model); goal steers the report's
    narrative. Returns report_id and version_id of the generated
    report; view and share it in the platform UI. The success dict
    always reports status "completed", even though the API's raw
    job status for success is "done".

    Category: workflow
    Workflow: Step 9 of workflow. Run after: workflow_train_model.
    """
    try:
        client = get_client()
        result = client.workflow.create_report(run_id, report_name, goal)
        logger.info(f"Executed workflow.create_report")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_create_report: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_decide(run_id: str, approve: Optional[bool] = None, choice: Optional[int] = None, custom: Optional[str] = None):
    """
    Submit a human-in-the-loop decision on a paused training run.
    
    Call when workflow_wait_for_update returns a pending_decision.
    Pass exactly one of: approve=True to accept the recommended /
    affirmative option (approve=False to skip/reject), choice=N to pick
    option N from pending_decision.options, or custom="..." for a
    free-form answer (label selection only; note: the platform may
    fall back to the recommended option — verify the outcome via
    workflow_wait_for_update). Returns what was submitted and the
    next step; on problems returns a coaching dict instead of
    raising.

    Category: workflow
    Workflow: Step 4 of workflow. Run after: workflow_wait_for_update.
    """
    try:
        client = get_client()
        result = client.workflow.decide(run_id, approve, choice, custom)
        logger.info(f"Executed workflow.decide")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_decide: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_deploy_model(model_id: str, version_id: Optional[str] = None):
    """
    Deploy a model version and return everything needed to call it.
    
    Idempotent — safe to re-run: reuses an existing deployment for the
    version instead of creating duplicates, activates it only if
    inactive (verified by read-back, retried once), and always
    generates a fresh deploy key (key secrets are not retrievable
    later). If version_id is omitted, the model's active (or latest)
    version is used. Returns deployment_id, endpoint_url, deploy_key,
    and sample_payload: POST sample_payload-shaped JSON to endpoint_url
    with header api_key=<deploy_key>.

    Category: workflow
    Workflow: Step 5 of workflow. Run after: workflow_train_model.
    """
    try:
        client = get_client()
        result = client.workflow.deploy_model(model_id, version_id)
        logger.info(f"Executed workflow.deploy_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_deploy_model: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_explain_model(model_id: str, version_id: Optional[str] = None):
    """
    Summarise how a trained model makes its predictions.
    
    Fetches the model's profile and digests it client-side (raw
    profiles are too large for LLM context) into the base value and
    the top features by importance, each with an effect direction
    (increasing/decreasing/mixed/flat for numeric features,
    categorical otherwise) and a one-line summary. If version_id is
    omitted, the model's active (or latest) version is used.

    Category: workflow
    Workflow: Step 7 of workflow. Run after: workflow_train_model.
    """
    try:
        client = get_client()
        result = client.workflow.explain_model(model_id, version_id)
        logger.info(f"Executed workflow.explain_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_explain_model: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_list_assets():
    """
    List the team's models, datasets, and deployments in one call.
    
    Start here: shows what exists before training, deploying, or
    optimising anything.

    Category: workflow
    Workflow: Step 1 of workflow.
    """
    try:
        client = get_client()
        result = client.workflow.list_assets()
        logger.info(f"Executed workflow.list_assets")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_list_assets: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_optimise_model(model_id: str, objective: str, dataset_id: str, constraints: Optional[dict] = None, version_id: Optional[str] = None):
    """
    Run a prescriptive optimisation over a hosted dataset.
    
    Hides the raw optimiser chain: deploys the model version first
    (the platform rejects optimiser runs against undeployed
    versions), creates an optimiser + policy version, and runs it
    synchronously against dataset_id (its columns must match the
    model's features). objective is 'minimize' (lowest prediction
    per row) or 'pareto' (cost-vs-prediction frontier per row).
    constraints (optional): {"immutable": [feature, ...] held at
    each row's current value, "bounds": {feature: [min, max] or
    [allowed categories]} — bounds may only tighten the model's
    configured ranges}. Returns optimiser_id, run_id and up to 10
    per-row prescriptions ({row, optimal_features, prediction,
    total_cost} for 'minimize'; {row, selected, reached_target} for
    'pareto'); the full result stays on the stored run.

    Category: workflow
    Workflow: Step 6 of workflow. Run after: workflow_deploy_model.
    """
    try:
        client = get_client()
        result = client.workflow.optimise_model(model_id, objective, dataset_id, constraints, version_id)
        logger.info(f"Executed workflow.optimise_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_optimise_model: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_predict(model_id: str, rows: List[dict], version_id: Optional[str] = None):
    """
    Score feature rows with a trained model.
    
    rows is a list of {feature: value} dicts, one per row to score,
    all sharing the same keys (the model's input features; column
    order is taken from the first row). Uses the platform's
    inference route, so any trained version works — no deployment
    needed. If version_id is omitted, the model's active (or
    latest) version is used. Returns predictions in the same order
    as rows.

    Category: workflow
    Workflow: Step 8 of workflow. Run after: workflow_train_model.
    """
    try:
        client = get_client()
        result = client.workflow.predict(model_id, rows, version_id)
        logger.info(f"Executed workflow.predict")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_predict: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_train_model(dataset_id: str, goal: str, model_name: str, model_description: str = ''):
    """
    Train an explainable model on a hosted dataset.
    
    Stages the dataset, then starts a run that pauses for approval at
    label selection, training config, and deployment. Follow with
    workflow_wait_for_update(run_id).

    Category: workflow
    Workflow: Step 2 of workflow. Run after: workflow_list_assets.
    """
    try:
        client = get_client()
        result = client.workflow.train_model(dataset_id, goal, model_name, model_description)
        logger.info(f"Executed workflow.train_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_train_model: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_wait_for_update(run_id: str, since_event: int = 0, timeout: int = 60):
    """
    Long-poll a training run for progress.
    
    Returns as soon as new events (past since_event), a pending
    decision, or a terminal status appear — or after timeout seconds.
    Pass the returned next_since_event into the next call.

    Category: workflow
    Workflow: Step 3 of workflow. Run after: workflow_train_model.
    """
    try:
        client = get_client()
        result = client.workflow.wait_for_update(run_id, since_event, timeout)
        logger.info(f"Executed workflow.wait_for_update")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in workflow_wait_for_update: {e}")
        raise
