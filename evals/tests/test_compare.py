"""Cross-run comparison (evals/reporting/compare.py) + plots smoke tests.

Synthetic fixtures: two results in the write_result JSON shape.
- result "a": healthy baseline. Its "full" scenario group has one flaky
  repeat (train False) rescued by the other repeat -> pass@k counts the
  group as a pass. Its "minimal" group passes ONLY via a repeat whose
  `completed` assertion is False -> completed is excluded from full-flow.
- result "b": DATA_PREP regression (rate 0.25 vs a's 1.00) and semantic
  flags firing (degenerate_prescriptions, saturated_probabilities) in b
  only. Its "minimal" group passes via a repeat where a semantic detector
  fired -> semantic keys are excluded from full-flow.
"""
import json

import pytest

from evals.reporting.compare import (
    comparison_rows,
    load_results,
    main,
    print_comparison,
)

_SEM_OK = {
    "degenerate_prescriptions": False,
    "zero_cost_prescriptions": False,
    "immutable_drift": False,
    "saturated_probabilities": False,
}


def _case(name, stages, step_count, wasted_calls, completed=True, **sem_overrides):
    assertions = {**stages, **_SEM_OK, **sem_overrides, "completed": completed}
    return {
        "name": name,
        "assertions": assertions,
        "scores": {"step_count": step_count, "wasted_calls": wasted_calls},
        "labels": {},
        "duration": 1.0,
    }


def _result(label, model, cases):
    return {
        "label": label,
        "timestamp": "2026-09-01T00:00:00+00:00",
        "config": {"model": model, "prompt_id": "default", "target": "local", "k": 2},
        "git": {"mcp_server": "deadbeef", "xplainable_client": "1.15.0"},
        "cases": cases,
        "leftovers": [],
    }


def result_a():
    return _result("a", "m1", [
        _case("full[0]",
              {"explore": True, "data_prep": True, "train": True, "report": True},
              10, 0),
        _case("full[1]",  # flaky repeat: rescued by full[0] for pass@k
              {"explore": True, "data_prep": True, "train": False, "report": True},
              12, 1),
        _case("minimal[0]",  # minimal scenario: no "report" stage expected
              {"explore": True, "data_prep": True, "train": False},
              5, 0),
        _case("minimal[1]",  # all stages True but completed False -> still a pass
              {"explore": True, "data_prep": True, "train": True},
              7, 0, completed=False),
    ])


def result_b():
    return _result("b", "m1", [
        _case("full[0]",
              {"explore": True, "data_prep": False, "train": True, "report": True},
              20, 3, degenerate_prescriptions=True),
        _case("full[1]",
              {"explore": True, "data_prep": False, "train": False, "report": False},
              25, 5),
        _case("minimal[0]",  # semantic flag fired but stages all True -> pass
              {"explore": True, "data_prep": True, "train": True},
              6, 0, saturated_probabilities=True),
        _case("minimal[1]",
              {"explore": True, "data_prep": False, "train": True},
              8, 1),
    ])


def _write(tmp_path, result):
    path = tmp_path / f"{result['label']}.json"
    path.write_text(json.dumps(result))
    return path


def _rows_by_label(rows):
    return {row["label"]: row for row in rows}


def test_load_results_round_trips(tmp_path):
    pa, pb = _write(tmp_path, result_a()), _write(tmp_path, result_b())
    assert load_results([pa, pb]) == [result_a(), result_b()]


def test_comparison_rows_exact_metrics():
    rows = _rows_by_label(comparison_rows([result_a(), result_b()]))

    a = rows["a"]
    assert a["model"] == "m1" and a["prompt_id"] == "default"
    assert a["stage_rates"] == pytest.approx(
        {"explore": 1.0, "data_prep": 1.0, "train": 0.5, "report": 1.0}
    )
    assert a["pass_at_k"] == pytest.approx(1.0)
    assert a["mean_step_count"] == pytest.approx(8.5)
    assert a["mean_wasted_calls"] == pytest.approx(0.25)
    assert a["flags"] == {
        "degenerate_prescriptions": 0,
        "zero_cost_prescriptions": 0,
        "immutable_drift": 0,
        "saturated_probabilities": 0,
    }

    b = rows["b"]
    assert b["stage_rates"] == pytest.approx(
        {"explore": 1.0, "data_prep": 0.25, "train": 0.75, "report": 0.5}
    )
    assert b["pass_at_k"] == pytest.approx(0.5)
    assert b["mean_step_count"] == pytest.approx(14.75)
    assert b["mean_wasted_calls"] == pytest.approx(2.25)
    assert b["flags"] == {
        "degenerate_prescriptions": 1,
        "zero_cost_prescriptions": 0,
        "immutable_drift": 0,
        "saturated_probabilities": 1,
    }

    # Regression direction: b's data_prep rate is visibly below a's.
    assert b["stage_rates"]["data_prep"] < a["stage_rates"]["data_prep"]


def test_pass_at_k_rescues_flaky_repeat():
    # a's "full" group: repeat 1 fails train, repeat 0 all-true -> group passes.
    (a,) = comparison_rows([result_a()])
    assert a["pass_at_k"] == pytest.approx(1.0)


def test_completed_and_semantic_keys_excluded_from_full_flow():
    # a's "minimal" group passes only via minimal[1] (completed=False there);
    # b's "minimal" group passes only via minimal[0] (semantic flag True there).
    # If either non-stage key leaked into the all-true check, pass@k would drop.
    (a,) = comparison_rows([result_a()])
    (b,) = comparison_rows([result_b()])
    assert a["pass_at_k"] == pytest.approx(1.0)
    assert b["pass_at_k"] == pytest.approx(0.5)


def test_vacuous_group_without_stage_keys_is_not_a_pass():
    # A malformed case whose assertions carry NO stage keys must not count
    # its group as a full-flow pass via all([]) == True.
    case = {
        "name": "ghost[0]",
        "assertions": {"completed": True},
        "scores": {"step_count": 1, "wasted_calls": 0},
        "labels": {},
        "duration": 1.0,
    }
    (row,) = comparison_rows([_result("v", "m1", [case])])
    assert row["pass_at_k"] == pytest.approx(0.0)


def test_stage_rate_only_averages_cases_with_the_stage():
    # "report" exists on 2 of a's 4 cases (both True) -> 1.0, not 0.5.
    (a,) = comparison_rows([result_a()])
    assert a["stage_rates"]["report"] == pytest.approx(1.0)


def test_print_comparison_table(capsys):
    rows = comparison_rows([result_b(), result_a()])  # unsorted on purpose
    text = print_comparison(rows)
    assert capsys.readouterr().out.rstrip("\n") == text.rstrip("\n")

    lines = text.splitlines()
    header = lines[0].split()
    for col in ("label", "model", "prompt", "pass@k", "steps", "wasted",
                "data_prep", "flags:degenerate_prescriptions"):
        assert col in header

    body = [line.split() for line in lines[1:] if line.strip()]
    by_label = {tokens[header.index("label")]: tokens for tokens in body}
    assert list(by_label) == ["a", "b"]  # deterministic sort by label

    dp = header.index("data_prep")
    assert float(by_label["b"][dp]) < float(by_label["a"][dp])  # regression visible
    assert float(by_label["a"][dp]) == pytest.approx(1.0)
    assert float(by_label["b"][dp]) == pytest.approx(0.25)

    flag = header.index("flags:degenerate_prescriptions")
    assert by_label["a"][flag] == "0" and by_label["b"][flag] == "1"


def test_print_comparison_renders_dash_for_absent_stage():
    # Result "c" has a deploy-bearing case; result "a" has no deploy stage
    # anywhere -> a's deploy cell renders as "-", c's as a rate.
    with_deploy = _result("c", "m1", [
        _case("deployflow[0]", {"explore": True, "deploy": True}, 4, 0),
    ])
    text = print_comparison(comparison_rows([result_a(), with_deploy]))
    lines = text.splitlines()
    header = lines[0].split()
    assert "deploy" in header

    body = [line.split() for line in lines[1:] if line.strip()]
    by_label = {tokens[header.index("label")]: tokens for tokens in body}
    deploy = header.index("deploy")
    assert by_label["a"][deploy] == "-"
    assert float(by_label["c"][deploy]) == pytest.approx(1.0)


def test_cli_main_prints_table_and_emits_plots(tmp_path, capsys):
    pa, pb = _write(tmp_path, result_a()), _write(tmp_path, result_b())
    png_dir = tmp_path / "pngs"

    main([str(pa), str(pb), "--png-dir", str(png_dir)])

    out = capsys.readouterr().out
    assert "data_prep" in out and "pass@k" in out
    pngs = sorted(p.name for p in png_dir.glob("*.png"))
    assert pngs == ["pass_at_k.png", "stage_pass.png", "step_count_hist.png"]
    assert all((png_dir / p).stat().st_size > 0 for p in pngs)


def test_cli_main_requires_paths():
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code != 0


def test_stage_pass_bars_creates_png(tmp_path):
    from evals.reporting.plots import stage_pass_bars

    out = tmp_path / "stages.png"
    stage_pass_bars([result_a(), result_b()], out)
    assert out.exists() and out.stat().st_size > 0


def test_step_count_hist_creates_png(tmp_path):
    from evals.reporting.plots import step_count_hist

    out = tmp_path / "steps.png"
    step_count_hist([result_a(), result_b()], out)
    assert out.exists() and out.stat().st_size > 0


def test_pass_at_k_estimate_known_values():
    from evals.reporting.plots import pass_at_k_estimate

    # n=3 samples, c=1 pass: pass@1 = 1/3, pass@2 = 2/3, pass@3 = 1.
    assert pass_at_k_estimate(3, 1, 1) == pytest.approx(1 / 3)
    assert pass_at_k_estimate(3, 1, 2) == pytest.approx(2 / 3)
    assert pass_at_k_estimate(3, 1, 3) == pytest.approx(1.0)
    assert pass_at_k_estimate(2, 0, 1) == 0.0
    assert pass_at_k_estimate(2, 2, 1) == 1.0


def test_pass_at_k_curves_uses_full_flow_rule():
    from evals.reporting.plots import pass_at_k_curves

    # result_a: both groups n=2, c=1 (full[1] train False; minimal[0] train
    # False, minimal[1] passes despite completed=False).
    # result_b: full c=0 (data_prep False in both), minimal c=1 (semantic
    # flag never fails a case; minimal[1] data_prep False).
    curves = pass_at_k_curves([result_a(), result_b()])
    assert [label for label, _ in curves] == ["a", "b"]
    a_points = dict(curves[0][1])
    b_points = dict(curves[1][1])
    assert a_points[1] == pytest.approx(0.5)   # mean(1/2, 1/2)
    assert a_points[2] == pytest.approx(1.0)   # mean(1, 1)
    assert b_points[1] == pytest.approx(0.25)  # mean(0, 1/2)
    assert b_points[2] == pytest.approx(0.5)   # mean(0, 1)


def test_pass_at_k_curve_creates_png(tmp_path):
    from evals.reporting.plots import pass_at_k_curve

    out = tmp_path / "pass_at_k.png"
    pass_at_k_curve([result_a(), result_b()], out)
    assert out.exists() and out.stat().st_size > 0


def test_duplicate_labels_deduped_for_legends():
    from evals.reporting.plots import dedupe_labels

    assert dedupe_labels(["a", "a", "b", "a"]) == ["a", "a (2)", "b", "a (3)"]


def test_cli_emits_pass_at_k_png(tmp_path):
    png_dir = tmp_path / "pngs"
    pa, pb = _write(tmp_path, result_a()), _write(tmp_path, result_b())
    main([str(pa), str(pb), "--png-dir", str(png_dir)])
    assert (png_dir / "pass_at_k.png").stat().st_size > 0


def _with_costs(result, cost_per_case):
    for case in result["cases"]:
        case["usage"] = {"input_tokens": 100, "output_tokens": 10,
                         "cost_usd": cost_per_case}
    return result


def test_comparison_rows_total_cost():
    (row,) = comparison_rows([_with_costs(result_a(), 0.05)])
    assert row["total_cost_usd"] == pytest.approx(0.20)


def test_comparison_rows_cost_none_when_absent():
    # Old result files have no "usage" key at all -> cost is None, not 0.
    (row,) = comparison_rows([result_a()])
    assert row["total_cost_usd"] is None


def test_print_comparison_renders_cost_column_with_dash_for_absent():
    rows = comparison_rows([_with_costs(result_a(), 0.05), result_b()])
    text = print_comparison(rows)
    lines = text.splitlines()
    header = lines[0].split()
    assert "cost" in header

    body = [line.split() for line in lines[1:] if line.strip()]
    by_label = {tokens[header.index("label")]: tokens for tokens in body}
    cost = header.index("cost")
    assert by_label["a"][cost] == "0.20"
    assert by_label["b"][cost] == "-"
