"""
auth/dependencies.py — FastAPI dependencies for auth and RBAC.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from auth.utils import decode_token
from database import get_pool

bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

_ROLE_LEVELS = {"viewer": 0, "developer": 1, "admin": 2}


# ── Auth dependencies ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),  # noqa: B008
) -> dict | None:
    """Validate JWT and return user dict, or None if no token provided."""
    if not credentials:
        return None  # ← was raising 401 here; now returns None so require_auth can try API key
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
    Raises 401 if key is provided but invalid.
    """
    if not api_key:
        return None

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT ak.user_id, ak.project_id, u.email
            FROM api_keys ak
            JOIN users u ON u.user_id = ak.user_id
            WHERE ak.key_value = $1 AND ak.is_active = true
        """, api_key)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE api_keys SET last_used_at = NOW() WHERE key_value = $1
        """, api_key)

    return {
        "user_id":    str(row["user_id"]),
        "email":      row["email"],
        "project_id": str(row["project_id"]) if row["project_id"] else None,
    }


async def require_auth(
    jwt_user: dict | None = Depends(get_current_user),       # noqa: B008
    api_key_user: dict | None = Depends(get_api_key_user),   # noqa: B008
) -> dict:
    """
    Accept either JWT or API key. Returns user dict.
    Raises 401 only if NEITHER is provided.
    """
    user = api_key_user or jwt_user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — provide Bearer token or X-API-Key",
        )
    return user


# ── RBAC dependencies (C1) ────────────────────────────────────────────────────

async def _get_member_role(project_id: str, user_id: str) -> str | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT role FROM project_members
            WHERE project_id = $1 AND user_id = $2
        """, project_id, user_id)
    return row["role"] if row else None


def require_role(project_id_param: str, min_role: str = "viewer"):
    async def _check(
        project_id: str,
        user: dict = Depends(get_current_user),  # noqa: B008
    ) -> dict:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        role = await _get_member_role(project_id, user["user_id"])

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this project",
            )

        required_level = _ROLE_LEVELS.get(min_role, 0)
        actual_level   = _ROLE_LEVELS.get(role, -1)

        if actual_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {min_role} role (you have {role})",
            )

        return {**user, "role": role, "project_id": project_id}

    return _check


def require_admin(project_id: str = "project_id"):
    return require_role(project_id, "admin")


def require_developer(project_id: str = "project_id"):
    return require_role(project_id, "developer")


def require_viewer(project_id: str = "project_id"):
    return require_role(project_id, "viewer")