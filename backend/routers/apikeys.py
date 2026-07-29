"""
routers/apikeys.py — API key management.

POST   /api-keys        — generate a new API key
GET    /api-keys        — list all keys for current user
DELETE /api-keys/{id}  — revoke a key

API keys start with swt_ for easy identification.
Example: swt_a1b2c3d4e5f6...
"""

import secrets
import uuid

from auth.dependencies import get_current_user
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    name: str  # e.g. "AEGIS production", "ACSA dev"


@router.post("")
async def create_api_key(
    body: CreateKeyRequest,
    user: dict = Depends(get_current_user),    # noqa: B008
):
    """Generate a new API key for the current user."""
    key_id    = str(uuid.uuid4())
    key_value = "swt_" + secrets.token_hex(32)  # swt_<64 hex chars>

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO api_keys (key_id, user_id, name, key_value)
            VALUES ($1, $2, $3, $4)
        """, key_id, user["user_id"], body.name, key_value)

    return {
        "key_id": key_id,
        "name": body.name,
        "key_value": key_value,  # Only returned once — user must copy it now
        "message": "Copy this key now — it will not be shown again",
    }


@router.get("")
async def list_api_keys(
    user: dict = Depends(get_current_user)      # noqa: B008
    ):
    """List all API keys for the current user (key values masked)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT key_id, name, is_active, last_used_at, created_at,
                   LEFT(key_value, 12) || '...' AS key_preview
            FROM api_keys
            WHERE user_id = $1
            ORDER BY created_at DESC
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
        result = await conn.execute("""
            UPDATE api_keys SET is_active = false
            WHERE key_id = $1 AND user_id = $2
        """, key_id, user["user_id"])

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Key not found")

    return {"status": "revoked", "key_id": key_id}