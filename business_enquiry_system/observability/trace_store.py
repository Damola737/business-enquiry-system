"""
Simple JSONL-based TraceStore implementation.

Implements the TraceStore contract from Phase 1 of the next-level plan:
- start_run() -> run_id
- append_span()
- append_event()
- finish_run()
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .redaction import redact_dict
from .run_metadata import RunMetadata


@dataclass
class TraceSpan:
    span_id: str
    run_id: str
    name: str
    start_time: str
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TraceEvent:
    event_id: str
    run_id: str
    span_id: Optional[str]
    timestamp: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)


class TraceStore:
    """
    Minimal thread-safe JSONL trace store.

    Each line is a JSON object tagged with type: run/span/event.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        root = os.path.dirname(os.path.dirname(__file__))
        default_path = os.path.join(root, "logs", "traces.jsonl")
        self.path = path or default_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()

    def _write_record(self, record: Dict[str, Any]) -> None:
        sanitized = redact_dict(record)
        line = json.dumps(sanitized, ensure_ascii=False)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def start_run(self, metadata: RunMetadata, route: Optional[str] = None) -> str:
        run_id = str(uuid.uuid4())
        record = {
            "type": "run_start",
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "route": route,
            "metadata": asdict(metadata),
        }
        self._write_record(record)
        return run_id

    def append_span(
        self,
        run_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        span_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=span_id,
            run_id=run_id,
            name=name,
            start_time=(start_time or datetime.utcnow()).isoformat() + "Z",
            end_time=(end_time or datetime.utcnow()).isoformat() + "Z",
            metadata=metadata or {},
            error=error,
        )
        record = {"type": "span", **asdict(span)}
        self._write_record(record)
        return span_id

    def append_event(
        self,
        run_id: str,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
        span_id: Optional[str] = None,
    ) -> str:
        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            span_id=span_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            kind=kind,
            payload=payload or {},
        )
        record = {"type": "event", **asdict(event)}
        self._write_record(record)
        return event.event_id

    def finish_run(
        self,
        run_id: str,
        status: str,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "type": "run_end",
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "summary": summary or {},
        }
        self._write_record(record)

