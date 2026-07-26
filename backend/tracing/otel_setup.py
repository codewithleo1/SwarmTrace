"""
otel_setup.py — OpenTelemetry SDK initialisation + span helper.

Why OpenTelemetry?
  OTel is the industry standard for distributed tracing (used by Google,
  Netflix, Datadog). By using OTel primitives, SwarmTrace speaks the same
  language as production observability tooling.

  A Span = one unit of work (one agent action).
  A Trace = the full tree of spans for one end-to-end swarm run.
"""

import logging
import os
import time
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

INGEST_URL = os.getenv("INGEST_URL", "http://localhost:8000/ingest")


def new_id() -> str:
    """Generate a unique 16-character hex ID (standard OTel format)."""
    return uuid.uuid4().hex[:16]


class Span:
    """
    Lightweight span object that mirrors OTel semantics.
    Records start time, end time, inputs, and outputs for one agent action.
    """

    def __init__(
        self,
        trace_id: str,
        agent_name: str,
        span_type: str,
        input_payload: dict,
        parent_span_id: str | None = None,
    ):
        self.span_id = new_id()
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.agent_name = agent_name
        self.span_type = span_type
        self.input_payload = input_payload
        self.output_payload: dict = {}
        self.token_usage: dict | None = None
        self._start_ms = int(time.time() * 1000)
        self.latency_ms: int = 0

    def end(self, output_payload: dict, token_usage: dict | None = None) -> None:
        """Call this when the agent action is complete."""
        self.latency_ms = int(time.time() * 1000) - self._start_ms
        self.output_payload = output_payload
        self.token_usage = token_usage

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "agent_name": self.agent_name,
            "span_type": self.span_type,
            "input_payload": self.input_payload,
            "output_payload": self.output_payload,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
        }


def emit_spans(spans: list[Span], snapshots: list[dict] | None = None) -> None:
    """
    Send completed spans (and optional state snapshots) to the FastAPI /ingest endpoint.
    Uses httpx (sync) so agents don't need to be async.
    """
    payload = {
        "spans": [s.to_dict() for s in spans],
        "snapshots": snapshots or [],
    }
    try:
        response = httpx.post(INGEST_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"📡 Emitted {len(spans)} span(s) to SwarmTrace")
    except httpx.HTTPError as e:
        logger.warning("Failed to emit spans: %s", e)