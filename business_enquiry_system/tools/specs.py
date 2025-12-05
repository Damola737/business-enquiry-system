"""
Tool specifications and registry.

Phase 4 Implementation: Tool platform with ToolSpec, ToolRegistry,
search_tools, budgets, and error handling.
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

    def Field(default=None, default_factory=None):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default


class ToolExample(BaseModel):
    """Example usage of a tool."""
    description: str
    input: Dict[str, Any]
    expected_output: Dict[str, Any]


class ToolSpec(BaseModel):
    """
    Complete specification for a tool.
    
    Includes schema, examples, error taxonomy, and permissions.
    """
    name: str
    description: str
    version: str = "1.0.0"
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    examples: List[ToolExample] = Field(default_factory=list)
    error_taxonomy: List[str] = Field(default_factory=lambda: [
        "auth", "not_found", "validation", "rate_limit", "transient", "timeout"
    ])
    permissions: str = "read_only"  # read_only, write_low_risk, write_high_risk
    tenant_scoped: bool = True
    requires_confirmation: bool = False  # For high-risk operations
    max_retries: int = 2
    timeout_ms: int = 10000
    idempotency_key_field: Optional[str] = None  # For write operations


class ToolError(BaseModel):
    """Standardized tool error for model repair."""
    error_category: str  # auth, not_found, validation, rate_limit, transient
    human_message: str
    model_fix_hint: str
    retryable: bool = False
    missing_fields: List[str] = Field(default_factory=list)
    invalid_fields: Dict[str, str] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Standardized tool execution result."""
    tool_name: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None
    duration_ms: int = 0
    attempt_number: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ToolBudget(BaseModel):
    """Budget constraints for tool usage in a run."""
    max_tool_calls: int = 10
    max_total_time_ms: int = 30000
    max_retries_per_tool: int = 2
    calls_made: int = 0
    time_used_ms: int = 0
    retries_by_tool: Dict[str, int] = Field(default_factory=dict)
    
    def can_call(self, tool_name: str) -> bool:
        """Check if we can make another call to this tool."""
        if self.calls_made >= self.max_tool_calls:
            return False
        retries = self.retries_by_tool.get(tool_name, 0)
        if retries >= self.max_retries_per_tool:
            return False
        return True
    
    def record_call(self, tool_name: str, duration_ms: int, is_retry: bool = False) -> None:
        """Record a tool call."""
        self.calls_made += 1
        self.time_used_ms += duration_ms
        if is_retry:
            self.retries_by_tool[tool_name] = self.retries_by_tool.get(tool_name, 0) + 1
    
    def get_remaining(self) -> Dict[str, int]:
        """Get remaining budget."""
        return {
            "calls": self.max_tool_calls - self.calls_made,
            "time_ms": self.max_total_time_ms - self.time_used_ms,
        }


class ToolRegistry:
    """
    Registry for tool specifications with discovery support.
    """
    
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        self._core_tools: List[str] = []  # Always loaded tools
    
    def register(self, spec: ToolSpec, is_core: bool = False) -> None:
        """Register a tool specification."""
        self._tools[spec.name] = spec
        if is_core and spec.name not in self._core_tools:
            self._core_tools.append(spec.name)
    
    def get(self, name: str) -> Optional[ToolSpec]:
        """Get a tool specification by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[ToolSpec]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def list_core_tools(self) -> List[ToolSpec]:
        """List only core (always-loaded) tools."""
        return [self._tools[name] for name in self._core_tools if name in self._tools]
    
    def search_tools(self, query: str) -> List[ToolSpec]:
        """
        Search for tools matching a query.
        
        This allows the agent to discover tools on-demand rather than
        loading all tools into context.
        """
        term = query.lower()
        matches = []
        for spec in self._tools.values():
            score = 0
            if term in spec.name.lower():
                score += 3
            if term in spec.description.lower():
                score += 2
            # Check examples
            for example in spec.examples:
                if term in example.description.lower():
                    score += 1
                    break
            if score > 0:
                matches.append((score, spec))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        return [spec for _, spec in matches]
    
    def get_tools_for_context(self, route: Optional[str] = None, include_discovery: bool = True) -> List[ToolSpec]:
        """
        Get tools to include in context for a specific route.
        
        Returns core tools plus optionally the search_tools meta-tool.
        """
        tools = self.list_core_tools()
        
        if include_discovery and "search_tools" not in [t.name for t in tools]:
            # Add the search_tools meta-tool
            search_tool = ToolSpec(
                name="search_tools",
                description="Search for additional tools by keyword. Use when you need a capability not in your current toolset.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term for finding tools"}
                    },
                    "required": ["query"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "tools": {"type": "array", "items": {"type": "object"}}
                    }
                },
                permissions="read_only",
                tenant_scoped=False,
            )
            tools.append(search_tool)
        
        return tools


def create_tool_error(
    category: str,
    human_message: str,
    model_fix_hint: str,
    retryable: bool = False,
    missing_fields: Optional[List[str]] = None,
    invalid_fields: Optional[Dict[str, str]] = None,
) -> ToolError:
    """Helper to create a standardized tool error."""
    return ToolError(
        error_category=category,
        human_message=human_message,
        model_fix_hint=model_fix_hint,
        retryable=retryable,
        missing_fields=missing_fields or [],
        invalid_fields=invalid_fields or {},
    )


def build_default_registry() -> ToolRegistry:
    """Build the default tool registry with core tools."""
    registry = ToolRegistry()
    
    # KB Search - Core tool
    registry.register(
        ToolSpec(
            name="kb_search",
            description="Search the tenant knowledge base for relevant documents, FAQs, and pricing information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "domain": {"type": "string", "description": "Optional: filter by domain (AIRTIME, POWER, DATA)"},
                    "limit": {"type": "integer", "description": "Max results to return", "default": 5}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "total_found": {"type": "integer"}
                }
            },
            examples=[
                ToolExample(
                    description="Search for airtime pricing",
                    input={"query": "MTN airtime pricing", "domain": "AIRTIME"},
                    expected_output={"results": [{"title": "Airtime Pricing", "content": "..."}], "total_found": 1}
                )
            ],
            error_taxonomy=["not_found", "validation", "transient"],
            permissions="read_only",
            tenant_scoped=True,
        ),
        is_core=True
    )
    
    # Build CTA - Core tool
    registry.register(
        ToolSpec(
            name="build_cta",
            description="Build a call-to-action message with purchase link for a service.",
            input_schema={
                "type": "object",
                "properties": {
                    "service": {"type": "string", "enum": ["airtime", "power", "data"]},
                    "network_or_disco": {"type": "string", "description": "Network (MTN, Airtel, Glo, 9Mobile) or DISCO name"},
                    "amount": {"type": "number", "description": "Transaction amount"},
                    "recipient": {"type": "string", "description": "Phone or meter number"}
                },
                "required": ["service"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "url": {"type": "string"}
                }
            },
            examples=[
                ToolExample(
                    description="Build airtime CTA",
                    input={"service": "airtime", "network_or_disco": "MTN", "amount": 1000, "recipient": "08012345678"},
                    expected_output={"text": "Click to purchase MTN airtime...", "url": "https://..."}
                )
            ],
            permissions="read_only",
            tenant_scoped=True,
        ),
        is_core=True
    )
    
    # Validate Phone - Utility tool (not core, discoverable)
    registry.register(
        ToolSpec(
            name="validate_phone",
            description="Validate a Nigerian phone number and identify the network.",
            input_schema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to validate"}
                },
                "required": ["phone"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "valid": {"type": "boolean"},
                    "network": {"type": "string"},
                    "formatted": {"type": "string"}
                }
            },
            permissions="read_only",
            tenant_scoped=False,
        ),
        is_core=False
    )
    
    # Validate Meter - Utility tool
    registry.register(
        ToolSpec(
            name="validate_meter",
            description="Validate an electricity meter number.",
            input_schema={
                "type": "object",
                "properties": {
                    "meter_number": {"type": "string"},
                    "disco": {"type": "string", "description": "DISCO name (EKEDC, IKEDC, etc.)"}
                },
                "required": ["meter_number"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "valid": {"type": "boolean"},
                    "meter_type": {"type": "string"},
                    "customer_name": {"type": "string"}
                }
            },
            permissions="read_only",
            tenant_scoped=True,
        ),
        is_core=False
    )
    
    # Escalate - Core tool
    registry.register(
        ToolSpec(
            name="escalate_to_human",
            description="Escalate the conversation to a human agent. Use when you cannot resolve the issue or customer explicitly requests human support.",
            input_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for escalation"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "context_summary": {"type": "string", "description": "Brief summary for the human agent"}
                },
                "required": ["reason", "severity"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "estimated_wait": {"type": "string"}
                }
            },
            permissions="write_low_risk",
            tenant_scoped=True,
        ),
        is_core=True
    )
    
    return registry

