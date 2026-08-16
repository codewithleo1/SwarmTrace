"""
routers/export.py — OTLP-compatible span export.

GET  /export/otlp/{trace_id}  — export one trace as OTLP JSON
GET  /export/otlp/{trace_id}/download — same but as a downloadable .json file

Why OTLP?
  OpenTelemetry Protocol is the industry standard for telemetry data.
  Jaeger, Datadog, Honeycomb, Grafana Tempo, and every major observability
  platform can ingest OTLP. By exporting in this format, SwarmTrace spans
  can flow into any existing observability stack — no vendor lock-in.

Why post-hoc export instead of real-time OTel SDK export?
  Real-time export works only for traces that are currently running.
  Post-hoc export works for any historical trace in the database — you can
  export a trace from 3 weeks ago to Jaeger without re-running the swarm.

OTLP JSON spec reference:
  https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding
"""

import json
import time
from datetime import UTC

from database import get_pool
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

router = APIRouter(prefix="/export", tags=["export"])


def _to_otlp_attributes(data: dict) -> list[dict]:
    """
    Convert a flat dict to OTLP attribute format.
    OTLP attributes are typed: { key, value: { stringValue | intValue | ... } }
    We store everything as JSON strings for simplicity.
    """
    attrs = []
    for key, val in data.items():
        if isinstance(val, bool):
            attrs.append({"key": key, "value": {"boolValue": val}})
        elif isinstance(val, int):
            attrs.append({"key": key, "value": {"intValue": str(val)}})
        elif isinstance(val, float):
            attrs.append({"key": key, "value": {"doubleValue": val}})
        elif isinstance(val, (dict, list)):
            attrs.append({"key": key, "value": {"stringValue": json.dumps(val)}})
        else:
            attrs.append({"key": key, "value": {"stringValue": str(val)}})
    return attrs


def _datetime_to_unix_nano(dt) -> str:
    """
    Convert a datetime object to Unix nanoseconds as a string.
    OTLP requires nanosecond timestamps as strings (int64 in proto).
    """
    if dt is None:
        return str(int(time.time() * 1_000_000_000))
    ts = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
    return str(int(ts.timestamp() * 1_000_000_000))


def _span_to_otlp(span: dict) -> dict:
    """
    Convert a SwarmTrace span row to OTLP span format.

    Key mappings:
      span_id        → spanId  (must be 16 hex chars = 8 bytes)
      trace_id       → traceId (must be 32 hex chars = 16 bytes)
      parent_span_id → parentSpanId
      agent_name     → name prefix
      created_at     → startTimeUnixNano
      created_at + latency_ms → endTimeUnixNano
      input/output payloads → attributes
    """
    # Normalise IDs to correct OTLP lengths
    # OTLP traceId = 32 hex chars (16 bytes)
    # OTLP spanId  = 16 hex chars (8 bytes)
    raw_trace_id = str(span.get("trace_id", "")).replace("-", "")
    raw_span_id  = str(span.get("span_id",  "")).replace("-", "")

    trace_id = raw_trace_id.ljust(32, "0")[:32]
    span_id  = raw_span_id.ljust(16,  "0")[:16]

    parent_span_id = span.get("parent_span_id")
    if parent_span_id:
        parent_span_id = str(parent_span_id).replace("-", "").ljust(16, "0")[:16]

    # Timestamps
    created_at    = span.get("created_at")
    start_nano    = _datetime_to_unix_nano(created_at)
    latency_ms    = span.get("latency_ms") or 0
    end_nano      = str(int(start_nano) + latency_ms * 1_000_000)

    # Build attributes from input/output payloads + metadata
    attributes = []

    input_payload = span.get("input_payload") or {}
    if isinstance(input_payload, str):
        input_payload = json.loads(input_payload)
    for k, v in input_payload.items():
        attributes.append({
            "key": f"input.{k}",
            "value": {"stringValue": json.dumps(v) if isinstance(v, (dict, list)) else str(v)},
        })

    output_payload = span.get("output_payload") or {}
    if isinstance(output_payload, str):
        output_payload = json.loads(output_payload)
    for k, v in output_payload.items():
        attributes.append({
            "key": f"output.{k}",
            "value": {"stringValue": json.dumps(v) if isinstance(v, (dict, list)) else str(v)},
        })

    # Add SwarmTrace-specific metadata as attributes
    attributes.extend(_to_otlp_attributes({
        "swarmtrace.agent_name":  span.get("agent_name", ""),
        "swarmtrace.span_type":   span.get("span_type", ""),
        "swarmtrace.latency_ms":  latency_ms,
    }))

    token_usage = span.get("token_usage")
    if token_usage:
        if isinstance(token_usage, str):
            token_usage = json.loads(token_usage)
        attributes.extend(_to_otlp_attributes({
            "swarmtrace.prompt_tokens":     token_usage.get("prompt_tokens", 0),
            "swarmtrace.completion_tokens": token_usage.get("completion_tokens", 0),
        }))

    cost = span.get("estimated_cost_usd")
    if cost is not None:
        attributes.append({
            "key":   "swarmtrace.estimated_cost_usd",
            "value": {"doubleValue": float(cost)},
        })

    otlp_span: dict = {
        "traceId":              trace_id,
        "spanId":               span_id,
        "name":                 f"{span.get('agent_name', 'unknown')}/{span.get('span_type', 'SPAN')}",
        "kind":                 3,          # SPAN_KIND_CLIENT — closest to agent calls
        "startTimeUnixNano":    start_nano,
        "endTimeUnixNano":      end_nano,
        "attributes":           attributes,
        "status":               {"code": 1},  # STATUS_CODE_OK
    }

    if parent_span_id:
        otlp_span["parentSpanId"] = parent_span_id

    return otlp_span


def _build_otlp_payload(trace: dict, spans: list[dict]) -> dict:
    """
    Wrap converted spans in a full OTLP ResourceSpans envelope.
    This is the top-level structure that OTLP collectors expect.
    """
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": _to_otlp_attributes({
                        "service.name":             "SwarmTrace",
                        "service.version":          "0.4.0",
                        "swarmtrace.trace_id":      trace.get("trace_id", ""),
                        "swarmtrace.root_agent":    trace.get("root_agent", ""),
                        "swarmtrace.status":        trace.get("status", ""),
                    }),
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name":    "swarmtrace",
                            "version": "0.4.0",
                        },
                        "spans": [_span_to_otlp(s) for s in spans],
                    }
                ],
            }
        ]
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/otlp/{trace_id}")
async def export_otlp(trace_id: str):
    """
    Export a trace as OTLP JSON.
    Compatible with Jaeger, Grafana Tempo, Honeycomb, and any OTLP collector.

    To forward to Jaeger:
        curl http://localhost:8000/export/otlp/{trace_id} | \\
        curl -X POST http://jaeger:4318/v1/traces -d @-
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        trace = await conn.fetchrow(
            "SELECT * FROM traces WHERE trace_id = $1", trace_id
        )
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        span_rows = await conn.fetch(
            "SELECT * FROM spans WHERE trace_id = $1 ORDER BY created_at ASC",
            trace_id,
        )

    trace_dict = dict(trace)
    spans      = [dict(row) for row in span_rows]
    payload    = _build_otlp_payload(trace_dict, spans)

    return JSONResponse(content=payload)


@router.get("/otlp/{trace_id}/download")
async def export_otlp_download(trace_id: str):
    """
    Same as /export/otlp/{trace_id} but returns a downloadable .json file.
    Useful for importing into tools that accept file uploads.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        trace = await conn.fetchrow(
            "SELECT * FROM traces WHERE trace_id = $1", trace_id
        )
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        span_rows = await conn.fetch(
            "SELECT * FROM spans WHERE trace_id = $1 ORDER BY created_at ASC",
            trace_id,
        )

    trace_dict = dict(trace)
    spans      = [dict(row) for row in span_rows]
    payload    = _build_otlp_payload(trace_dict, spans)

    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="trace-{trace_id[:12]}.otlp.json"'
        },
    )