"""
Run metadata and artifact versioning utilities.

Implements the core pieces from Phase 0 of the next-level plan:
- PromptBundle abstraction
- Hash-based versions for prompts, tenant config, and toolsets
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _sha256_of_text(text: str) -> str:
    encoded = text.encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PromptBundle:
    """
    Immutable description of a prompt bundle.

    The hash is derived from the effective template content and key
    configuration inputs so that changes are traceable and runs can be
    replayed by pinning a bundle hash.
    """

    name: str
    version: str
    template_id: str
    extras: Optional[Dict[str, Any]] = None

    @property
    def hash(self) -> str:
        payload = {
            "name": self.name,
            "version": self.version,
            "template_id": self.template_id,
            "extras": self.extras or {},
        }
        return _sha256_of_text(json.dumps(payload, sort_keys=True))


def compute_tenant_config_version(config: Dict[str, Any]) -> str:
    """
    Compute a deterministic version string for a tenant configuration.
    """
    normalized = json.dumps(config or {}, sort_keys=True, separators=(",", ":"))
    return _sha256_of_text(normalized)


def compute_toolset_version(tool_specs: Dict[str, Any]) -> str:
    """
    Compute a deterministic version string for the active tool registry.
    """
    normalized = json.dumps(tool_specs or {}, sort_keys=True, separators=(",", ":"))
    return _sha256_of_text(normalized)


@dataclass
class RunMetadata:
    """
    Minimal run-level metadata to attach to traces and results.

    This is the common contract used by tracing, evals, and dashboards.
    """

    tenant_id: str
    conversation_id: str
    model_id: str
    prompt_bundle_hash: str
    config_version: str
    toolset_version: str

