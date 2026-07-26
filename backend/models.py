"""
models.py — Pydantic models for all API request/response shapes.

Why Pydantic?
  FastAPI uses Pydantic to validate incoming JSON automatically.
  If a field is missing or the wrong type, FastAPI returns a clear
  422 error before your code ever runs — no manual validation needed.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ── Ingest (receiving spans from the swarm) ──────────────────────────────────

class SpanPayload(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    agent_name: str
    span_type: str          # 'AGENT_REASONING' | 'TOOL_EXECUTION' | 'HANDOFF'
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    latency_ms: int
    token_usage: dict[str, int] | None = None


class StateSnapshotPayload(BaseModel):
    trace_id: str
    span_id: str
    step_number: int
    agent_name: str
    state_data: dict[str, Any]


class IngestRequest(BaseModel):
    spans: list[SpanPayload]
    snapshots: list[StateSnapshotPayload] = []


# ── Traces (query responses) ──────────────────────────────────────────────────

class TraceListItem(BaseModel):
    trace_id: str
    root_agent: str
    status: str
    total_latency_ms: int | None
    parent_trace_id: str | None
    created_at: datetime


class SpanResponse(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None
    agent_name: str
    span_type: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    latency_ms: int
    token_usage: dict[str, Any] | None
    created_at: datetime
    children: list["SpanResponse"] = []   # nested tree built by the API


SpanResponse.model_rebuild()   # required for self-referential models


# ── Replay ────────────────────────────────────────────────────────────────────

class ReplayRequest(BaseModel):
    trace_id: str
    step_number: int                          # which snapshot to fork from
    overrides: dict[str, Any] = {}            # fields to inject into state_data
