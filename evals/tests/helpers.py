"""Shared test helpers for evaluator tests.

A plain module (not conftest fixtures) because make_ctx is called with
per-test arguments; evals/tests is a package, so bare ``from conftest
import ...`` does not resolve under pytest — import from here instead.
"""

from pydantic_evals.evaluators import EvaluatorContext
from pydantic_evals.otel.span_tree import SpanTree

from evals.harness.models import RunOutcome


def make_ctx(outcome: RunOutcome) -> EvaluatorContext:
    """Real pydantic-evals EvaluatorContext wrapping a RunOutcome.

    Pins pydantic-evals 2.37 internals: EvaluatorContext takes the private
    ``_span_tree`` kwarg. This is the single place to fix on upgrade.
    """
    return EvaluatorContext(
        name="case",
        inputs=None,
        metadata=None,
        expected_output=None,
        output=outcome,
        duration=0.0,
        _span_tree=SpanTree(),
        attributes={},
        metrics={},
    )
