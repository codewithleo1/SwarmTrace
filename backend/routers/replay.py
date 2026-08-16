"""
routers/replay.py — POST /replay (Time-Travel Engine)
C2: audit log call added after successful fork.
"""

import json
import uuid

from database import get_pool
from fastapi import APIRouter, HTTPException
from models import ReplayRequest

from routers.audit import log_action

router = APIRouter()


@router.post("/replay")
async def replay(request: ReplayRequest):
    pool = await get_pool()

    async with pool.acquire() as conn:
        snapshot = await conn.fetchrow("""
            SELECT * FROM state_snapshots
            WHERE trace_id = $1 AND step_number = $2
        """, request.trace_id, request.step_number)

        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"No snapshot found at step {request.step_number} for trace {request.trace_id}",
            )

        state_data = (
            json.loads(snapshot["state_data"])
            if isinstance(snapshot["state_data"], str)
            else dict(snapshot["state_data"])
        )
        state_data.update(request.overrides)

        new_trace_id = uuid.uuid4().hex

        await conn.execute("""
            INSERT INTO traces (trace_id, root_agent, status, parent_trace_id)
            VALUES ($1, $2, 'RUNNING', $3)
        """, new_trace_id, snapshot["agent_name"], request.trace_id)

    # Fetch project_id separately — safe against missing key in mock/real row
    project_id = None
    try:
        async with pool.acquire() as conn:
            orig_trace = await conn.fetchrow(
                "SELECT project_id FROM traces WHERE trace_id = $1", request.trace_id
            )
        if orig_trace:
            raw = orig_trace.get("project_id") if hasattr(orig_trace, "get") else orig_trace["project_id"]
            project_id = str(raw) if raw else None
    except Exception:  # noqa: BLE001
        pass  # audit log is best-effort — don't block the replay

    from agents.orchestrator import resume_from_snapshot

    try:
        await resume_from_snapshot(
            new_trace_id=new_trace_id,
            state_data=state_data,
            from_step=request.step_number,
        )
    except Exception as e:
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE traces SET status = 'FAILED' WHERE trace_id = $1
            """, new_trace_id)
        raise HTTPException(status_code=500, detail=f"Replay failed: {e}") from e

    # C2: audit — best-effort
    await log_action(
        project_id=project_id,
        user_id="system",
        user_email="replay@swarmtrace",
        action="TRACE_REPLAY",
        resource_type="trace",
        resource_id=new_trace_id,
        metadata={
            "original_trace_id": request.trace_id,
            "step_number":       request.step_number,
            "overrides_keys":    list(request.overrides.keys()),
        },
    )

    return {
        "status":            "ok",
        "original_trace_id": request.trace_id,
        "forked_trace_id":   new_trace_id,
        "forked_from_step":  request.step_number,
    }