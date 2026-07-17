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

@mcp.tool(icons=[XP_ICON], tags={"write"})
def agentic_start_run(model_name: str, model_description: str = '', auto_mode: bool = False, require_approval: Optional[List[str]] = None, auto_apply_safe_features: bool = True, auto_deploy: bool = False, run_id: Optional[str] = None, user_query: Optional[str] = None, phase_plan: Optional[List[str]] = None, algorithm: str = 'xgm'):
    """
    Start a new agentic ML training pipeline run.
    
    This initiates the full ML workflow: data preparation -> label selection ->
    feature engineering -> model training -> deployment -> reporting -> monitoring.
    
    The pipeline will pause at each phase listed in require_approval and wait
    for a decision via submit_decision().
    
    Args:
        model_name: Name for the model being trained
        model_description: Description of the model's purpose
        auto_mode: If True, automatically proceed through phases without approval
        require_approval: List of phases requiring human approval. Defaults to all phases.
            Valid phases: label_selection, data_preparation, feature_engineering,
            model_training, model_deployment, report_creation, monitoring_creation
        auto_apply_safe_features: Automatically apply safe feature engineering suggestions
        auto_deploy: Automatically deploy the model after training
        run_id: Optional existing run ID to resume
        user_query: Optional natural language description of what to build
        phase_plan: Optional ordered list of phases to execute
        algorithm: Training algorithm. Defaults to "xgm" (v2, trained on
            Xplainable servers). Pass "xplainable" to use the legacy v1
            training path.
    
    Returns:
        StartRunResponse with run_id and status

    Category: write
    Workflow: Step 1 of agentic.
    """
    try:
        client = get_client()
        result = client.agentic.start_run(model_name, model_description, auto_mode, require_approval, auto_apply_safe_features, auto_deploy, run_id, user_query, phase_plan, algorithm)
        logger.info(f"Executed agentic.start_run")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_start_run: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def agentic_get_run_state(run_id: str):
    """
    Get the current state of an agentic pipeline run.
    
    Use this to poll for run status and see current phase, progress, and results.
    
    Args:
        run_id: The run ID returned from start_run
    
    Returns:
        Dict with run state including current phase, status, and any results

    Category: read
    Workflow: Step 2 of agentic. Run after: agentic_agentic_start_run.
    """
    try:
        client = get_client()
        result = client.agentic.get_run_state(run_id)
        logger.info(f"Executed agentic.get_run_state")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_get_run_state: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def agentic_get_pending_decision(run_id: str):
    """
    Check if the pipeline is waiting for a human decision.
    
    When the pipeline reaches a phase listed in require_approval, it pauses
    and creates a pending decision. Call this to see what decision is needed,
    then use submit_decision() to provide your choice.
    
    Args:
        run_id: The run ID
    
    Returns:
        Decision info dict with decision_type, options, and context, or None if no decision pending

    Category: read
    """
    try:
        client = get_client()
        result = client.agentic.get_pending_decision(run_id)
        logger.info(f"Executed agentic.get_pending_decision")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_get_pending_decision: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def agentic_submit_decision(run_id: str, decision_type: str, choice_index: Optional[int] = None, action: Optional[str] = None, custom_value: Optional[Any] = None, label_type: Optional[str] = None, apply_indices: Optional[List[int]] = None, skip_indices: Optional[List[int]] = None, selected_indices: Optional[List[int]] = None, selected_options: Optional[List[Any]] = None, selected_features: Optional[List[Any]] = None, monotonic_constraints: Optional[Dict[str, str]] = None, skipped: Optional[bool] = None, done: Optional[bool] = None, report_config: Optional[dict] = None, monitoring_config: Optional[dict] = None):
    """
    Submit a decision for a pending approval in the pipeline.
    
    The required fields depend on the decision_type from get_pending_decision().
    Common patterns:
    - Label selection: decision_type="label_selection", choice_index=N
    - Feature engineering: decision_type="feature_engineering", apply_indices=[...], skip_indices=[...]
    - Model training: decision_type="model_training", choice_index=N
    - Deployment: decision_type="model_deployment", action="approve" or "skip"
    - Report: decision_type="report_creation", report_config={...}
    - Monitoring: decision_type="monitoring_creation", monitoring_config={...}
    
    Args:
        run_id: The run ID
        decision_type: Type of decision (matches pending decision's decision_type)
        choice_index: Index of chosen option from the options list
        action: Action string (e.g., "approve", "skip", "reject")
        custom_value: Custom value for decisions that accept free-form input
        label_type: Label type for label selection decisions
        apply_indices: Indices of items to apply (e.g., feature engineering steps)
        skip_indices: Indices of items to skip
        selected_indices: Indices of selected items
        selected_options: List of selected option values
        selected_features: List of selected features
        monotonic_constraints: Feature -> direction ("increasing"/"decreasing")
            map for training approvals. Passing a dict — even an empty one —
            marks the constraint proposals as reviewed; pass {} to train
            unconstrained after reviewing, or omit (None) to leave the
            server default behaviour.
        skipped: Whether to skip this phase entirely
        done: Whether the decision process is complete
        report_config: Configuration for report creation
        monitoring_config: Configuration for monitoring setup
    
    Returns:
        SubmitDecisionResponse with status

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.submit_decision(run_id, decision_type, choice_index, action, custom_value, label_type, apply_indices, skip_indices, selected_indices, selected_options, selected_features, monotonic_constraints, skipped, done, report_config, monitoring_config)
        logger.info(f"Executed agentic.submit_decision")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_submit_decision: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def agentic_send_chat(run_id: str, content: str):
    """
    Send a chat message to the agentic pipeline and get a response.
    
    Use this to ask questions about the current state of the run,
    request explanations, or provide additional context.
    
    Args:
        run_id: The run ID
        content: The message content
    
    Returns:
        ChatMessageResponse with the pipeline's reply

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.send_chat(run_id, content)
        logger.info(f"Executed agentic.send_chat")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_send_chat: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def agentic_cancel_run(run_id: str):
    """
    Cancel a running agentic pipeline.
    
    Args:
        run_id: The run ID to cancel
    
    Returns:
        CancelRunResponse with success status

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.cancel_run(run_id)
        logger.info(f"Executed agentic.cancel_run")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_cancel_run: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def agentic_skip_phase(run_id: str):
    """
    Skip the current phase and move to the next.
    
    Args:
        run_id: The run ID
    
    Returns:
        SkipPhaseResponse with skipped_phase and next_phase

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.skip_phase(run_id)
        logger.info(f"Executed agentic.skip_phase")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_skip_phase: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def agentic_get_phases(run_id: str):
    """
    Get the phase execution history for a run.
    
    Args:
        run_id: The run ID
    
    Returns:
        List of phase status dicts with phase name, status, timestamps, and any errors

    Category: read
    """
    try:
        client = get_client()
        result = client.agentic.get_phases(run_id)
        logger.info(f"Executed agentic.get_phases")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_get_phases: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def agentic_retrain(run_id: str, params: Optional[Dict[str, Any]] = None):
    """
    Retrain a completed run with optional new preprocessing steps or parameters.
    
    Args:
        run_id: The run ID of the completed run to retrain
        params: Optional dict of retraining parameters
    
    Returns:
        Retrain result dict

    Category: write
    """
    try:
        client = get_client()
        result = client.agentic.retrain(run_id, params)
        logger.info(f"Executed agentic.retrain")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in agentic_retrain: {e}")
        raise
