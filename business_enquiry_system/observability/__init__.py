"""
Observability package.

Implements Phase 0, 1, and 9:
- Run metadata and versioning
- JSONL trace store with spans/events
- PII redaction
- Scoreboard and dashboards

Contains tracing, run metadata, and metrics utilities shared across the
multi-tenant agent platform.
"""

from observability.run_metadata import (
    PromptBundle,
    RunMetadata,
    compute_tenant_config_version,
    compute_toolset_version,
)

from observability.trace_store import TraceStore

from observability.dashboard import (
    MetricWindow,
    TenantMetrics,
    ErrorTrend,
    Scoreboard,
    get_scoreboard,
    record_pipeline_result,
    print_scoreboard,
    summarize,
)

__all__ = [
    # Run metadata
    "PromptBundle",
    "RunMetadata",
    "compute_tenant_config_version",
    "compute_toolset_version",
    # Trace store
    "TraceStore",
    # Dashboard
    "MetricWindow",
    "TenantMetrics",
    "ErrorTrend",
    "Scoreboard",
    "get_scoreboard",
    "record_pipeline_result",
    "print_scoreboard",
    "summarize",
]

