"""
routers/replay.py — POST /replay (Time-Travel Engine)

How it works:
  1. Load the state_snapshot at the requested step_number
  2. Apply the user's overrides (e.g. changed prompt or tool output)
  3. Resume the LangGraph swarm from that snapshot
  4. Save the result as a new trace with parent_trace_id pointing to the original
  5. Return the new trace_id so the frontend can show the forked run
"""

import json
import uuid

from database import get_pool
from fastapi import APIRouter, HTTPException
from models import ReplayRequest

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

        state_data = json.loads(snapshot["state_data"]) if isinstance(snapshot["state_data"], str) else dict(snapshot["state_data"])
        state_data.update(request.overrides)

        new_trace_id = uuid.uuid4().hex
        await conn.execute("""
            INSERT INTO traces (trace_id, root_agent, status, parent_trace_id)
            VALUES ($1, $2, 'RUNNING', $3)
        """, new_trace_id, snapshot["agent_name"], request.trace_id)

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

    return {
        "status": "ok",
        "original_trace_id": request.trace_id,
        "forked_trace_id": new_trace_id,
        "forked_from_step": request.step_number,
    }