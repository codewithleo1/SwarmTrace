"""
routers/traces.py — GET /traces and GET /trace/{trace_id}

GET /traces      → flat list of all traces (for the trace list page)
GET /trace/{id}  → full nested span tree for one trace (for the detail page)

Why build a tree in Python instead of SQL?
  Recursive CTEs in SQL can do this, but they're hard to read and maintain.
  Since trace sizes are small (<100 spans), it's cleaner to fetch all spans
  flat and build the parent-child tree in Python.

B2: /traces now accepts project_id query param to scope results to a project.
"""

import json

from alerting import fire_alert
from database import get_pool
from fastapi import APIRouter, HTTPException
from models import TraceListItem

router = APIRouter()


@router.get("/traces", response_model=list[TraceListItem])
async def list_traces(
    project_id: str | None = None,
    status: str | None = None,
    root_agent: str | None = None,
    search: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    pool = await get_pool()

    conditions = []
    params = []
    idx = 1

    if project_id:
        conditions.append(f"project_id = ${idx}")
        params.append(project_id)
        idx += 1

    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    if root_agent:
        conditions.append(f"root_agent ILIKE ${idx}")
        params.append(f"%{root_agent}%")
        idx += 1

    if search:
        conditions.append(f"trace_id ILIKE ${idx}")
        params.append(f"%{search}%")
        idx += 1

    if from_date:
        conditions.append(f"created_at >= ${idx}")
        params.append(from_date)
        idx += 1

    if to_date:
        conditions.append(f"created_at <= ${idx}")
        params.append(to_date)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT trace_id, root_agent, status, total_latency_ms,
                   total_cost_usd, parent_trace_id, created_at
            FROM traces
            {where}
            ORDER BY created_at DESC
            LIMIT 100
            """,
            *params,
        )

    return [dict(row) for row in rows]


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        trace = await conn.fetchrow("""
            SELECT * FROM traces WHERE trace_id = $1
        """, trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        span_rows = await conn.fetch("""
            SELECT * FROM spans WHERE trace_id = $1 ORDER BY created_at ASC
        """, trace_id)

    # Build nested tree in Python
    span_map: dict[str, dict] = {}
    for row in span_rows:
        s = dict(row)
        s["input_payload"] = (
            json.loads(s["input_payload"])
            if isinstance(s["input_payload"], str)
            else s["input_payload"]
        )
        s["output_payload"] = (
            json.loads(s["output_payload"])
            if isinstance(s["output_payload"], str)
            else s["output_payload"]
        )
        s["token_usage"] = (
            json.loads(s["token_usage"])
            if isinstance(s.get("token_usage"), str)
            else s.get("token_usage")
        )
        s["children"] = []
        span_map[s["span_id"]] = s

    roots = []
    for s in span_map.values():
        parent_id = s.get("parent_span_id")
        if parent_id and parent_id in span_map:
            span_map[parent_id]["children"].append(s)
        else:
            roots.append(s)

    return {
        "trace": dict(trace),
        "span_tree": roots,
    }



@router.patch("/traces/{trace_id}/complete")
async def complete_trace(trace_id: str, status: str = "SUCCESS"):
    """Mark a trace as complete and calculate total latency. Fires alert if FAILED."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE traces
            SET status = $2,
                total_latency_ms = (
                    SELECT COALESCE(SUM(latency_ms), 0)
                    FROM spans WHERE trace_id = $1
                ),
                total_cost_usd = (
                    SELECT COALESCE(SUM(estimated_cost_usd), 0)
                    FROM spans WHERE trace_id = $1
                )
            WHERE trace_id = $1
            """,
            trace_id, status,
        )
        # Fetch project_id for alert firing
        row = await conn.fetchrow(
            "SELECT project_id FROM traces WHERE trace_id = $1", trace_id
        )

    if status == "FAILED" and row:
        await fire_alert(trace_id, "FAILED", str(row["project_id"]) if row["project_id"] else None)

    return {"status": "ok"}


@router.get("/metrics")
async def get_metrics(project_id: str | None = None):
    """
    Returns aggregate metrics for the dashboard.
    Optionally scoped to a project.
    """
    pool = await get_pool()

    where = "WHERE project_id = $1" if project_id else ""
    date_filter = (
        "AND created_at >= NOW() - INTERVAL '7 days'"
        if project_id
        else "WHERE created_at >= NOW() - INTERVAL '7 days'"
    )
    params = [project_id] if project_id else []

    async with pool.acquire() as conn:
        summary = await conn.fetchrow(
            f"""
            SELECT
                COUNT(*)                                            AS total_traces,
                COUNT(*) FILTER (WHERE status = 'SUCCESS')         AS successful,
                COUNT(*) FILTER (WHERE status = 'FAILED')          AS failed,
                COUNT(*) FILTER (WHERE status = 'LOOP_DETECTED')   AS loops,
                COUNT(*) FILTER (WHERE status = 'RUNNING')         AS running,
                ROUND(AVG(total_latency_ms))                       AS avg_latency_ms,
                ROUND(CAST(SUM(total_cost_usd) AS NUMERIC), 6)     AS total_cost_usd,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE status = 'SUCCESS')
                    / NULLIF(COUNT(*), 0), 1
                )                                                   AS success_rate
            FROM traces
            {where}
            """,
            *params,
        )

        daily = await conn.fetch(
            f"""
            SELECT
                DATE(created_at) AS day,
                COUNT(*)         AS count
            FROM traces
            {where}
            {date_filter}
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """,
            *params,
        )

    return {
        "summary": dict(summary),
        "daily":   [dict(r) for r in daily],
    }