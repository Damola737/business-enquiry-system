"""
Evaluation harness for the multi-tenant agent platform.

Implements Phase 2:
- EvalCase and EvalResult models
- Comprehensive metrics (routing accuracy, entity extraction, RAG groundedness, etc.)
- Suite aggregation and reporting
- JSON export for CI/CD integration

Usage:
    python -m eval.runner --suite smoke
    python -m eval.runner --suite smoke --output report.json
"""

from eval.models import (
    EvalCase,
    EvalResult,
    EvalSuiteResult,
    MetricScores,
)

from eval.runner import (
    load_cases,
    evaluate_case,
    calculate_metrics,
    aggregate_results,
    run,
)

__all__ = [
    # Models
    "EvalCase",
    "EvalResult",
    "EvalSuiteResult",
    "MetricScores",
    # Runner
    "load_cases",
    "evaluate_case",
    "calculate_metrics",
    "aggregate_results",
    "run",
]

