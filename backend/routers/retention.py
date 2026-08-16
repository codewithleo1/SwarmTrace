"""
routers/retention.py — Data retention controls (GDPR / SOC 2).

Endpoints:
  GET    /retention/{project_id}         — get current policy
  PUT    /retention/{project_id}         — set max_days (admin only)
  DELETE /retention/{project_id}/purge   — immediately purge old traces (admin only)

Background task:
  purge_all_projects() — called at startup, deletes traces beyond each
                         project's retention policy. Run daily on Render
                         via the keep-alive cron or a separate scheduler.

Why delete in a specific order?
  Postgres enforces foreign key constraints. If you try to delete a trace
  that still has spans referencing it, you get a FK violation error.
  Correct deletion order: evaluations → state_snapshots → spans → traces.
  Each child table must be cleared before its parent.

Why NUMERIC(4) for max_days?
  Retention policies are typically 30, 60, 90, 180, or 365 days.
  NUMERIC(4) handles up to 9999 days (~27 years) — more than enough.
"""

import logging
from datetime import UTC, datetime

from auth.dependencies import require_role
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routers.audit import log_action

logger = logging.getLogger("swarmtrace.retention")

router = APIRouter(prefix="/retention", tags=["retention"])

# Minimum allowed retention — prevents accidental mass deletion
_MIN_DAYS = 7


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_RETENTION_TABLE = """
    CREATE TABLE IF NOT EXISTS retention_policies (
        policy_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id  UUID        UNIQUE REFERENCES projects(project_id) ON DELETE CASCADE,
        max_days    INT         NOT NULL DEFAULT 90,
        created_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
    );
"""


async def ensure_retention_table() -> None:
    """Create retention_policies table if it doesn't exist. Called at startup."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_RETENTION_TABLE)


# ── Purge logic ───────────────────────────────────────────────────────────────

async def _purge_project(conn, project_id: str, max_days: int) -> int:
    """
    Delete all traces (and their children) older than max_days for one project.
    Returns the number of traces deleted.

    Deletion order (FK constraint safe):
      1. evaluations   (references spans)
      2. state_snapshots (references spans + traces)
      3. spans         (references traces)
      4. traces        (root table)
    """
    cutoff = f"NOW() - INTERVAL '{max_days} days'"

    # Find trace_ids to delete first (used for child table deletes)
    old_trace_ids = await conn.fetch(f"""
        SELECT trace_id FROM traces
        WHERE project_id = $1 AND created_at < {cutoff}
    """, project_id)

    if not old_trace_ids:
        return 0

    ids = [row["trace_id"] for row in old_trace_ids]

    # Delete in FK-safe order
    await conn.execute("""
        DELETE FROM evaluations WHERE trace_id = ANY($1::text[])
    """, ids)

    await conn.execute("""
        DELETE FROM state_snapshots WHERE trace_id = ANY($1::text[])
    """, ids)

    await conn.execute("""
        DELETE FROM spans WHERE trace_id = ANY($1::text[])
    """, ids)

    result = await conn.execute("""
        DELETE FROM traces WHERE trace_id = ANY($1::text[])
    """, ids)

    # asyncpg returns "DELETE N" as a string
    deleted = int(result.split()[-1]) if result else 0
    return deleted


async def purge_all_projects() -> None:
    """
    Purge old traces for every project that has a retention policy.
    Called at startup — acts as a daily cleanup on Render free tier
    (which restarts the dyno every ~24h due to inactivity + cron pings).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        policies = await conn.fetch("""
            SELECT project_id, max_days FROM retention_policies
        """)

    if not policies:
        return

    total_deleted = 0
    for policy in policies:
        try:
            async with pool.acquire() as conn:
                deleted = await _purge_project(
                    conn,
                    str(policy["project_id"]),
                    policy["max_days"],
                )
            total_deleted += deleted
            if deleted:
                logger.info(
                    "Retention purge: project=%s max_days=%s deleted=%s traces",
                    policy["project_id"], policy["max_days"], deleted,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Retention purge failed for project %s: %s", policy["project_id"], exc)

    if total_deleted:
        logger.info("Retention purge complete — %s traces deleted total", total_deleted)


# ── Endpoints ─────────────────────────────────────────────────────────────────

class SetRetentionRequest(BaseModel):
    max_days: int = Field(..., ge=_MIN_DAYS, le=9999,
                          description=f"Delete traces older than this many days (min {_MIN_DAYS})")


@router.get("/{project_id}")
async def get_retention_policy(
    project_id: str,
    user: dict = Depends(require_role("project_id", "viewer")),  # noqa: B008
):
    """Get the retention policy for a project. Any member can view."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT policy_id, max_days, updated_at
            FROM retention_policies
            WHERE project_id = $1
        """, project_id)

    if not row:
        return {
            "project_id": project_id,
            "max_days":   None,
            "message":    "No retention policy set — traces are kept indefinitely",
        }

    return {
        "project_id": project_id,
        "max_days":   row["max_days"],
        "updated_at": row["updated_at"],
    }


@router.put("/{project_id}")
async def set_retention_policy(
    project_id: str,
    body: SetRetentionRequest,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """
    Set or update the retention policy for a project.
    Requires admin. Minimum 7 days to prevent accidental mass deletion.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO retention_policies (project_id, max_days)
            VALUES ($1, $2)
            ON CONFLICT (project_id) DO UPDATE
                SET max_days   = EXCLUDED.max_days,
                    updated_at = NOW()
        """, project_id, body.max_days)

    await log_action(
        project_id=project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="RETENTION_POLICY_SET",
        resource_type="project",
        resource_id=project_id,
        metadata={"max_days": body.max_days},
    )

    return {
        "project_id": project_id,
        "max_days":   body.max_days,
        "message":    f"Traces older than {body.max_days} days will be deleted on next purge",
    }


@router.delete("/{project_id}/purge")
async def purge_now(
    project_id: str,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """
    Immediately delete all traces older than the retention policy.
    Requires admin. Returns count of deleted traces.
    If no policy is set, returns 400 — must set a policy first.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        policy = await conn.fetchrow("""
            SELECT max_days FROM retention_policies WHERE project_id = $1
        """, project_id)

    if not policy:
        raise HTTPException(
            status_code=400,
            detail="No retention policy set. Use PUT /retention/{project_id} first.",
        )

    max_days = policy["max_days"]

    async with pool.acquire() as conn:
        deleted = await _purge_project(conn, project_id, max_days)

    await log_action(
        project_id=project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="RETENTION_PURGE",
        resource_type="project",
        resource_id=project_id,
        metadata={"max_days": max_days, "traces_deleted": deleted},
    )

    return {
        "project_id":     project_id,
        "max_days":       max_days,
        "traces_deleted": deleted,
        "purged_at":      datetime.now(UTC).isoformat(),
    }