"""
auth/dependencies.py — FastAPI dependencies for auth.

Two dependency functions:
  - get_current_user: validates JWT from Authorization header
  - get_api_key_user: validates X-API-Key header for agent systems

Why two?
  Humans use JWT (short-lived, browser-friendly).
  Agent systems use API keys (static, easy to put in .env).
  Both return a user_id so downstream code doesn't care which was used.
"""

from database import get_pool
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from auth.utils import decode_token

bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),  # noqa: B008
) -> dict:
    """Validate JWT and return user dict. Raises 401 if invalid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — provide Bearer token or X-API-Key",
        )
    try:
        payload = decode_token(credentials.credentials)
        return {"user_id": payload["sub"], "email": payload["email"]}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_api_key_user(
    api_key: str = Security(api_key_scheme),
) -> dict | None:
    """
    Validate X-API-Key header against the api_keys table.
    Returns user dict if valid, None if header not present.
    Raises 401 if key is invalid.
    """
    if not api_key:
        return None

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT ak.user_id, u.email
            FROM api_keys ak
            JOIN users u ON u.user_id = ak.user_id
            WHERE ak.key_value = $1 AND ak.is_active = true
        """, api_key)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Update last_used_at
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE api_keys SET last_used_at = NOW() WHERE key_value = $1
        """, api_key)

    return {"user_id": str(row["user_id"]), "email": row["email"]}


async def require_auth(
    jwt_user: dict = Depends(get_current_user),  # noqa: B008
    api_key_user: dict | None = Depends(get_api_key_user),  # noqa: B008
) -> dict:
    """
    Accept either JWT or API key. Returns user dict.
    Used on /ingest so agent systems can send spans without JWT.
    """
    return api_key_user or jwt_user