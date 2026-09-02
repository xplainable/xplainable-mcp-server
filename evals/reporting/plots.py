"""Plots over write_result JSON dicts (same input as compare.py).

Headless by design: the Agg backend is selected BEFORE pyplot is imported
so these work in CI / without a display.
"""
import matplotlib

matplotlib.use("Agg")

from math import comb
from pathlib import Path
from typing import List, Sequence, Tuple, Union

import matplotlib.pyplot as plt  # noqa: E402  (must follow matplotlib.use)

from evals.harness.models import Stage
from evals.reporting.compare import (
    _group_name,
    case_full_flow_pass,
    comparison_rows,
    present_stages,
)

_STAGE_ORDER = [stage.value for stage in Stage]


def dedupe_labels(labels: Sequence[str]) -> List[str]:
    """Disambiguate repeated labels for legends: a, a (2), a (3), ..."""
    seen: dict = {}
    out = []
    for label in labels:
        seen[label] = seen.get(label, 0) + 1
        out.append(label if seen[label] == 1 else f"{label} ({seen[label]})")
    return out


def _style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)


def pass_at_k_estimate(n: int, c: int, k: int) -> float:
    """Unbiased pass@k: 1 - C(n-c, k) / C(n, k) over n samples, c passes."""
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_at_k_curves(
    results: Sequence[dict],
) -> List[Tuple[str, List[Tuple[int, float]]]]:
    """Per result: [(k, mean pass@k across scenario groups), ...] for
    k = 1..max repeats; groups with fewer than k repeats are skipped at
    that k. Full-flow pass rule is compare.case_full_flow_pass."""
    curves = []
    for result, label in zip(results, dedupe_labels([r["label"] for r in results])):
        groups: dict = {}
        for case in result["cases"]:
            groups.setdefault(_group_name(case["name"]), []).append(
                case_full_flow_pass(case)
            )
        counts = [(len(passes), sum(passes)) for passes in groups.values()]
        max_n = max((n for n, _ in counts), default=0)
        points = []
        for k in range(1, max_n + 1):
            estimates = [
                pass_at_k_estimate(n, c, k) for n, c in counts if n >= k
            ]
            points.append((k, sum(estimates) / len(estimates)))
        curves.append((label, points))
    return curves


def pass_at_k_curve(results: Sequence[dict], out_png: Union[str, Path]) -> None:
    """Standard pass@k line chart: x = k, y = pass@k, one line per result."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    max_k = 1
    for label, points in pass_at_k_curves(results):
        ks = [k for k, _ in points]
        ax.plot(ks, [rate for _, rate in points], marker="o", label=label)
        max_k = max(max_k, *ks) if ks else max_k
    ax.set_xlabel("k (repeats)")
    ax.set_ylabel("pass@k")
    ax.set_xticks(range(1, max_k + 1))
    ax.set_ylim(-0.02, 1.05)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def stage_pass_bars(results: Sequence[dict], out_png: Union[str, Path]) -> None:
    """Per-stage pass-rate profile: stages on x (pipeline order), one
    marker-line per result. Stages a run doesn't expect are left blank."""
    rows = comparison_rows(results)
    stage_cols = present_stages(rows)
    labels = dedupe_labels([row["label"] for row in rows])
    fig, ax = plt.subplots(figsize=(10, 4.5))
    xs = range(len(stage_cols))
    for row, label in zip(rows, labels):
        ys = [row["stage_rates"].get(stage) for stage in stage_cols]
        ax.plot(xs, ys, marker="o", linewidth=1.8, label=label)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(stage_cols, rotation=45, ha="right")
    ax.set_ylabel("stage pass rate")
    ax.set_ylim(-0.02, 1.05)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def step_count_hist(results: Sequence[dict], out_png: Union[str, Path]) -> None:
    """Side-by-side step_count distributions, one series per result."""
    data = [
        [case["scores"].get("step_count", 0) for case in result["cases"]]
        for result in results
    ]
    labels = dedupe_labels([result["label"] for result in results])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(data, label=labels, edgecolor="white")
    ax.set_xlabel("step_count")
    ax.set_ylabel("cases")
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
