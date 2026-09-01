"""Plots over write_result JSON dicts (same input as compare.py).

Headless by design: the Agg backend is selected BEFORE pyplot is imported
so these work in CI / without a display.
"""
import matplotlib

matplotlib.use("Agg")

from pathlib import Path
from typing import Sequence, Union

import matplotlib.pyplot as plt

from evals.reporting.compare import STAGE_VALUES, comparison_rows


def stage_pass_bars(results: Sequence[dict], out_png: Union[str, Path]) -> None:
    """Grouped bar chart: per-stage pass rate, one bar group per stage,
    one bar per result (legend = result label)."""
    rows = comparison_rows(results)
    stage_cols = [
        stage for stage in STAGE_VALUES
        if any(stage in row["stage_rates"] for row in rows)
    ]
    fig, ax = plt.subplots(figsize=(10, 5))
    n = max(len(rows), 1)
    width = 0.8 / n
    for j, row in enumerate(rows):
        heights = [row["stage_rates"].get(stage, 0.0) for stage in stage_cols]
        ax.bar(
            [i + j * width for i in range(len(stage_cols))],
            heights, width=width, label=row["label"],
        )
    ax.set_xticks([i + 0.4 - width / 2 for i in range(len(stage_cols))])
    ax.set_xticklabels(stage_cols, rotation=45, ha="right")
    ax.set_ylabel("stage pass rate")
    ax.set_ylim(0, 1.05)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def step_count_hist(results: Sequence[dict], out_png: Union[str, Path]) -> None:
    """Side-by-side step_count distributions, one series per result."""
    data = [
        [case["scores"].get("step_count", 0) for case in result["cases"]]
        for result in results
    ]
    labels = [result["label"] for result in results]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(data, label=labels)
    ax.set_xlabel("step_count")
    ax.set_ylabel("cases")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
