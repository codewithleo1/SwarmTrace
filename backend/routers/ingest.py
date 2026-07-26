"""
routers/ingest.py — POST /ingest

Receives a batch of OTel spans from the running swarm and stores them
in Neon Postgres. Also receives state_snapshots for time-travel replay.

Why batch ingest?
  Sending one HTTP request per span would be slow. Batching all spans
  from one agent step into a single POST reduces network overhead.
"""

import json

from database import get_pool
from fastapi import APIRouter
from models import IngestRequest

router = APIRouter()


@router.post("/ingest")
async def ingest(request: IngestRequest):
    pool = await get_pool()

    async with pool.acquire() as conn:
        for span in request.spans:
            # Upsert the parent trace row if it doesn't exist yet
            await conn.execute("""
                INSERT INTO traces (trace_id, root_agent, status)
                VALUES ($1, $2, 'RUNNING')
                ON CONFLICT (trace_id) DO NOTHING
            """, span.trace_id, span.agent_name if span.parent_span_id is None else "orchestrator")

            # Insert the span
            await conn.execute("""
                INSERT INTO spans (
                    span_id, trace_id, parent_span_id, agent_name,
                    span_type, input_payload, output_payload,
                    latency_ms, token_usage
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
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
            )

            # Loop detection — if same sender→receiver pair appears >4 times, flag it
            if span.span_type == "HANDOFF":
                sender = span.input_payload.get("sender", "")
                receiver = span.input_payload.get("receiver", "")
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM spans
                    WHERE trace_id = $1
                      AND span_type = 'HANDOFF'
                      AND input_payload->>'sender' = $2
                      AND input_payload->>'receiver' = $3
                """, span.trace_id, sender, receiver)

                if count > 4:
                    await conn.execute("""
                        UPDATE traces SET status = 'LOOP_DETECTED'
                        WHERE trace_id = $1
                    """, span.trace_id)

        # Store state snapshots
        for snap in request.snapshots:
            await conn.execute("""
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
