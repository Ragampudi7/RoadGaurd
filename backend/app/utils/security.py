"""Password hashing and JWT issue/verify."""

from __future__ import annotations

import datetime as dt
from typing import Any

import bcrypt
import jwt

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    # bcrypt silently truncates at 72 bytes; reject rather than accept a
    # password whose tail is ignored.
    raw = plain.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("Password must be 72 bytes or fewer.")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(*, subject: str, secret: str, expires_hours: int = 72, **claims: Any) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + dt.timedelta(hours=expires_hours),
        **claims,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
