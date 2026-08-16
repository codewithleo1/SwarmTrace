"""
routers/audit.py — Audit log system (ISO 27001 / SOC 2).

Provides:
  log_action()  — fire-and-forget helper called by other routers
  GET /audit/{project_id} — query audit log for a project (admin only)

Why a separate table instead of application logs?
  Application logs (stdout/stderr) are ephemeral — they disappear when
  the container restarts. The audit table persists in Postgres, is
  queryable with filters, and can be exported for compliance reports.

Why fire-and-forget?
  Audit logging must never block or fail the original user action.
  If the DB write fails (network blip, pool exhaustion), we log the
  error to stderr and move on. The user's action still completes.

Table structure:
  audit_logs(
    log_id        UUID PK,
    project_id    UUID  — which project this action happened in
    user_id       UUID  — who did it
    user_email    TEXT  — denormalised for fast display without JOIN
    action        TEXT  — e.g. 'MEMBER_INVITED', 'TRACE_REPLAY'
    resource_type TEXT  — e.g. 'trace', 'member', 'api_key'
    resource_id   TEXT  — the ID of the affected resource
    metadata      JSONB — extra context (old role, new role, etc.)
    created_at    TIMESTAMP
  )
"""

import json
import logging
import uuid

from auth.dependencies import require_role
from database import get_pool
from fastapi import APIRouter, Depends

logger = logging.getLogger("swarmtrace.audit")

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Schema migration (called from apply_schema via startup) ───────────────────

CREATE_AUDIT_TABLE = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id    UUID        REFERENCES projects(project_id) ON DELETE CASCADE,
        user_id       UUID,
        user_email    TEXT,
        action        TEXT        NOT NULL,
        resource_type TEXT,
        resource_id   TEXT,
        metadata      JSONB,
        created_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_logs (project_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_audit_user    ON audit_logs (user_id, created_at DESC);
"""


async def ensure_audit_table() -> None:
    """Create the audit_logs table if it doesn't exist. Called at startup."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_AUDIT_TABLE)


# ── Log helper ────────────────────────────────────────────────────────────────

async def log_action(
    *,
    project_id: str | None,
    user_id: str,
    user_email: str,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Write one audit log entry. Fire-and-forget — never raises.

    Call this from any router after a significant action:

        await log_action(
            project_id=project_id,
            user_id=user["user_id"],
            user_email=user["email"],
            action="MEMBER_INVITED",
            resource_type="member",
            resource_id=member_id,
            metadata={"email": body.email, "role": body.role},
        )

    Args:
        project_id:    UUID of the project context (None for global actions)
        user_id:       UUID of the acting user
        user_email:    Email of the acting user (denormalised for display)
        action:        Short uppercase string — e.g. "MEMBER_INVITED"
        resource_type: What was affected — "trace" | "member" | "api_key" | "project"
        resource_id:   ID of the affected resource
        metadata:      Any extra context (old/new values, counts, etc.)
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_logs
                    (log_id, project_id, user_id, user_email,
                     action, resource_type, resource_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                str(uuid.uuid4()),
                project_id,
                user_id,
                user_email,
                action,
                resource_type,
                resource_id,
                json.dumps(metadata) if metadata else None,
            )
    except Exception as exc:  # noqa: BLE001
        # Never block the caller — just warn
        logger.warning("Audit log write failed for action=%s: %s", action, exc)


# ── Query endpoint ────────────────────────────────────────────────────────────

@router.get("/{project_id}")
async def get_audit_log(
    project_id: str,
    limit: int = 100,
    action: str | None = None,
    user_id: str | None = None,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """
    Return the audit log for a project. Admin only.

    Query params:
      limit:   max rows to return (default 100, max 500)
      action:  filter by action type e.g. MEMBER_INVITED
      user_id: filter by acting user
    """
    limit = min(limit, 500)

    conditions = ["project_id = $1"]
    params: list = [project_id]
    idx = 2

    if action:
        conditions.append(f"action = ${idx}")
        params.append(action)
        idx += 1

    if user_id:
        conditions.append(f"user_id = ${idx}")
        params.append(user_id)
        idx += 1

    conditions.append(f"TRUE LIMIT ${idx}")
    params.append(limit)

    where = " AND ".join(conditions)

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT log_id, user_email, action, resource_type,
                   resource_id, metadata, created_at
            FROM audit_logs
            WHERE {where}
            ORDER BY created_at DESC
        """, *params)

    return [
        {
            "log_id":        str(row["log_id"]),
            "user_email":    row["user_email"],
            "action":        row["action"],
            "resource_type": row["resource_type"],
            "resource_id":   row["resource_id"],
            "metadata":      row["metadata"],
            "created_at":    row["created_at"],
        }
        for row in rows
    ]