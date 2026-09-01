"""Runner: tool-call extraction, report-url extraction, prompt loading, run_case.

Extraction tests use REAL pydantic-ai message classes (2.37.0) so they pin the
real API:
- ToolCallPart(tool_name, args: str|dict|None, tool_call_id auto) with
  part_kind='tool-call' and an args_as_dict() helper (handles str/dict/None).
- RetryPromptPart(content, tool_name: str|None, tool_call_id auto) with
  part_kind='retry-prompt'. tool_call_id is always populated (default factory),
  so error matching is id-based, with name-based fallback for unmatched ids.

run_case is orchestration; here we only test its contract (always returns a
RunOutcome, never raises) with stubbed Agent/session. Live behaviour is
validated in Task 12.
"""
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from evals.harness.models import CreatedArtifacts, RunConfig, RunOutcome, Scenario, Stage
from evals.harness import runner
from evals.harness.runner import (
    extract_report_urls,
    extract_tool_calls,
    load_prompt,
    run_case,
)


# ---------------------------------------------------------------- extraction

def _messages(*parts_per_message):
    """Build a message list; each item is a sequence of response/request parts."""
    messages = []
    for parts in parts_per_message:
        cls = ModelRequest if any(
            p.part_kind in ("retry-prompt", "tool-return", "user-prompt") for p in parts
        ) else ModelResponse
        messages.append(cls(parts=list(parts)))
    return messages


def test_extracts_tool_calls_in_order_with_dict_args():
    messages = _messages(
        [UserPromptPart(content="hi")],
        [ToolCallPart(tool_name="list_datasets", args={"team_id": "t1"})],
        [ToolReturnPart(tool_name="list_datasets", content="ok", tool_call_id="x")],
        [ToolCallPart(tool_name="train_model", args='{"dataset_id": "d1"}')],
        [TextPart(content="done")],
    )
    calls = extract_tool_calls(messages)
    assert [c.name for c in calls] == ["list_datasets", "train_model"]
    assert calls[0].args == {"team_id": "t1"}
    assert calls[1].args == {"dataset_id": "d1"}  # str args parsed to dict
    assert all(not c.error for c in calls)


def test_retry_marks_errored_call_by_tool_call_id_not_name():
    # Two calls to the same tool; the SECOND failed. Name-based matching would
    # mismark the first — id-based matching must mark the second only.
    first = ToolCallPart(tool_name="train_model", args={"try": 1}, tool_call_id="c1")
    second = ToolCallPart(tool_name="train_model", args={"try": 2}, tool_call_id="c2")
    retry = RetryPromptPart(
        content="boom", tool_name="train_model", tool_call_id="c2"
    )
    calls = extract_tool_calls(_messages([first], [retry], [second]))
    assert [(c.args["try"], c.error) for c in calls] == [(1, False), (2, True)]


def test_retry_without_matching_id_falls_back_to_name():
    # Retry whose id matches no call (e.g. id lost in transport): fall back to
    # marking the last call with that tool name.
    call = ToolCallPart(tool_name="deploy", args={}, tool_call_id="c1")
    other = ToolCallPart(tool_name="predict", args={}, tool_call_id="c2")
    retry = RetryPromptPart(content="bad", tool_name="deploy", tool_call_id="zz")
    calls = extract_tool_calls(_messages([call, other], [retry]))
    assert [(c.name, c.error) for c in calls] == [("deploy", True), ("predict", False)]


def test_calls_without_retry_are_not_errors():
    calls = extract_tool_calls(
        _messages([ToolCallPart(tool_name="list_models", args=None)])
    )
    assert len(calls) == 1
    assert calls[0].error is False
    assert calls[0].args == {}  # None args -> empty dict


def test_extract_handles_empty_messages():
    assert extract_tool_calls([]) == []


# ------------------------------------------------------------------- urls

def test_extract_report_urls_finds_report_links_only():
    text = (
        "Built it! Report: https://platform.xplainable.io/reports/abc-123 and "
        "model page https://platform.xplainable.io/models/m1 "
        "(also https://platform.xplainable.io/report/xyz)"
    )
    assert extract_report_urls(text) == [
        "https://platform.xplainable.io/reports/abc-123",
        "https://platform.xplainable.io/report/xyz",
    ]


def test_extract_report_urls_empty_and_none():
    assert extract_report_urls("") == []
    assert extract_report_urls(None) == []
    assert extract_report_urls("no urls here") == []


# ------------------------------------------------------------------ prompt

def test_load_prompt_default_returns_file_content():
    text = load_prompt("default")
    assert "data analyst" in text
    assert "Xplainable" in text


# ---------------------------------------------------------------- run_case

class _StubResult:
    output = "all done https://platform.xplainable.io/reports/r1"

    def all_messages(self):
        return [
            ModelResponse(parts=[ToolCallPart(tool_name="train_model", args={})])
        ]


class _StubAgent:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def run(self, prompt, usage_limits=None):
        return _StubResult()


class _StubSession:
    def __init__(self, diff_raises=False, inspect_raises=False):
        self.diff_raises = diff_raises
        self.inspect_raises = inspect_raises
        self.inspected = None

    def snapshot(self):
        pass

    def diff(self):
        if self.diff_raises:
            raise RuntimeError("diff boom")
        return CreatedArtifacts(models=["m1"])

    def inspect(self, outcome):
        if self.inspect_raises:
            raise RuntimeError("inspect boom")
        self.inspected = outcome


_SCENARIO = Scenario(
    name="s", prompt="do it", fixture="telco.csv", expected_stages=[Stage.TRAIN]
)


async def test_run_case_happy_path(monkeypatch):
    monkeypatch.setattr(runner, "Agent", _StubAgent)
    session = _StubSession()
    outcome = await run_case(_SCENARIO, RunConfig(), toolset=object(), session=session)
    assert isinstance(outcome, RunOutcome)
    assert outcome.error is None
    assert outcome.final_text.startswith("all done")
    assert [c.name for c in outcome.tool_calls] == ["train_model"]
    assert outcome.created.models == ["m1"]
    assert outcome.report_urls == ["https://platform.xplainable.io/reports/r1"]
    assert session.inspected is outcome  # inspection ran on the outcome


async def test_run_case_returns_outcome_when_diff_raises(monkeypatch):
    # Teardown must never be forfeited: diff() failure -> outcome with error
    # set and empty created, not an exception.
    monkeypatch.setattr(runner, "Agent", _StubAgent)
    outcome = await run_case(
        _SCENARIO, RunConfig(), toolset=object(), session=_StubSession(diff_raises=True)
    )
    assert isinstance(outcome, RunOutcome)
    assert "diff boom" in outcome.error
    assert outcome.created == CreatedArtifacts()


async def test_run_case_returns_outcome_when_inspect_raises(monkeypatch):
    monkeypatch.setattr(runner, "Agent", _StubAgent)
    outcome = await run_case(
        _SCENARIO, RunConfig(), toolset=object(),
        session=_StubSession(inspect_raises=True),
    )
    assert isinstance(outcome, RunOutcome)
    assert outcome.created.models == ["m1"]  # diff result kept


async def test_run_case_captures_agent_failure_as_error(monkeypatch):
    class _BoomAgent(_StubAgent):
        async def run(self, prompt, usage_limits=None):
            raise ValueError("model exploded")

    monkeypatch.setattr(runner, "Agent", _BoomAgent)
    session = _StubSession()
    outcome = await run_case(_SCENARIO, RunConfig(), toolset=object(), session=session)
    assert outcome.error == "ValueError: model exploded"
    assert outcome.final_text == ""
    assert outcome.created.models == ["m1"]  # diff still ran -> teardown possible
