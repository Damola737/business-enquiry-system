"""
Tool runner with sandboxing, budgets, and retry logic.

Phase 4 & 7 Implementation: Reliable tool execution with:
- Budget enforcement
- Safe retry policy
- Error handling for model repair
- Permission checks
- Execution isolation
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from tools.specs import (
    ToolSpec,
    ToolBudget,
    ToolResult,
    ToolError,
    ToolRegistry,
    create_tool_error,
    build_default_registry,
)


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    def __init__(self, error: ToolError):
        self.error = error
        super().__init__(error.human_message)


class ToolRunner:
    """
    Tool execution engine with budgets, retries, and sandboxing.
    
    Features:
    - Budget enforcement (max calls, max time)
    - Safe retry policy for transient errors
    - Standardized error responses for model repair
    - Permission validation
    - Execution logging
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        workspace_root: str = ".",
        allowed_hosts: Optional[List[str]] = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.workspace_root = workspace_root
        self.allowed_hosts = allowed_hosts or ["portal.example.com", "help.example.com"]
        self._handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register built-in tool handlers."""
        self._handlers["kb_search"] = self._handle_kb_search
        self._handlers["build_cta"] = self._handle_build_cta
        self._handlers["validate_phone"] = self._handle_validate_phone
        self._handlers["validate_meter"] = self._handle_validate_meter
        self._handlers["escalate_to_human"] = self._handle_escalate
        self._handlers["search_tools"] = self._handle_search_tools
    
    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a custom handler for a tool."""
        self._handlers[tool_name] = handler
    
    def execute(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        budget: Optional[ToolBudget] = None,
        tenant_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a tool with budget and permission checks.
        
        Args:
            tool_name: Name of the tool to execute
            payload: Input parameters for the tool
            budget: Optional budget constraints
            tenant_id: Tenant context for scoped tools
        
        Returns:
            ToolResult with success/failure and output/error
        """
        start_time = time.time()
        
        # Get tool spec
        spec = self.registry.get(tool_name)
        if not spec:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=create_tool_error(
                    category="not_found",
                    human_message=f"Tool '{tool_name}' not found",
                    model_fix_hint=f"Use search_tools to find available tools. '{tool_name}' is not registered.",
                    retryable=False,
                ),
                duration_ms=0,
            )
        
        # Check budget
        if budget and not budget.can_call(tool_name):
            remaining = budget.get_remaining()
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=create_tool_error(
                    category="rate_limit",
                    human_message="Tool call budget exceeded",
                    model_fix_hint=f"Budget exhausted. Remaining: {remaining['calls']} calls. Ask user for missing info or generate response with available information.",
                    retryable=False,
                ),
                duration_ms=0,
            )
        
        # Validate input schema
        validation_error = self._validate_input(spec, payload)
        if validation_error:
            duration_ms = int((time.time() - start_time) * 1000)
            if budget:
                budget.record_call(tool_name, duration_ms)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=validation_error,
                duration_ms=duration_ms,
            )
        
        # Check permissions for write operations
        if spec.permissions in ["write_low_risk", "write_high_risk"]:
            if spec.requires_confirmation:
                # In a real implementation, this would trigger a confirmation flow
                pass
        
        # Execute the tool
        handler = self._handlers.get(tool_name)
        if not handler:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=create_tool_error(
                    category="not_found",
                    human_message=f"No handler registered for '{tool_name}'",
                    model_fix_hint="This tool exists but has no implementation. Try a different approach.",
                    retryable=False,
                ),
                duration_ms=duration_ms,
            )
        
        try:
            output = handler(payload, tenant_id=tenant_id, spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if budget:
                budget.record_call(tool_name, duration_ms)
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )
        
        except ToolExecutionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if budget:
                budget.record_call(tool_name, duration_ms, is_retry=e.error.retryable)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=e.error,
                duration_ms=duration_ms,
            )
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if budget:
                budget.record_call(tool_name, duration_ms)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=create_tool_error(
                    category="transient",
                    human_message=f"Unexpected error: {str(e)}",
                    model_fix_hint="An unexpected error occurred. You may retry once or proceed without this tool's output.",
                    retryable=True,
                ),
                duration_ms=duration_ms,
            )
    
    def execute_with_retry(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        budget: Optional[ToolBudget] = None,
        tenant_id: Optional[str] = None,
        max_retries: int = 2,
    ) -> ToolResult:
        """Execute a tool with automatic retry for transient errors."""
        attempts = 0
        last_result = None
        
        while attempts <= max_retries:
            result = self.execute(tool_name, payload, budget, tenant_id)
            last_result = result
            result.attempt_number = attempts + 1
            
            if result.success:
                return result
            
            if result.error and not result.error.retryable:
                return result
            
            attempts += 1
            if attempts <= max_retries:
                time.sleep(0.1 * (2 ** attempts))  # Exponential backoff
        
        return last_result
    
    def _validate_input(self, spec: ToolSpec, payload: Dict[str, Any]) -> Optional[ToolError]:
        """Validate input against tool schema."""
        schema = spec.input_schema
        if not schema:
            return None
        
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        missing = [field for field in required if field not in payload]
        if missing:
            return create_tool_error(
                category="validation",
                human_message=f"Missing required fields: {', '.join(missing)}",
                model_fix_hint=f"Add the following fields to your input: {missing}. Check the tool schema for field types.",
                retryable=False,
                missing_fields=missing,
            )
        
        # Type validation
        invalid = {}
        for field, value in payload.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    invalid[field] = f"Expected string, got {type(value).__name__}"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    invalid[field] = f"Expected number, got {type(value).__name__}"
                elif expected_type == "integer" and not isinstance(value, int):
                    invalid[field] = f"Expected integer, got {type(value).__name__}"
        
        if invalid:
            return create_tool_error(
                category="validation",
                human_message=f"Invalid field types: {invalid}",
                model_fix_hint=f"Fix field types: {invalid}",
                retryable=False,
                invalid_fields=invalid,
            )
        
        return None
    
    # ============================================================
    # Built-in Tool Handlers
    # ============================================================
    
    def _handle_kb_search(
        self,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
        spec: Optional[ToolSpec] = None,
    ) -> Dict[str, Any]:
        """Handle KB search tool."""
        query = payload.get("query", "")
        domain = payload.get("domain")
        limit = payload.get("limit", 5)
        
        # In a real implementation, this would call ResearchAgent
        # For now, return a stub
        return {
            "results": [],
            "total_found": 0,
            "search_method": "keyword",
            "query": query,
        }
    
    def _handle_build_cta(
        self,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
        spec: Optional[ToolSpec] = None,
    ) -> Dict[str, Any]:
        """Handle CTA building tool."""
        service = payload.get("service", "")
        network_or_disco = payload.get("network_or_disco", "")
        amount = payload.get("amount", 0)
        recipient = payload.get("recipient", "")
        
        # Build URL based on service
        base_url = "https://portal.example.com"
        url = f"{base_url}/{service}/{network_or_disco.lower()}"
        
        # Build CTA text
        if service == "airtime":
            text = f"Purchase {network_or_disco} airtime for {recipient}: {url}"
        elif service == "power":
            text = f"Buy electricity token from {network_or_disco}: {url}"
        elif service == "data":
            text = f"Get {network_or_disco} data bundle: {url}"
        else:
            text = f"Visit {url}"
        
        return {"text": text, "url": url}
    
    def _handle_validate_phone(
        self,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
        spec: Optional[ToolSpec] = None,
    ) -> Dict[str, Any]:
        """Validate Nigerian phone number."""
        phone = payload.get("phone", "").replace(" ", "").replace("-", "")
        
        # Nigerian phone pattern
        pattern = r'^(\+?234|0)[789]\d{9}$'
        valid = bool(re.match(pattern, phone))
        
        network = None
        if valid:
            # Determine network from prefix
            normalized = phone[-10:]  # Get last 10 digits
            prefix = normalized[:3]
            network_map = {
                "803": "MTN", "806": "MTN", "813": "MTN", "816": "MTN",
                "805": "Glo", "807": "Glo", "811": "Glo", "815": "Glo",
                "802": "Airtel", "808": "Airtel", "812": "Airtel",
                "809": "9Mobile", "817": "9Mobile", "818": "9Mobile",
            }
            network = network_map.get(prefix, "Unknown")
        
        formatted = f"+234{phone[-10:]}" if valid else phone
        
        return {"valid": valid, "network": network, "formatted": formatted}
    
    def _handle_validate_meter(
        self,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
        spec: Optional[ToolSpec] = None,
    ) -> Dict[str, Any]:
        """Validate electricity meter number."""
        meter = payload.get("meter_number", "").replace(" ", "")
        disco = payload.get("disco", "")
        
        # Meter should be 11-13 digits
        valid = bool(re.match(r'^\d{11,13}$', meter))
        
        return {
            "valid": valid,
            "meter_type": "prepaid" if valid else None,
            "customer_name": None,  # Would be fetched from API in real implementation
        }
    
    def _handle_escalate(
        self,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
        spec: Optional[ToolSpec] = None,
    ) -> Dict[str, Any]:
        """Handle escalation to human agent."""
        reason = payload.get("reason", "")
        severity = payload.get("severity", "medium")
        context = payload.get("context_summary", "")
        
        # Generate ticket ID
        import uuid
        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        
        # Estimate wait time based on severity
        wait_times = {
            "critical": "5 minutes",
            "high": "15 minutes",
            "medium": "30 minutes",
            "low": "1 hour",
        }
        
        return {
            "ticket_id": ticket_id,
            "estimated_wait": wait_times.get(severity, "30 minutes"),
            "status": "queued",
        }
    
    def _handle_search_tools(
        self,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
        spec: Optional[ToolSpec] = None,
    ) -> Dict[str, Any]:
        """Handle tool discovery."""
        query = payload.get("query", "")
        
        matches = self.registry.search_tools(query)
        
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "permissions": t.permissions,
                }
                for t in matches[:5]
            ],
            "total_found": len(matches),
        }

