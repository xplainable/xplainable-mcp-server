"""Run one scenario case: agent + MCP toolset -> RunOutcome.

pydantic-ai 2.37 facts this module relies on (verified by introspection):
- ToolCallPart/RetryPromptPart both carry an always-populated tool_call_id
  (default factory), so errored calls are matched by id; name-based matching
  is only a fallback for retries whose id matches no seen call.
- ToolCallPart.args may be a JSON str, dict, or None; args_as_dict() handles
  all three.
- UsageLimitExceeded carries no messages; capture_run_messages() is the
  supported way to recover the partial transcript when a run raises.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic_ai import Agent, UsageLimitExceeded, UsageLimits, capture_run_messages

from evals.harness.models import CreatedArtifacts, RunConfig, RunOutcome, Scenario, ToolCall

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
URL_RE = re.compile(r"https://[^\s)\"']+")


def extract_tool_calls(messages) -> List[ToolCall]:
    """Tool calls in transcript order, with failed calls marked error=True.

    A call is only evidenced successful by a matching tool-return part
    (matched by tool_call_id). A dangling call — no tool-return AND no
    retry-prompt — means the run aborted on that call's failure (e.g.
    UnexpectedModelBehavior when the retry cap is exceeded) or was truncated
    mid-call; evaluators must fail safe, so it is marked error=True.

    A RetryPromptPart also marks the call it retried: matched by
    tool_call_id; if the id matches no call (defensive), the last call with
    the retry's tool_name is marked instead. Its content (the ToolError
    message — str, or list[ErrorDetails] for validation failures in
    pydantic-ai 2.37) is captured as error_text; dangling calls get a
    sentinel explaining the missing return.
    """
    call_parts = []
    retry_parts = []
    return_ids = set()
    for message in messages:
        for part in getattr(message, "parts", []):
            kind = getattr(part, "part_kind", None)
            if kind == "tool-call":
                call_parts.append(part)
            elif kind == "retry-prompt" and getattr(part, "tool_name", None):
                retry_parts.append(part)
            elif kind == "tool-return":
                return_ids.add(getattr(part, "tool_call_id", None))

    ids = [getattr(p, "tool_call_id", None) for p in call_parts]
    errored = [call_id not in return_ids for call_id in ids]
    error_texts: List = [
        "(no tool return — run aborted or transcript truncated)" if error else None
        for error in errored
    ]
    for retry in retry_parts:
        content = getattr(retry, "content", None)
        text = content if isinstance(content, str) else str(content)
        retry_id = getattr(retry, "tool_call_id", None)
        if retry_id is not None and retry_id in ids:
            i = ids.index(retry_id)
        else:
            # Fallback: mark the last call with the same tool name.
            i = next(
                (j for j in range(len(call_parts) - 1, -1, -1)
                 if call_parts[j].tool_name == retry.tool_name),
                None,
            )
            if i is None:
                continue
        errored[i] = True
        error_texts[i] = text

    return [
        ToolCall(name=part.tool_name, args=part.args_as_dict(), error=error,
                 error_text=text)
        for part, error, text in zip(call_parts, errored, error_texts)
    ]


def _parse_return_content(content):
    """Tolerant tool-return payload parsing.

    pydantic-ai 2.37 types ToolReturnPart.content as ToolReturnContent
    (MultiModalContent | Sequence[Any] | Mapping[str, Any] | Any — i.e.
    effectively Any); MCP servers commonly serialise returns as JSON text.
    Returns the parsed structure, or None if the content is unusable.
    """
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return None
    return content


def _dict_rows(value) -> List[Dict]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _prediction_rows(payload) -> List[Dict]:
    """Prediction rows from a predict-tool return (list, keyed dict, or
    single-row dict). Non-dict rows (e.g. bare probabilities) are dropped:
    RunOutcome.predictions is List[Dict]."""
    if isinstance(payload, list):
        return _dict_rows(payload)
    if isinstance(payload, dict):
        for key in ("predictions", "results", "data", "rows"):
            if isinstance(payload.get(key), list):
                return _dict_rows(payload[key])
        return [payload]
    return []


def _prescription_rows(payload) -> List[Dict]:
    """Prescription rows from an optimiser-run return.

    The client wrapper returns {run_id, batch_id, result} where result is
    the XGM envelope {"status": ..., "results": [rows]}
    (xplainable_client/client/optimisers.py::run_optimiser); a bare
    envelope or a bare row list are tolerated too.
    """
    if isinstance(payload, list):
        return _dict_rows(payload)
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("results"), list):
        return _dict_rows(result["results"])
    if isinstance(payload.get("results"), list):
        return _dict_rows(payload["results"])
    return []


def extract_run_outputs(messages) -> Tuple[List[Dict], List[Dict]]:
    """(predictions, prescriptions) from 'tool-return' message parts.

    Predict tools are matched by "predict" in the tool name
    (inference_predict); optimiser runs by "optimis" AND "run"
    (optimisers_run_optimiser). Tool-return parts only exist for
    successful calls (failures surface as retry-prompt parts).
    """
    predictions: List[Dict] = []
    prescriptions: List[Dict] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if getattr(part, "part_kind", None) != "tool-return":
                continue
            name = (getattr(part, "tool_name", None) or "").lower()
            payload = _parse_return_content(getattr(part, "content", None))
            if payload is None:
                continue
            if "predict" in name:
                predictions.extend(_prediction_rows(payload))
            elif "optimis" in name and "run" in name:
                prescriptions.extend(_prescription_rows(payload))
    return predictions, prescriptions


def extract_report_urls(text: str) -> List[str]:
    """URLs containing "/report", trailing sentence punctuation stripped.

    Note: the "/report" substring filter is deliberately loose — it also
    matches paths like /reporting/ or /report-builder/.
    """
    urls = (u.rstrip(".,;:!?") for u in URL_RE.findall(text or ""))
    return [u for u in urls if "/report" in u]


def load_prompt(prompt_id: str) -> str:
    return (PROMPTS_DIR / f"{prompt_id}.md").read_text()


def _fmt(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"


async def run_case(scenario: Scenario, config: RunConfig, toolset, session) -> RunOutcome:
    """Execute one agent run and inspect resulting platform state.

    Contract: always returns a RunOutcome — setup (snapshot/prompt/agent
    construction), agent, diff and inspect failures are all captured in
    outcome.error so the caller can still run teardown from outcome.created
    (Task 9 wires that). If setup fails, nothing was created: the outcome
    carries an empty CreatedArtifacts and diff/inspect are skipped. Distinct
    failure messages are joined with "; ".
    """
    try:
        session.snapshot()
        agent = Agent(
            config.model,
            toolsets=[toolset],
            system_prompt=load_prompt(config.prompt_id),
            # pydantic-ai's default tool-retry cap (1) raises
            # UnexpectedModelBehavior and aborts the run on a tool's second
            # consecutive failure. Real MCP consumers just see the error text
            # and continue; runs are already bounded by UsageLimits, so relax
            # the per-tool cap.
            retries=5,
        )
    except Exception as e:  # noqa: BLE001 — setup failed, nothing created
        return RunOutcome(final_text="", error=_fmt(e))

    limits = UsageLimits(
        request_limit=config.request_limit,
        tool_calls_limit=config.tool_calls_limit,
    )
    final_text, usage_hit = "", False
    errors: List[str] = []
    messages: list = []
    captured: list = []
    try:
        with capture_run_messages() as captured:
            async with agent:
                result = await agent.run(scenario.prompt, usage_limits=limits)
        final_text = str(result.output)
        messages = result.all_messages()
    except UsageLimitExceeded:
        usage_hit = True
        messages = list(captured)
    except Exception as e:  # noqa: BLE001 — outcome must always be returned
        errors.append(_fmt(e))
        messages = list(captured)

    created = CreatedArtifacts()
    try:
        created = session.diff()
    except Exception as e:  # noqa: BLE001 — never forfeit the outcome
        if _fmt(e) not in errors:
            errors.append(_fmt(e))

    predictions, prescriptions = extract_run_outputs(messages)
    outcome = RunOutcome(
        final_text=final_text,
        tool_calls=extract_tool_calls(messages),
        created=created,
        predictions=predictions,
        prescriptions=prescriptions,
        report_urls=extract_report_urls(final_text),
        usage_limit_hit=usage_hit,
        error="; ".join(errors) or None,
    )
    try:
        session.inspect(outcome)
    except Exception as e:  # noqa: BLE001 — inspection is best-effort
        if _fmt(e) not in errors:
            errors.append(_fmt(e))
        outcome.error = "; ".join(errors)
    return outcome
