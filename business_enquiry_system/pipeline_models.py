"""
Typed pipeline models shared across stages.

These Pydantic models provide a standardized schema for:
- classification output
- retrieval results
- tool calls
- orchestrator steps
- escalation decisions

Phase 0.2 Implementation: Standardize structured outputs between pipeline stages.
"""

from __future__ import annotations

from datetime import datetime
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
        
        def model_dump(self) -> Dict[str, Any]:
            return self.__dict__

    def Field(default=None, default_factory=None):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default


# ============================================================
# CLASSIFICATION MODELS
# ============================================================

class ClassificationResultModel(BaseModel):
    """Structured classification output from ClassifierAgent."""
    service_domain: str  # AIRTIME, POWER, DATA, MULTI, OTHER
    intent: str
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    sentiment: str  # VERY_NEGATIVE, NEGATIVE, NEUTRAL, POSITIVE
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    reasoning: str = ""  # Internal debugging info, not shown to user


# ============================================================
# RETRIEVAL MODELS
# ============================================================

class RetrievalResult(BaseModel):
    """Single retrieval result from knowledge base search."""
    doc_id: str
    chunk_id: Optional[str] = None
    title: str
    content: str
    relevance_score: float
    tenant_id: Optional[str] = None
    service_domain: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    chunk_context: Optional[str] = None


class RetrievalResultSet(BaseModel):
    """Collection of retrieval results with metadata."""
    query: str
    results: List[RetrievalResult] = Field(default_factory=list)
    total_found: int = 0
    search_method: str = "keyword"
    reranked: bool = False
    retrieval_time_ms: int = 0


# ============================================================
# TOOL CALL MODELS
# ============================================================

class ToolCallRecord(BaseModel):
    """Record of a single tool invocation."""
    tool_name: str
    tool_version: Optional[str] = None
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Optional[Dict[str, Any]] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    duration_ms: int = 0
    retryable: bool = False
    attempt_number: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ToolBudget(BaseModel):
    """Budget constraints for tool usage in a run."""
    max_tool_calls: int = 10
    max_total_time_ms: int = 30000
    max_retries_per_tool: int = 2
    current_calls: int = 0
    current_time_ms: int = 0
    
    def can_call(self) -> bool:
        return self.current_calls < self.max_tool_calls
    
    def record_call(self, duration_ms: int) -> None:
        self.current_calls += 1
        self.current_time_ms += duration_ms


# ============================================================
# ORCHESTRATOR MODELS
# ============================================================

class OrchestratorStep(BaseModel):
    """Single step in the orchestration pipeline."""
    name: str
    agent_name: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    finished_at: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    success: bool = True


class PipelineTrace(BaseModel):
    """Complete trace of a pipeline run."""
    run_id: str
    enquiry_id: str
    tenant_id: str
    steps: List[OrchestratorStep] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    retrieval_results: Optional[RetrievalResultSet] = None
    classification: Optional[ClassificationResultModel] = None
    total_duration_ms: int = 0
    status: str = "pending"


# ============================================================
# ESCALATION MODELS
# ============================================================

class EscalationTrigger(BaseModel):
    """Reason for escalation."""
    trigger_type: str
    description: str
    confidence: float = 1.0
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class EscalationDecision(BaseModel):
    """Decision to escalate to human agent."""
    should_escalate: bool = False
    severity: str = "medium"
    triggers: List[EscalationTrigger] = Field(default_factory=list)
    summary: str = ""
    recommended_team: Optional[str] = None
    context_for_agent: Dict[str, Any] = Field(default_factory=dict)
    
    def add_trigger(self, trigger_type: str, description: str, confidence: float = 1.0) -> None:
        self.triggers.append(EscalationTrigger(
            trigger_type=trigger_type,
            description=description,
            confidence=confidence
        ))
        self.should_escalate = True


# ============================================================
# RESPONSE MODELS
# ============================================================

class Citation(BaseModel):
    """Citation linking a claim to a source."""
    claim: str
    source_doc_id: str
    source_title: Optional[str] = None
    source_snippet: Optional[str] = None
    confidence: float = 1.0


class AgentResponseModel(BaseModel):
    """Standardized response from any agent."""
    success: bool
    agent_name: str
    processing_time_ms: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    confidence: float = 1.0
    fallback_used: bool = False
    citations: List[Citation] = Field(default_factory=list)
    escalation: Optional[EscalationDecision] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ============================================================
# REFLECT STEP MODELS (Phase 3.4)
# ============================================================

class ReflectStepResult(BaseModel):
    """Result of internal reflection after tool/retrieval."""
    has_sufficient_info: bool = False
    missing_info: List[str] = Field(default_factory=list)
    suggested_next_action: Optional[str] = None
    suggested_tool: Optional[str] = None
    policy_triggers: List[str] = Field(default_factory=list)
    should_escalate: bool = False
    reasoning: str = ""


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_classification(data: Dict[str, Any]) -> ClassificationResultModel:
    """Validate and parse classification data."""
    return ClassificationResultModel(**data)


def validate_retrieval_result(data: Dict[str, Any]) -> RetrievalResult:
    """Validate and parse a single retrieval result."""
    return RetrievalResult(**data)


def validate_tool_call(data: Dict[str, Any]) -> ToolCallRecord:
    """Validate and parse a tool call record."""
    return ToolCallRecord(**data)


def validate_escalation(data: Dict[str, Any]) -> EscalationDecision:
    """Validate and parse escalation decision."""
    return EscalationDecision(**data)

