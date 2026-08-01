"""
routers/auth.py — Auth endpoints.

POST /auth/register  — create account
POST /auth/login     — get JWT
GET  /auth/me        — get current user info
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from auth.dependencies import get_current_user
from auth.utils import create_access_token, hash_password, verify_password
from database import get_pool

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    """Create a new user account and return a JWT."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE email = $1", body.email
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user_id = str(uuid.uuid4())
        hashed  = hash_password(body.password)

        await conn.execute("""
            INSERT INTO users (user_id, email, name, password_hash)
            VALUES ($1, $2, $3, $4)
        """, user_id, body.email, body.name, hashed)

    token = create_access_token(user_id, body.email)
    return AuthResponse(
        access_token=token,
        user_id=user_id,
        email=body.email,
        name=body.name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Verify credentials and return a JWT."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, email, name, password_hash FROM users WHERE email = $1",
            body.email,
        )

    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(row["user_id"]), row["email"])
    return AuthResponse(
        access_token=token,
        user_id=str(row["user_id"]),
        email=row["email"],
        name=row["name"],
    )


@router.get("/me")
async def me(
    user: dict = Depends(get_current_user)  # noqa: B008
    ):
    """Return the current user's profile."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, email, name, created_at FROM users WHERE user_id = $1",
            user["user_id"],
        )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)