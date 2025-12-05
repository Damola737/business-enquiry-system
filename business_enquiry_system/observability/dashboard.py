"""
Scoreboard Dashboard for agent performance monitoring.

Phase 9 Implementation: Real-time dashboards with:
- Running average metrics across all Phase 2 dimensions
- Latency histograms
- Error rate trends
- Per-tenant breakdowns
- Live trace inspection
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MetricWindow:
    """Rolling window for metric aggregation."""
    window_size: int = 100  # Number of samples to keep
    values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    
    def add(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a value to the window."""
        self.values.append(value)
        self.timestamps.append(timestamp or datetime.utcnow())
        
        # Trim to window size
        if len(self.values) > self.window_size:
            self.values = self.values[-self.window_size:]
            self.timestamps = self.timestamps[-self.window_size:]
    
    def average(self) -> float:
        """Calculate running average."""
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)
    
    def p50(self) -> float:
        """Calculate 50th percentile."""
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = len(sorted_vals) // 2
        return sorted_vals[idx]
    
    def p95(self) -> float:
        """Calculate 95th percentile."""
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    def p99(self) -> float:
        """Calculate 99th percentile."""
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * 0.99)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    def recent(self, minutes: int = 5) -> List[float]:
        """Get values from the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            v for v, t in zip(self.values, self.timestamps)
            if t >= cutoff
        ]


@dataclass
class TenantMetrics:
    """Metrics for a single tenant."""
    tenant_id: str
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    escalated_requests: int = 0
    
    # Latency metrics
    latency_window: MetricWindow = field(default_factory=MetricWindow)
    
    # Accuracy metrics
    routing_accuracy: MetricWindow = field(default_factory=MetricWindow)
    entity_extraction: MetricWindow = field(default_factory=MetricWindow)
    rag_groundedness: MetricWindow = field(default_factory=MetricWindow)
    
    # Domain breakdown
    requests_by_domain: Dict[str, int] = field(default_factory=dict)
    errors_by_domain: Dict[str, int] = field(default_factory=dict)
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def escalation_rate(self) -> float:
        """Calculate escalation rate."""
        if self.total_requests == 0:
            return 0.0
        return self.escalated_requests / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "tenant_id": self.tenant_id,
            "total_requests": self.total_requests,
            "success_rate": round(self.success_rate(), 3),
            "escalation_rate": round(self.escalation_rate(), 3),
            "latency": {
                "avg": round(self.latency_window.average(), 1),
                "p50": round(self.latency_window.p50(), 1),
                "p95": round(self.latency_window.p95(), 1),
                "p99": round(self.latency_window.p99(), 1),
            },
            "accuracy": {
                "routing": round(self.routing_accuracy.average(), 3),
                "entities": round(self.entity_extraction.average(), 3),
                "rag": round(self.rag_groundedness.average(), 3),
            },
            "by_domain": self.requests_by_domain,
        }


@dataclass 
class ErrorTrend:
    """Track error trends over time."""
    error_category: str
    count: int = 0
    last_seen: Optional[datetime] = None
    sample_messages: List[str] = field(default_factory=list)
    
    def record(self, message: str) -> None:
        """Record an error occurrence."""
        self.count += 1
        self.last_seen = datetime.utcnow()
        if len(self.sample_messages) < 5:
            self.sample_messages.append(message)


class Scoreboard:
    """
    Real-time scoreboard for agent performance.
    
    Tracks:
    - Per-tenant metrics
    - System-wide aggregates
    - Error trends
    - Latency histograms
    """
    
    def __init__(
        self,
        window_size: int = 100,
    ) -> None:
        self.window_size = window_size
        
        # Per-tenant metrics
        self._tenant_metrics: Dict[str, TenantMetrics] = {}
        
        # System-wide metrics
        self._system_latency = MetricWindow(window_size)
        self._system_routing = MetricWindow(window_size)
        self._system_requests = 0
        self._system_errors = 0
        
        # Error tracking
        self._error_trends: Dict[str, ErrorTrend] = {}
        
        # Recent traces for inspection
        self._recent_traces: List[Dict[str, Any]] = []
        self._max_traces = 50
    
    def get_tenant_metrics(self, tenant_id: str) -> TenantMetrics:
        """Get or create metrics for a tenant."""
        if tenant_id not in self._tenant_metrics:
            self._tenant_metrics[tenant_id] = TenantMetrics(tenant_id=tenant_id)
        return self._tenant_metrics[tenant_id]
    
    def record_request(
        self,
        tenant_id: str,
        latency_ms: float,
        domain: Optional[str] = None,
        success: bool = True,
        escalated: bool = False,
        routing_accuracy: float = 1.0,
        entity_extraction: float = 1.0,
        rag_groundedness: float = 1.0,
        trace_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a completed request."""
        metrics = self.get_tenant_metrics(tenant_id)
        
        # Update counts
        metrics.total_requests += 1
        self._system_requests += 1
        
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
            self._system_errors += 1
        
        if escalated:
            metrics.escalated_requests += 1
        
        # Update latency
        metrics.latency_window.add(latency_ms)
        self._system_latency.add(latency_ms)
        
        # Update accuracy metrics
        metrics.routing_accuracy.add(routing_accuracy)
        metrics.entity_extraction.add(entity_extraction)
        metrics.rag_groundedness.add(rag_groundedness)
        self._system_routing.add(routing_accuracy)
        
        # Update domain counts
        if domain:
            domain_key = domain.upper()
            metrics.requests_by_domain[domain_key] = \
                metrics.requests_by_domain.get(domain_key, 0) + 1
            if not success:
                metrics.errors_by_domain[domain_key] = \
                    metrics.errors_by_domain.get(domain_key, 0) + 1
        
        # Store trace for inspection
        if trace_data:
            self._recent_traces.append({
                "timestamp": datetime.utcnow().isoformat(),
                "tenant_id": tenant_id,
                "latency_ms": latency_ms,
                "success": success,
                "domain": domain,
                **trace_data,
            })
            if len(self._recent_traces) > self._max_traces:
                self._recent_traces = self._recent_traces[-self._max_traces:]
    
    def record_error(
        self,
        category: str,
        message: str,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record an error for trend tracking."""
        if category not in self._error_trends:
            self._error_trends[category] = ErrorTrend(error_category=category)
        self._error_trends[category].record(message)
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system-wide summary metrics."""
        return {
            "total_requests": self._system_requests,
            "total_errors": self._system_errors,
            "error_rate": round(
                self._system_errors / max(1, self._system_requests), 3
            ),
            "latency": {
                "avg": round(self._system_latency.average(), 1),
                "p50": round(self._system_latency.p50(), 1),
                "p95": round(self._system_latency.p95(), 1),
                "p99": round(self._system_latency.p99(), 1),
            },
            "routing_accuracy": round(self._system_routing.average(), 3),
            "active_tenants": len(self._tenant_metrics),
        }
    
    def get_tenant_summaries(self) -> List[Dict[str, Any]]:
        """Get summaries for all tenants."""
        return [m.to_dict() for m in self._tenant_metrics.values()]
    
    def get_error_trends(self) -> Dict[str, Any]:
        """Get error trend summary."""
        trends = {}
        for category, trend in self._error_trends.items():
            trends[category] = {
                "count": trend.count,
                "last_seen": trend.last_seen.isoformat() if trend.last_seen else None,
                "samples": trend.sample_messages[:3],
            }
        return trends
    
    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent traces for inspection."""
        return self._recent_traces[-limit:]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data."""
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "system": self.get_system_summary(),
            "tenants": self.get_tenant_summaries(),
            "errors": self.get_error_trends(),
            "recent_traces": self.get_recent_traces(10),
        }
    
    def export_to_json(self, path: Path) -> None:
        """Export dashboard data to JSON file."""
        data = self.get_dashboard_data()
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


# ============================================================
# Legacy Functions for backwards compatibility
# ============================================================

def load_traces(path: str) -> Any:
    """Load traces from JSONL file."""
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def summarize(path: str) -> Dict[str, Any]:
    """Summarize traces from a JSONL file."""
    records = load_traces(path)
    totals = defaultdict(int)
    latency_by_domain: Dict[str, list] = defaultdict(list)

    for rec in records:
        if rec.get("type") == "run_end":
            status = rec.get("status")
            totals[f"runs_{status}"] += 1
            summary = rec.get("summary") or {}
            domain = summary.get("domain") or "UNKNOWN"
            processing = summary.get("processing_time_ms")
            if isinstance(processing, (int, float)):
                latency_by_domain[domain].append(float(processing))

    domain_metrics: Dict[str, Any] = {}
    for domain, values in latency_by_domain.items():
        if not values:
            continue
        values_sorted = sorted(values)
        count = len(values_sorted)
        p95_index = max(int(count * 0.95) - 1, 0)
        domain_metrics[domain] = {
            "count": count,
            "avg_ms": sum(values_sorted) / count,
            "p95_ms": values_sorted[p95_index],
        }

    return {
        "totals": dict(totals),
        "per_domain": domain_metrics,
    }


# ============================================================
# Global Scoreboard Instance
# ============================================================

_scoreboard: Optional[Scoreboard] = None


def get_scoreboard() -> Scoreboard:
    """Get or create the global scoreboard instance."""
    global _scoreboard
    if _scoreboard is None:
        _scoreboard = Scoreboard()
    return _scoreboard


def record_pipeline_result(
    tenant_id: str,
    output: Dict[str, Any],
    latency_ms: float,
) -> None:
    """Convenience function to record a pipeline result."""
    scoreboard = get_scoreboard()
    
    classification = output.get("classification", {})
    domain = classification.get("service_domain")
    success = output.get("status") == "success"
    escalated = output.get("escalated", False)
    
    scoreboard.record_request(
        tenant_id=tenant_id,
        latency_ms=latency_ms,
        domain=domain,
        success=success,
        escalated=escalated,
        trace_data={
            "query": output.get("original_query", "")[:100],
            "agent": output.get("selected_agent", ""),
        },
    )


def print_scoreboard() -> None:
    """Print current scoreboard to console."""
    scoreboard = get_scoreboard()
    summary = scoreboard.get_system_summary()
    
    print("\n" + "=" * 60)
    print("  AGENT SCOREBOARD")
    print("=" * 60)
    
    print(f"\n📊 SYSTEM METRICS")
    print(f"   Total Requests: {summary['total_requests']}")
    print(f"   Error Rate: {summary['error_rate'] * 100:.1f}%")
    print(f"   Routing Accuracy: {summary['routing_accuracy'] * 100:.1f}%")
    
    print(f"\n⏱️  LATENCY")
    lat = summary['latency']
    print(f"   Avg: {lat['avg']:.0f}ms | P50: {lat['p50']:.0f}ms | P95: {lat['p95']:.0f}ms | P99: {lat['p99']:.0f}ms")
    
    print(f"\n🏢 TENANTS ({summary['active_tenants']})")
    for tenant in scoreboard.get_tenant_summaries():
        print(f"   {tenant['tenant_id']}: {tenant['total_requests']} requests, "
              f"{tenant['success_rate'] * 100:.0f}% success")
    
    errors = scoreboard.get_error_trends()
    if errors:
        print(f"\n⚠️  ERROR TRENDS")
        for cat, data in errors.items():
            print(f"   {cat}: {data['count']} occurrences")
    
    print("\n" + "=" * 60)


def main() -> None:
    """CLI entry point for scoreboard."""
    root = os.path.dirname(os.path.dirname(__file__))
    trace_path = os.path.join(root, "logs", "traces.jsonl")
    summary = summarize(trace_path)
    print("Trace Scoreboard")
    print("================")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

