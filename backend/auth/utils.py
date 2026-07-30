"""
auth/utils.py — Password hashing and JWT creation/verification.

Why bcrypt?
  Industry standard for password hashing. Slow by design — makes
  brute-force attacks impractical.

Why JWT?
  Stateless — no session store needed. The token itself carries the
  user identity. Backend verifies signature on every request.
"""

import os
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT containing user_id and email."""
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT. Raises JWTError if invalid or expired.
    Returns the payload dict.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])