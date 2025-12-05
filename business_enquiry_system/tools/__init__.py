"""
Tool specifications, registry, and execution.

Implements Phase 4 & 7:
- ToolSpec: Tool definition schema
- ToolRegistry: Tool discovery and search
- ToolRunner: Execution with budgets, retries, sandboxing
- ToolError: Standardized error taxonomy
"""

from tools.specs import (
    ToolSpec,
    ToolBudget,
    ToolResult,
    ToolError,
    ToolRegistry,
    create_tool_error,
    build_default_registry,
)

from tools.runner import (
    ToolRunner,
    ToolExecutionError,
)

__all__ = [
    # Specs
    "ToolSpec",
    "ToolBudget",
    "ToolResult",
    "ToolError",
    "ToolRegistry",
    "create_tool_error",
    "build_default_registry",
    # Runner
    "ToolRunner",
    "ToolExecutionError",
]

