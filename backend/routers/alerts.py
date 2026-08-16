"""
routers/alerts.py — Webhook alert configuration.

POST   /alerts                  — create or update webhook config for a project
GET    /alerts/{project_id}     — get current alert config for a project
DELETE /alerts/{project_id}     — remove alert config

B4: When a trace status becomes FAILED or LOOP_DETECTED, SwarmTrace fires
    an HTTP POST to the configured webhook URL with trace details.
    The fire_alert() function is called from ingest.py — not from here.
"""

from auth.dependencies import get_current_user
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertConfigRequest(BaseModel):
    project_id: str
    webhook_url: str
    on_failed: bool = True
    on_loop: bool = True


@router.post("")
async def upsert_alert_config(
    body: AlertConfigRequest,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Create or update the webhook config for a project."""
    pool = await get_pool()

    # Verify project belongs to this user
    async with pool.acquire() as conn:
        project = await conn.fetchrow("""
            SELECT project_id FROM projects
            WHERE project_id = $1 AND user_id = $2
        """, body.project_id, user["user_id"])

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO alert_configs (project_id, webhook_url, on_failed, on_loop)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (project_id) DO UPDATE
                SET webhook_url = EXCLUDED.webhook_url,
                    on_failed   = EXCLUDED.on_failed,
                    on_loop     = EXCLUDED.on_loop,
                    updated_at  = NOW()
        """, body.project_id, body.webhook_url, body.on_failed, body.on_loop)

    return {
        "status": "ok",
        "project_id": body.project_id,
        "webhook_url": body.webhook_url,
        "on_failed": body.on_failed,
        "on_loop": body.on_loop,
    }


@router.get("/{project_id}")
async def get_alert_config(
    project_id: str,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Get the webhook config for a project."""
    pool = await get_pool()

    # Verify ownership
    async with pool.acquire() as conn:
        project = await conn.fetchrow("""
            SELECT project_id FROM projects
            WHERE project_id = $1 AND user_id = $2
        """, project_id, user["user_id"])

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT config_id, project_id, webhook_url, on_failed, on_loop, updated_at
            FROM alert_configs WHERE project_id = $1
        """, project_id)

    if not row:
        return None  # No config yet — frontend shows "not configured"

    return dict(row)


@router.delete("/{project_id}")
async def delete_alert_config(
    project_id: str,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Remove the webhook config for a project."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        project = await conn.fetchrow("""
            SELECT project_id FROM projects
            WHERE project_id = $1 AND user_id = $2
        """, project_id, user["user_id"])

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM alert_configs WHERE project_id = $1
        """, project_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="No alert config found")

    return {"status": "deleted", "project_id": project_id}