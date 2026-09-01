"""Cross-run comparison over write_result JSON files.

Reads one or more result files (the shape produced by
evals.harness.runner_dataset.write_result) and computes, per result:

- per-stage pass rate: mean of that stage's assertion over the cases that
  HAVE the stage key (scenarios differ in expected stages, so a missing
  key is "not expected", never a failure);
- full-flow pass@k: cases are grouped into scenario groups by stripping
  the "[i]" repeat suffix; a group passes if AT LEAST ONE repeat has all
  its STAGE assertions True. Only stage keys (Stage enum values) count —
  semantic detector keys and `completed` are separate signals;
- mean step_count / wasted_calls (from scores);
- semantic flag counts: number of cases where each detector fired.
  Detector polarity is True = failure detected (BAD) — the table renders
  these as "flags:<detector>" columns so a non-zero count reads as bad.

CLI: python -m evals.reporting.compare results/a.json results/b.json
     [--png-dir DIR]   # also emit stage_pass.png + step_count_hist.png
"""
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Sequence, Union

from evals.harness.models import Stage

STAGE_VALUES = [stage.value for stage in Stage]
_STAGE_SET = set(STAGE_VALUES)
_REPEAT_SUFFIX = re.compile(r"\[\d+\]$")


def load_results(paths: Sequence[Union[str, Path]]) -> List[dict]:
    """Parse each result JSON file, preserving argument order."""
    return [json.loads(Path(path).read_text()) for path in paths]


def _group_name(case_name: str) -> str:
    return _REPEAT_SUFFIX.sub("", case_name)


def comparison_rows(results: Sequence[dict]) -> List[dict]:
    """One summary row per result; sorted by (label, model, prompt_id)."""
    rows = []
    for result in results:
        stage_hits: Dict[str, List[int]] = {}   # stage -> [passed, present]
        flags: Dict[str, int] = {}
        groups: Dict[str, List[bool]] = {}
        steps: List[float] = []
        wasted: List[float] = []

        for case in result["cases"]:
            assertions = case["assertions"]
            stage_keys = [k for k in assertions if k in _STAGE_SET]
            for key in stage_keys:
                hit = stage_hits.setdefault(key, [0, 0])
                hit[0] += bool(assertions[key])
                hit[1] += 1
            for key, value in assertions.items():
                if key in _STAGE_SET or key == "completed":
                    continue
                flags[key] = flags.get(key, 0) + bool(value)
            groups.setdefault(_group_name(case["name"]), []).append(
                all(assertions[key] for key in stage_keys)
            )
            steps.append(case["scores"].get("step_count", 0))
            wasted.append(case["scores"].get("wasted_calls", 0))

        n_cases = len(result["cases"])
        rows.append({
            "label": result["label"],
            "model": result["config"]["model"],
            "prompt_id": result["config"]["prompt_id"],
            "stage_rates": {
                key: passed / present for key, (passed, present) in stage_hits.items()
            },
            "pass_at_k": (
                sum(any(repeats) for repeats in groups.values()) / len(groups)
                if groups else 0.0
            ),
            "mean_step_count": sum(steps) / n_cases if n_cases else 0.0,
            "mean_wasted_calls": sum(wasted) / n_cases if n_cases else 0.0,
            "flags": flags,
        })
    rows.sort(key=lambda row: (row["label"], row["model"], row["prompt_id"]))
    return rows


def print_comparison(rows: Sequence[dict]) -> str:
    """Render (and print) an aligned text table; stdlib only."""
    rows = sorted(rows, key=lambda row: (row["label"], row["model"], row["prompt_id"]))
    stage_cols = [
        stage for stage in STAGE_VALUES
        if any(stage in row["stage_rates"] for row in rows)
    ]
    flag_cols = sorted({key for row in rows for key in row["flags"]})
    header = (
        ["label", "model", "prompt", "pass@k", "steps", "wasted"]
        + stage_cols
        + [f"flags:{key}" for key in flag_cols]
    )

    table = []
    for row in rows:
        cells = [
            row["label"],
            row["model"],
            row["prompt_id"],
            f"{row['pass_at_k']:.2f}",
            f"{row['mean_step_count']:.2f}",
            f"{row['mean_wasted_calls']:.2f}",
        ]
        cells += [
            f"{row['stage_rates'][stage]:.2f}" if stage in row["stage_rates"] else "-"
            for stage in stage_cols
        ]
        cells += [str(row["flags"].get(key, 0)) for key in flag_cols]
        table.append(cells)

    widths = [
        max(len(header[i]), *(len(cells[i]) for cells in table)) if table
        else len(header[i])
        for i in range(len(header))
    ]
    lines = [
        "  ".join(cell.ljust(width) for cell, width in zip(cells, widths)).rstrip()
        for cells in [header] + table
    ]
    text = "\n".join(lines)
    print(text)
    return text


def main(argv: Sequence[str] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m evals.reporting.compare",
        description="Compare eval result JSON files across runs.",
    )
    parser.add_argument("paths", nargs="+", help="result JSON files to compare")
    parser.add_argument(
        "--png-dir", default=None,
        help="also write stage_pass.png and step_count_hist.png here",
    )
    args = parser.parse_args(argv)

    results = load_results(args.paths)
    print_comparison(comparison_rows(results))

    if args.png_dir:
        from evals.reporting.plots import stage_pass_bars, step_count_hist

        png_dir = Path(args.png_dir)
        png_dir.mkdir(parents=True, exist_ok=True)
        stage_pass_bars(results, png_dir / "stage_pass.png")
        step_count_hist(results, png_dir / "step_count_hist.png")


if __name__ == "__main__":
    main()
