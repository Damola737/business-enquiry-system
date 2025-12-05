"""
Eval models for comprehensive evaluation harness.

Phase 2 Implementation: Typed evaluation with rich metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field  # type: ignore
except Exception:  # pragma: no cover
    class BaseModel:  # type: ignore
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> Dict[str, Any]:
            return self.__dict__

    def Field(default=None, default_factory=None):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default


class EvalCase(BaseModel):
    """
    A single evaluation test case.
    
    Attributes:
        id: Unique case identifier
        tenant_id: Tenant context for the test
        input_messages: Conversation history leading to the query
        expected_route: Expected agent route (e.g., "AirtimeSalesAgent")
        expected_domain: Expected service domain (e.g., "airtime")
        expected_intent: Expected user intent (e.g., "purchase")
        expected_entities: Expected extracted entities (e.g., {"phone": "08012345678"})
        expected_must_include: Tokens that must appear in response
        expected_must_not_include: Tokens that must not appear in response
        expected_escalation: Whether escalation is expected
        expected_tool_calls: Expected tool names to be called
        rag_sources: Expected KB sources to be retrieved
        difficulty: Test difficulty level for stratification
        tags: Labels for filtering/grouping tests
        metadata: Additional test metadata
    """
    id: str = ""
    tenant_id: str = "legacy-ng-telecom"
    input_messages: List[str] = Field(default_factory=list)
    expected_route: Optional[str] = None
    expected_domain: Optional[str] = None
    expected_intent: Optional[str] = None
    expected_entities: Dict[str, Any] = Field(default_factory=dict)
    expected_must_include: List[str] = Field(default_factory=list)
    expected_must_not_include: List[str] = Field(default_factory=list)
    expected_escalation: Optional[bool] = None
    expected_tool_calls: List[str] = Field(default_factory=list)
    rag_sources: List[str] = Field(default_factory=list)
    difficulty: str = "medium"  # easy, medium, hard, adversarial
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class MetricScores:
    """
    Detailed scores for each evaluation dimension.
    
    Phase 2 Metrics:
    - routing_accuracy: Did the classifier pick the correct agent?
    - entity_extraction: Were all expected entities extracted correctly?
    - rag_groundedness: Is response grounded in retrieved knowledge?
    - escalation_correctness: Did escalation happen when/only when expected?
    - tool_efficiency: Did the agent use tools appropriately?
    - response_quality: Overall response quality metrics
    """
    routing_accuracy: float = 0.0
    entity_extraction: float = 0.0
    rag_groundedness: float = 0.0
    escalation_correctness: float = 0.0
    tool_efficiency: float = 0.0
    response_quality: float = 0.0
    
    # Detailed breakdowns
    entities_found: Dict[str, Any] = field(default_factory=dict)
    entities_missing: List[str] = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    tools_expected: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    sources_expected: List[str] = field(default_factory=list)
    
    def overall_score(self) -> float:
        """Calculate weighted overall score."""
        weights = {
            "routing_accuracy": 0.25,
            "entity_extraction": 0.20,
            "rag_groundedness": 0.20,
            "escalation_correctness": 0.15,
            "tool_efficiency": 0.10,
            "response_quality": 0.10,
        }
        score = (
            self.routing_accuracy * weights["routing_accuracy"] +
            self.entity_extraction * weights["entity_extraction"] +
            self.rag_groundedness * weights["rag_groundedness"] +
            self.escalation_correctness * weights["escalation_correctness"] +
            self.tool_efficiency * weights["tool_efficiency"] +
            self.response_quality * weights["response_quality"]
        )
        return round(score, 3)


class EvalResult(BaseModel):
    """
    Result of evaluating a single test case.
    
    Includes both pass/fail judgments and detailed metrics.
    """
    case: EvalCase
    passed: bool
    domain_ok: bool
    intent_ok: bool
    content_ok: bool
    route_ok: bool = True
    escalation_ok: bool = True
    entities_ok: bool = True
    tools_ok: bool = True
    
    # Detailed metrics
    metrics: Optional[MetricScores] = None
    
    # Execution details
    latency_ms: int = 0
    token_count: int = 0
    
    details: Dict[str, Any] = Field(default_factory=dict)
    
    def to_report_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "case_id": self.case.id,
            "tenant_id": self.case.tenant_id,
            "passed": self.passed,
            "checks": {
                "domain": self.domain_ok,
                "intent": self.intent_ok,
                "content": self.content_ok,
                "route": self.route_ok,
                "escalation": self.escalation_ok,
                "entities": self.entities_ok,
                "tools": self.tools_ok,
            },
            "metrics": {
                "routing_accuracy": self.metrics.routing_accuracy if self.metrics else 0,
                "entity_extraction": self.metrics.entity_extraction if self.metrics else 0,
                "rag_groundedness": self.metrics.rag_groundedness if self.metrics else 0,
                "overall": self.metrics.overall_score() if self.metrics else 0,
            },
            "latency_ms": self.latency_ms,
        }


@dataclass
class EvalSuiteResult:
    """
    Aggregated results for an entire test suite.
    """
    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    
    # Aggregate metrics
    avg_routing_accuracy: float = 0.0
    avg_entity_extraction: float = 0.0
    avg_rag_groundedness: float = 0.0
    avg_escalation_correctness: float = 0.0
    avg_tool_efficiency: float = 0.0
    avg_response_quality: float = 0.0
    avg_overall_score: float = 0.0
    
    # Performance stats
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens: int = 0
    
    # Results by category
    results_by_domain: Dict[str, Dict[str, int]] = field(default_factory=dict)
    results_by_difficulty: Dict[str, Dict[str, int]] = field(default_factory=dict)
    results_by_tag: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Individual results
    results: List[EvalResult] = field(default_factory=list)
    
    def pass_rate(self) -> float:
        """Calculate overall pass rate."""
        if self.total_cases == 0:
            return 0.0
        return round(self.passed_cases / self.total_cases, 3)
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Generate summary report."""
        return {
            "suite": self.suite_name,
            "total": self.total_cases,
            "passed": self.passed_cases,
            "failed": self.failed_cases,
            "pass_rate": self.pass_rate(),
            "metrics": {
                "routing_accuracy": self.avg_routing_accuracy,
                "entity_extraction": self.avg_entity_extraction,
                "rag_groundedness": self.avg_rag_groundedness,
                "escalation_correctness": self.avg_escalation_correctness,
                "tool_efficiency": self.avg_tool_efficiency,
                "overall": self.avg_overall_score,
            },
            "performance": {
                "avg_latency_ms": self.avg_latency_ms,
                "p95_latency_ms": self.p95_latency_ms,
                "total_tokens": self.total_tokens,
            },
        }

