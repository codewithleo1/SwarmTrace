"""
routers/apikeys.py — API key management.
C2: audit log calls added on create and revoke.
"""

import secrets
import uuid

from auth.dependencies import get_current_user
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.audit import log_action

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    name: str
    project_id: str


@router.post("")
async def create_api_key(
    body: CreateKeyRequest,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Generate a new API key scoped to a project."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        project = await conn.fetchrow("""
            SELECT project_id FROM projects
            WHERE project_id = $1 AND user_id = $2
        """, body.project_id, user["user_id"])

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    key_id    = str(uuid.uuid4())
    key_value = "swt_" + secrets.token_hex(32)

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO api_keys (key_id, user_id, project_id, name, key_value)
            VALUES ($1, $2, $3, $4, $5)
        """, key_id, user["user_id"], body.project_id, body.name, key_value)

    # C2: audit
    await log_action(
        project_id=body.project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="API_KEY_CREATED",
        resource_type="api_key",
        resource_id=key_id,
        metadata={"name": body.name},
    )

    return {
        "key_id":     key_id,
        "name":       body.name,
        "project_id": body.project_id,
        "key_value":  key_value,
        "message":    "Copy this key now — it will not be shown again",
    }


@router.get("")
async def list_api_keys(
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """List all API keys for the current user, with project name."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT ak.key_id, ak.name, ak.is_active, ak.last_used_at, ak.created_at,
                   LEFT(ak.key_value, 12) || '...' AS key_preview,
                   ak.project_id,
                   p.name AS project_name
            FROM api_keys ak
            LEFT JOIN projects p ON p.project_id = ak.project_id
            WHERE ak.user_id = $1
            ORDER BY ak.created_at DESC
        """, user["user_id"])
    return [dict(row) for row in rows]


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Revoke (deactivate) an API key."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Fetch key info before revoking so we can log it
        key_row = await conn.fetchrow("""
            SELECT project_id, name FROM api_keys
            WHERE key_id = $1 AND user_id = $2
        """, key_id, user["user_id"])

        result = await conn.execute("""
            UPDATE api_keys SET is_active = false
            WHERE key_id = $1 AND user_id = $2
        """, key_id, user["user_id"])

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Key not found")

    # C2: audit
    await log_action(
        project_id=str(key_row["project_id"]) if key_row and key_row["project_id"] else None,
        user_id=user["user_id"],
        user_email=user["email"],
        action="API_KEY_REVOKED",
        resource_type="api_key",
        resource_id=key_id,
        metadata={"name": key_row["name"] if key_row else None},
    )

    return {"status": "revoked", "key_id": key_id}