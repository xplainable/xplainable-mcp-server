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
import re
from pathlib import Path
from typing import List

from pydantic_ai import Agent, UsageLimitExceeded, UsageLimits, capture_run_messages

from evals.harness.models import CreatedArtifacts, RunConfig, RunOutcome, Scenario, ToolCall

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
URL_RE = re.compile(r"https://[^\s)\"']+")


def extract_tool_calls(messages) -> List[ToolCall]:
    """Tool calls in transcript order, with retried calls marked error=True.

    A RetryPromptPart marks the call it retried: matched by tool_call_id;
    if the id matches no call (defensive), the last call with the retry's
    tool_name is marked instead.
    """
    call_parts = []
    retry_parts = []
    for message in messages:
        for part in getattr(message, "parts", []):
            kind = getattr(part, "part_kind", None)
            if kind == "tool-call":
                call_parts.append(part)
            elif kind == "retry-prompt" and getattr(part, "tool_name", None):
                retry_parts.append(part)

    errored = [False] * len(call_parts)
    ids = [getattr(p, "tool_call_id", None) for p in call_parts]
    for retry in retry_parts:
        retry_id = getattr(retry, "tool_call_id", None)
        if retry_id is not None and retry_id in ids:
            errored[ids.index(retry_id)] = True
            continue
        # Fallback: mark the last call with the same tool name.
        for i in range(len(call_parts) - 1, -1, -1):
            if call_parts[i].tool_name == retry.tool_name:
                errored[i] = True
                break

    return [
        ToolCall(name=part.tool_name, args=part.args_as_dict(), error=error)
        for part, error in zip(call_parts, errored)
    ]


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

    outcome = RunOutcome(
        final_text=final_text,
        tool_calls=extract_tool_calls(messages),
        created=created,
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
