"""
routers/ingest.py — POST /ingest

Receives a batch of OTel spans from the running swarm and stores them
in Neon Postgres. Also receives state_snapshots for time-travel replay.

B2: project_id stamped on every trace from API key.
B4: fire_alert() called when LOOP_DETECTED.
C4: broadcast_trace_update() and broadcast_span() push to WebSocket clients.
"""

import json

from alerting import fire_alert
from auth.dependencies import require_auth
from database import get_pool
from fastapi import APIRouter, Depends
from models import IngestRequest

from routers.ws import broadcast_span, broadcast_trace_update

_INPUT_COST_PER_M  = 0.59
_OUTPUT_COST_PER_M = 0.79


def _calculate_cost(token_usage: dict | None) -> float | None:
    if not token_usage:
        return None
    prompt     = token_usage.get("prompt_tokens", 0)
    completion = token_usage.get("completion_tokens", 0)
    cost = (prompt / 1_000_000 * _INPUT_COST_PER_M) + (
        completion / 1_000_000 * _OUTPUT_COST_PER_M
    )
    return round(cost, 6)


router = APIRouter()


@router.post("/ingest")
async def ingest(
    request: IngestRequest,
    user: dict = Depends(require_auth),  # noqa: B008
):
    pool = await get_pool()
    project_id = user.get("project_id")

    async with pool.acquire() as conn:
        for span in request.spans:
            root_agent = span.agent_name if span.parent_span_id is None else "orchestrator"

            await conn.execute(
                """
                INSERT INTO traces (trace_id, project_id, root_agent, status)
                VALUES ($1, $2, $3, 'RUNNING')
                ON CONFLICT (trace_id) DO UPDATE
                    SET project_id = COALESCE(traces.project_id, EXCLUDED.project_id)
                """,
                span.trace_id,
                project_id,
                root_agent,
            )

            cost = _calculate_cost(span.token_usage)
            await conn.execute(
                """
                INSERT INTO spans (
                    span_id, trace_id, parent_span_id, agent_name,
                    span_type, input_payload, output_payload,
                    latency_ms, token_usage, estimated_cost_usd
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (span_id) DO NOTHING
                """,
                span.span_id,
                span.trace_id,
                span.parent_span_id,
                span.agent_name,
                span.span_type,
                json.dumps(span.input_payload),
                json.dumps(span.output_payload),
                span.latency_ms,
                json.dumps(span.token_usage) if span.token_usage else None,
                cost,
            )

            # C4: push to any open WebSocket connections
            await broadcast_trace_update(span.trace_id, "RUNNING", root_agent)
            await broadcast_span(span.trace_id, {
                "span_id":        span.span_id,
                "trace_id":       span.trace_id,
                "parent_span_id": span.parent_span_id,
                "agent_name":     span.agent_name,
                "span_type":      span.span_type,
                "input_payload":  span.input_payload,
                "output_payload": span.output_payload,
                "latency_ms":     span.latency_ms,
                "token_usage":    span.token_usage,
                "estimated_cost_usd": cost,
                "children":       [],
            })

            if span.span_type == "HANDOFF":
                sender   = span.input_payload.get("sender", "")
                receiver = span.input_payload.get("receiver", "")
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM spans
                    WHERE trace_id = $1
                      AND span_type = 'HANDOFF'
                      AND input_payload->>'sender' = $2
                      AND input_payload->>'receiver' = $3
                    """,
                    span.trace_id, sender, receiver,
                )

                if count > 4:
                    await conn.execute(
                        "UPDATE traces SET status = 'LOOP_DETECTED' WHERE trace_id = $1",
                        span.trace_id,
                    )
                    await broadcast_trace_update(span.trace_id, "LOOP_DETECTED", root_agent)
                    await fire_alert(span.trace_id, "LOOP_DETECTED", project_id)

        for snap in request.snapshots:
            await conn.execute(
                """
                INSERT INTO state_snapshots
                    (trace_id, span_id, step_number, agent_name, state_data)
                VALUES ($1, $2, $3, $4, $5)
                """,
                snap.trace_id,
                snap.span_id,
                snap.step_number,
                snap.agent_name,
                json.dumps(snap.state_data),
            )

    return {"status": "ok", "spans_ingested": len(request.spans)}