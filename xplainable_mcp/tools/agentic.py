"""
Agentic pipeline MCP tools — the primary XGM v2 training workflow.

All v2 training happens on Xplainable servers: agentic_start_run kicks off
a server-side run (algorithm="xgm" by default) and the remaining tools
poll, steer, and finish it. The MCP host never fits a v2 model locally.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp
from ..server import get_client, XP_ICON

logger = logging.getLogger(__name__)


def _dump(result):
    """Normalise client return types for MCP transport."""
    if hasattr(result, 'model_dump'):
        return result.model_dump()
    elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
        return [item.model_dump() for item in result]
    return result


# Agentic Tools
# ============================================

@mcp.tool(icons=[XP_ICON])
def agentic_start_run(
    model_name: str,
    model_description: str = "",
    auto_mode: bool = True,
    require_approval: Optional[List[str]] = None,
    auto_apply_safe_features: bool = True,
    auto_deploy: bool = False,
    run_id: Optional[str] = None,
    user_query: Optional[str] = None,
    phase_plan: Optional[List[str]] = None,
    algorithm: str = "xgm",
):
    """
    Start a server-side agentic ML training run (XGM v2 by default).

    This is the primary way to train a model: upload a dataset, call
    datasets/autotrain summarize to get a run_id, then start the run and
    poll agentic_get_run_state until it completes (runs take ~10 minutes).

    With auto_mode=True (default) the pipeline proceeds through all phases
    without pausing. Set auto_mode=False and require_approval to pause for
    decisions (see agentic_get_pending_decision / agentic_submit_decision).

    Args:
        model_name: Name for the model being trained
        model_description: Description of the model's purpose
        auto_mode: Proceed through phases automatically (default True)
        require_approval: Phases requiring human approval when auto_mode=False
        auto_apply_safe_features: Automatically apply safe feature engineering
        auto_deploy: Automatically deploy the model after training
        run_id: Run ID from dataset summarization (seeds the run's data)
        user_query: Natural language description of what to build
        phase_plan: Optional ordered list of phases to execute
        algorithm: "xgm" (v2, default) or "xplainable" (legacy v1)

    Category: write
    Workflow: Step 1 of agentic.
    """
    try:
        client = get_client()
        result = client.agentic.start_run(
            model_name=model_name,
            model_description=model_description,
            auto_mode=auto_mode,
            require_approval=require_approval,
            auto_apply_safe_features=auto_apply_safe_features,
            auto_deploy=auto_deploy,
            run_id=run_id,
            user_query=user_query,
            phase_plan=phase_plan,
            algorithm=algorithm,
        )
        logger.info(f"Executed agentic.start_run")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_start_run: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_get_run_state(run_id: str):
    """
    Get the current state of an agentic run (poll until done).

    Poll this after agentic_start_run. The run is finished when status is
    'completed' (or 'failed'/'cancelled'); it needs input when status is
    'waiting_input' — then call agentic_get_pending_decision.

    Category: read
    Workflow: Step 2 of agentic. Run after: agentic_start_run.
    """
    try:
        client = get_client()
        result = client.agentic.get_run_state(run_id)
        logger.info(f"Executed agentic.get_run_state")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_get_run_state: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_get_pending_decision(run_id: str):
    """
    Check whether the run is paused waiting for a human decision.

    Returns the decision context (decision_type, options) or None when no
    decision is pending. Answer with agentic_submit_decision.

    Category: read
    """
    try:
        client = get_client()
        result = client.agentic.get_pending_decision(run_id)
        logger.info(f"Executed agentic.get_pending_decision")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_get_pending_decision: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_submit_decision(
    run_id: str,
    decision_type: str,
    choice_index: Optional[int] = None,
    action: Optional[str] = None,
    custom_value: Optional[Any] = None,
    label_type: Optional[str] = None,
    apply_indices: Optional[List[int]] = None,
    skip_indices: Optional[List[int]] = None,
    selected_indices: Optional[List[int]] = None,
    selected_options: Optional[List[Any]] = None,
    selected_features: Optional[List[Any]] = None,
    skipped: Optional[bool] = None,
    done: Optional[bool] = None,
    report_config: Optional[Dict] = None,
    monitoring_config: Optional[Dict] = None,
):
    """
    Submit a decision for a pending approval in the pipeline.

    Required fields depend on the decision_type returned by
    agentic_get_pending_decision. Common patterns:
    - label_selection: choice_index=N
    - feature_engineering: apply_indices=[...], skip_indices=[...]
    - model_training: choice_index=N
    - model_deployment: action="approve" or "skip"

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.submit_decision(
            run_id=run_id,
            decision_type=decision_type,
            choice_index=choice_index,
            action=action,
            custom_value=custom_value,
            label_type=label_type,
            apply_indices=apply_indices,
            skip_indices=skip_indices,
            selected_indices=selected_indices,
            selected_options=selected_options,
            selected_features=selected_features,
            skipped=skipped,
            done=done,
            report_config=report_config,
            monitoring_config=monitoring_config,
        )
        logger.info(f"Executed agentic.submit_decision")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_submit_decision: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_send_chat(run_id: str, content: str):
    """
    Send a chat message to the run's agent and get a reply.

    Use this to ask questions about the run's state or provide context.

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.send_chat(run_id, content)
        logger.info(f"Executed agentic.send_chat")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_send_chat: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_cancel_run(run_id: str):
    """
    Cancel a running agentic pipeline.

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.cancel_run(run_id)
        logger.info(f"Executed agentic.cancel_run")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_cancel_run: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_skip_phase(run_id: str):
    """
    Skip the run's current phase and move to the next.

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.skip_phase(run_id)
        logger.info(f"Executed agentic.skip_phase")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_skip_phase: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_get_phases(run_id: str):
    """
    Get the phase execution history for a run.

    Category: read
    """
    try:
        client = get_client()
        result = client.agentic.get_phases(run_id)
        logger.info(f"Executed agentic.get_phases")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_get_phases: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def agentic_retrain(run_id: str, params: Optional[Dict] = None):
    """
    Retrain a completed run with optional new preprocessing or parameters.

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.retrain(run_id, params)
        logger.info(f"Executed agentic.retrain")
        return _dump(result)
    except Exception as e:
        logger.error(f"Error in agentic_retrain: {e}")
        raise
