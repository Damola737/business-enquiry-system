"""
PII redaction utilities for logs and traces.

Implements Phase 1: PII redaction rules applied before persisting traces.
"""

from __future__ import annotations

import re
from typing import Any, Dict


PHONE_PATTERN = re.compile(r"(\+?234|0)[789]\d{9}")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
METER_PATTERN = re.compile(r"\b\d{11,13}\b")


def redact_text(text: str) -> str:
    """
    Best-effort redaction for common PII in Nigerian telecom/utility contexts.
    """
    if not text:
        return text

    redacted = PHONE_PATTERN.sub("***PHONE***", text)
    redacted = EMAIL_PATTERN.sub("***EMAIL***", redacted)
    redacted = METER_PATTERN.sub("***METER***", redacted)
    return redacted


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply redaction recursively to a dictionary.
    """
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = redact_text(value)
        elif isinstance(value, dict):
            sanitized[key] = redact_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                redact_text(item) if isinstance(item, str) else item for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized

