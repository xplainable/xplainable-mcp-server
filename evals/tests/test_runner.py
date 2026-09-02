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
        [ToolCallPart(tool_name="list_datasets", args={"team_id": "t1"},
                      tool_call_id="c1")],
        [ToolReturnPart(tool_name="list_datasets", content="ok", tool_call_id="c1")],
        [ToolCallPart(tool_name="train_model", args='{"dataset_id": "d1"}',
                      tool_call_id="c2")],
        [ToolReturnPart(tool_name="train_model", content="ok", tool_call_id="c2")],
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
    first_ret = ToolReturnPart(tool_name="train_model", content="ok", tool_call_id="c1")
    second = ToolCallPart(tool_name="train_model", args={"try": 2}, tool_call_id="c2")
    retry = RetryPromptPart(
        content="boom", tool_name="train_model", tool_call_id="c2"
    )
    calls = extract_tool_calls(_messages([first], [first_ret], [second], [retry]))
    assert [(c.args["try"], c.error) for c in calls] == [(1, False), (2, True)]


def test_retry_without_matching_id_falls_back_to_name():
    # Retry whose id matches no call (e.g. id lost in transport): fall back to
    # marking the last call with that tool name.
    call = ToolCallPart(tool_name="deploy", args={}, tool_call_id="c1")
    other = ToolCallPart(tool_name="predict", args={}, tool_call_id="c2")
    other_ret = ToolReturnPart(tool_name="predict", content="ok", tool_call_id="c2")
    retry = RetryPromptPart(content="bad", tool_name="deploy", tool_call_id="zz")
    calls = extract_tool_calls(_messages([call, other], [other_ret, retry]))
    assert [(c.name, c.error) for c in calls] == [("deploy", True), ("predict", False)]


def test_returned_calls_without_retry_are_not_errors():
    calls = extract_tool_calls(
        _messages(
            [ToolCallPart(tool_name="list_models", args=None, tool_call_id="c1")],
            [ToolReturnPart(tool_name="list_models", content="ok", tool_call_id="c1")],
        )
    )
    assert len(calls) == 1
    assert calls[0].error is False
    assert calls[0].args == {}  # None args -> empty dict


def test_extract_handles_empty_messages():
    assert extract_tool_calls([]) == []


def test_dangling_tool_call_without_return_or_retry_is_error():
    # Live-run bug: when a tool exceeds pydantic-ai's retry cap the run raises
    # UnexpectedModelBehavior and the final ToolCallPart gets neither a
    # tool-return nor a retry-prompt part. No tool-return = no evidence of
    # success — evaluators must fail safe, so the dangling call is an error.
    ok = ToolCallPart(
        tool_name="deployments_get_deployment_payload", args={}, tool_call_id="c1"
    )
    ret = ToolReturnPart(
        tool_name="deployments_get_deployment_payload", content="ok", tool_call_id="c1"
    )
    dangling = ToolCallPart(tool_name="inference_predict", args={}, tool_call_id="c2")
    calls = extract_tool_calls(_messages([ok], [ret], [dangling]))
    assert [(c.name, c.error) for c in calls] == [
        ("deployments_get_deployment_payload", False),  # has return -> success
        ("inference_predict", True),                    # dangling -> error
    ]


def test_error_text_captured_from_retry_string_content():
    # Failed calls must persist the ToolError message (the platform's
    # structured "[CODE] msg — Suggestion: ..." envelope) — not just a bool.
    ok = ToolCallPart(tool_name="list_models", args={}, tool_call_id="c1")
    ok_ret = ToolReturnPart(tool_name="list_models", content="ok", tool_call_id="c1")
    bad = ToolCallPart(tool_name="train_model", args={}, tool_call_id="c2")
    retry = RetryPromptPart(content="E42 boom", tool_name="train_model",
                            tool_call_id="c2")
    calls = extract_tool_calls(_messages([ok], [ok_ret], [bad], [retry]))
    assert [(c.name, c.error, c.error_text) for c in calls] == [
        ("list_models", False, None),
        ("train_model", True, "E42 boom"),
    ]


def test_error_text_for_dangling_call_is_sentinel():
    dangling = ToolCallPart(tool_name="inference_predict", args={}, tool_call_id="c1")
    (call,) = extract_tool_calls(_messages([dangling]))
    assert call.error is True
    assert call.error_text == "(no tool return — run aborted or transcript truncated)"


# ------------------------------------------- predictions / prescriptions

def test_extracts_predictions_from_predict_tool_returns():
    # pydantic-ai 2.37 ToolReturnPart.content is ToolReturnContent (~Any);
    # MCP servers commonly serialise returns as JSON text -> both must work.
    rows = [{"customerID": "c1", "proba": 0.7}, {"customerID": "c2", "proba": 0.2}]
    messages = _messages(
        [ToolReturnPart(tool_name="inference_predict", content=rows, tool_call_id="a")],
        [ToolReturnPart(
            tool_name="inference_predict",
            content='{"predictions": [{"customerID": "c3", "proba": 0.9}]}',
            tool_call_id="b",
        )],
    )
    predictions, prescriptions = runner.extract_run_outputs(messages)
    assert predictions == rows + [{"customerID": "c3", "proba": 0.9}]
    assert prescriptions == []


def test_extracts_prescriptions_from_optimiser_run_envelope():
    # run_optimiser returns {run_id, batch_id, result} where result is the
    # XGM envelope {"status": ..., "results": [rows]} (client optimisers.py).
    row = {"optimal_features": {"Contract": "Two year"}, "total_cost": 30.0}
    envelope = {"run_id": "r1", "batch_id": "b1",
                "result": {"status": "success", "results": [row]}}
    messages = _messages(
        [ToolReturnPart(
            tool_name="optimisers_run_optimiser", content=envelope, tool_call_id="a",
        )],
    )
    predictions, prescriptions = runner.extract_run_outputs(messages)
    assert prescriptions == [row]
    assert predictions == []


def test_extract_run_outputs_tolerates_junk_content():
    messages = _messages(
        [ToolReturnPart(tool_name="inference_predict", content="not json {",
                        tool_call_id="a")],
        [ToolReturnPart(tool_name="optimisers_run_optimiser", content=42,
                        tool_call_id="b")],
        [ToolReturnPart(tool_name="optimisers_run_optimiser",
                        content={"result": {"status": "error"}}, tool_call_id="c")],
        # Non-predict/optimiser returns are ignored entirely.
        [ToolReturnPart(tool_name="datasets_list_team_datasets",
                        content=[{"dataset_id": "d1"}], tool_call_id="d")],
    )
    assert runner.extract_run_outputs(messages) == ([], [])


def test_extract_run_outputs_single_dict_predict_return_is_one_row():
    messages = _messages(
        [ToolReturnPart(tool_name="inference_predict",
                        content={"prediction": "Yes", "proba": 0.83},
                        tool_call_id="a")],
    )
    predictions, _ = runner.extract_run_outputs(messages)
    assert predictions == [{"prediction": "Yes", "proba": 0.83}]


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


def test_extract_report_urls_strips_trailing_sentence_punctuation():
    text = (
        "See https://platform.xplainable.io/reports/abc. "
        "Or https://platform.xplainable.io/reports/def, then done! "
        "Finally https://platform.xplainable.io/reports/ghi?"
    )
    assert extract_report_urls(text) == [
        "https://platform.xplainable.io/reports/abc",
        "https://platform.xplainable.io/reports/def",
        "https://platform.xplainable.io/reports/ghi",
    ]


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
    def __init__(self, diff_raises=False, inspect_raises=False, snapshot_raises=False):
        self.diff_raises = diff_raises
        self.inspect_raises = inspect_raises
        self.snapshot_raises = snapshot_raises
        self.inspected = None
        self.diff_called = False

    def snapshot(self):
        if self.snapshot_raises:
            raise ConnectionError("api unreachable")

    def diff(self):
        self.diff_called = True
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


async def test_run_case_usage_limit_recovers_partial_transcript(monkeypatch):
    # Spec: usage limit -> usage_limit_hit True with partial tool_calls.
    # UsageLimitExceeded carries no messages; the transcript must be recovered
    # via capture_run_messages(). The stub feeds the REAL capture mechanism:
    # it appends real message objects to the contextvar-held list that
    # capture_run_messages() yields (same list the real agent internals use),
    # then raises — exactly what an interrupted run looks like.
    from pydantic_ai import UsageLimitExceeded, _agent_graph

    class _LimitAgent(_StubAgent):
        async def run(self, prompt, usage_limits=None):
            captured = _agent_graph._messages_ctx_var.get().messages
            captured.append(
                ModelResponse(parts=[ToolCallPart(tool_name="list_datasets", args={})])
            )
            raise UsageLimitExceeded("The next request would exceed the request_limit of 1")

    monkeypatch.setattr(runner, "Agent", _LimitAgent)
    session = _StubSession()
    outcome = await run_case(_SCENARIO, RunConfig(), toolset=object(), session=session)
    assert isinstance(outcome, RunOutcome)  # did not raise
    assert outcome.usage_limit_hit is True
    assert [c.name for c in outcome.tool_calls] == ["list_datasets"]  # partial transcript
    assert outcome.error is None  # limit hit is signalled by the flag, not error
    assert outcome.final_text == ""
    assert outcome.created.models == ["m1"]  # diff still ran -> teardown possible


async def test_run_case_agent_gets_relaxed_tool_retry_cap(monkeypatch):
    # pydantic-ai's default retries=1 aborts the whole run (UnexpectedModelBehavior)
    # on a tool's second consecutive failure — unrepresentative of real MCP
    # consumers, which just see the error text and continue. run_case must
    # construct the Agent with retries=5 (runs stay bounded by UsageLimits).
    kwargs_seen = {}

    class _RecordingAgent(_StubAgent):
        def __init__(self, *args, **kwargs):
            kwargs_seen.update(kwargs)

    monkeypatch.setattr(runner, "Agent", _RecordingAgent)
    await run_case(_SCENARIO, RunConfig(), toolset=object(), session=_StubSession())
    assert kwargs_seen.get("retries") == 5


async def test_run_case_generic_failure_recovers_partial_transcript(monkeypatch):
    # Generic exceptions (e.g. UnexpectedModelBehavior) carry no messages;
    # the partial transcript must be recovered via capture_run_messages(),
    # same as the usage-limit path.
    from pydantic_ai import _agent_graph

    class _BoomAgent(_StubAgent):
        async def run(self, prompt, usage_limits=None):
            captured = _agent_graph._messages_ctx_var.get().messages
            captured.append(
                ModelResponse(parts=[ToolCallPart(tool_name="inference_predict", args={})])
            )
            raise RuntimeError("Tool 'inference_predict' exceeded max retries count of 1")

    monkeypatch.setattr(runner, "Agent", _BoomAgent)
    outcome = await run_case(_SCENARIO, RunConfig(), toolset=object(), session=_StubSession())
    assert "exceeded max retries" in outcome.error
    assert [(c.name, c.error) for c in outcome.tool_calls] == [("inference_predict", True)]


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


async def test_run_case_joins_agent_and_diff_failures(monkeypatch):
    # Later failures must not be dropped: agent AND diff errors both surface.
    class _BoomAgent(_StubAgent):
        async def run(self, prompt, usage_limits=None):
            raise ValueError("model exploded")

    monkeypatch.setattr(runner, "Agent", _BoomAgent)
    outcome = await run_case(
        _SCENARIO, RunConfig(), toolset=object(), session=_StubSession(diff_raises=True)
    )
    assert "ValueError: model exploded" in outcome.error
    assert "RuntimeError: diff boom" in outcome.error


# ------------------------------------------------------- run_case setup guard

async def test_run_case_returns_outcome_when_snapshot_raises(monkeypatch):
    # Setup failure before the agent runs: never raise, return an outcome with
    # error set and empty created; skip diff/inspect (no snapshot to diff).
    ran = []

    class _TrackingAgent(_StubAgent):
        async def run(self, prompt, usage_limits=None):
            ran.append(prompt)
            return _StubResult()

    monkeypatch.setattr(runner, "Agent", _TrackingAgent)
    session = _StubSession(snapshot_raises=True)
    outcome = await run_case(_SCENARIO, RunConfig(), toolset=object(), session=session)
    assert isinstance(outcome, RunOutcome)
    assert "ConnectionError: api unreachable" in outcome.error
    assert outcome.created == CreatedArtifacts()
    assert ran == []  # agent never ran
    assert session.diff_called is False  # diff skipped: snapshot never happened
    assert session.inspected is None  # inspect skipped too


async def test_run_case_returns_outcome_when_prompt_missing(monkeypatch):
    # Bad prompt_id -> load_prompt raises during setup. Same contract: outcome
    # with error, empty created, agent never constructed.
    constructed = []

    class _TrackingAgent(_StubAgent):
        def __init__(self, *args, **kwargs):
            constructed.append(args)

    monkeypatch.setattr(runner, "Agent", _TrackingAgent)
    session = _StubSession()
    outcome = await run_case(
        _SCENARIO, RunConfig(prompt_id="does-not-exist"), toolset=object(),
        session=session,
    )
    assert isinstance(outcome, RunOutcome)
    assert "FileNotFoundError" in outcome.error
    assert outcome.created == CreatedArtifacts()
    assert constructed == []  # Agent never constructed

# ---------------------------------------- run_case output extraction wiring

async def test_run_case_populates_predictions_and_prescriptions(monkeypatch):
    # The OPTIMISE stage + semantic detectors read outcome.predictions /
    # .prescriptions — run_case must populate them from the transcript.
    row = {"feature_changes": {"Contract": {"from": "Monthly", "to": "Two year"}},
           "total_cost": 25.0}

    class _ReturnResult(_StubResult):
        def all_messages(self):
            return _messages(
                [ToolReturnPart(tool_name="inference_predict",
                                content=[{"proba": 0.4}], tool_call_id="a")],
                [ToolReturnPart(
                    tool_name="optimisers_run_optimiser",
                    content={"run_id": "r", "batch_id": "b",
                             "result": {"status": "success", "results": [row]}},
                    tool_call_id="b",
                )],
            )

    class _ReturnAgent(_StubAgent):
        async def run(self, prompt, usage_limits=None):
            return _ReturnResult()

    monkeypatch.setattr(runner, "Agent", _ReturnAgent)
    outcome = await run_case(
        _SCENARIO, RunConfig(), toolset=object(), session=_StubSession()
    )
    assert outcome.predictions == [{"proba": 0.4}]
    assert outcome.prescriptions == [row]


# ------------------------------------------------------------------- usage

def test_extract_usage_sums_tokens_and_cost():
    import pytest
    from pydantic_ai.usage import RequestUsage
    from evals.harness.runner import extract_usage

    messages = [
        ModelRequest(parts=[UserPromptPart(content="hi")]),  # no usage attr
        ModelResponse(parts=[TextPart(content="a")],
                      usage=RequestUsage(input_tokens=100, output_tokens=10),
                      provider_details={"cost": 0.01}),
        ModelResponse(parts=[TextPart(content="b")],
                      usage=RequestUsage(input_tokens=200, output_tokens=20),
                      provider_details={"cost": 0.02}),
    ]
    input_t, output_t, cost = extract_usage(messages)
    assert (input_t, output_t) == (300, 30)
    assert cost == pytest.approx(0.03)


def test_extract_usage_without_cost_reports_none():
    from pydantic_ai.usage import RequestUsage
    from evals.harness.runner import extract_usage

    messages = [
        ModelResponse(parts=[TextPart(content="a")],
                      usage=RequestUsage(input_tokens=5, output_tokens=1)),
    ]
    assert extract_usage(messages) == (5, 1, None)


def test_extract_usage_mixes_decimal_and_float_costs():
    # RequestUsage.cost is typed Decimal | None in pydantic-ai 2.37 while
    # OpenRouter's provider_details["cost"] is a float. A transcript mixing
    # both paths crashed a real run (float + Decimal TypeError); the sum
    # must coerce to float and stay JSON-serialisable.
    from decimal import Decimal

    import pytest
    from pydantic_ai.usage import RequestUsage
    from evals.harness.runner import extract_usage

    messages = [
        ModelResponse(parts=[TextPart(content="a")],
                      usage=RequestUsage(input_tokens=100, output_tokens=10),
                      provider_details={"cost": 0.01}),
        ModelResponse(parts=[TextPart(content="b")],
                      usage=RequestUsage(input_tokens=200, output_tokens=20,
                                         cost=Decimal("0.02"))),  # fallback path
    ]
    _, _, cost = extract_usage(messages)
    assert isinstance(cost, float)
    assert cost == pytest.approx(0.03)


def test_usage_model_settings_openrouter_enables_cost_accounting():
    from evals.harness.runner import usage_model_settings

    settings = usage_model_settings("openrouter:z-ai/glm-5.3")
    assert settings["openrouter_usage"] == {"include": True}


def test_usage_model_settings_other_providers_none():
    from evals.harness.runner import usage_model_settings

    assert usage_model_settings("anthropic:claude-sonnet-4-6") is None
