"""
Accounts and sessions.

Real auth this time: bcrypt-hashed passwords, signed JWTs, and reports owned by
a user. The frontend's localStorage "session" gated navigation only; this gates
data.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.base import get_session
from app.db.models import User
from app.utils.errors import (
    AccountDisabledError, EmailTakenError, InvalidCredentialsError,
    InvalidTokenError, UnauthenticatedError,
)
from app.utils.security import create_token, decode_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


# ----------------------------------------------------------------- schemas --
class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    city: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    city: str | None
    role: str

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_hours: int
    user: UserOut


class ProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=120)


# -------------------------------------------------------------- dependency --
async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthenticatedError()

    payload = decode_token(authorization.split(" ", 1)[1].strip(), settings.jwt_secret)
    if not payload:
        # Covers expired, tampered and wrong-secret alike. Saying which would
        # tell an attacker something they should not learn.
        raise InvalidTokenError()

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise InvalidTokenError("Your session is not valid.")

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("This account is no longer active.")
    return user


# ------------------------------------------------------------------ routes --
@router.post("/auth/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    email = body.email.lower().strip()
    existing = await session.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise EmailTakenError()

    user = User(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        city=(body.city or None),
    )
    session.add(user)
    await session.flush()

    token = create_token(subject=str(user.id), secret=settings.jwt_secret,
                         expires_hours=settings.jwt_expires_hours, role=user.role)
    return TokenOut(access_token=token, expires_hours=settings.jwt_expires_hours,
                    user=UserOut.model_validate(user))


@router.post("/auth/login", response_model=TokenOut)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    email = body.email.lower().strip()
    user = await session.scalar(select(User).where(func.lower(User.email) == email))

    # One message for "no such user" and "wrong password" — distinguishing them
    # turns the login form into an account-enumeration oracle.
    if user is None or not verify_password(body.password, user.password_hash):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise AccountDisabledError()

    token = create_token(subject=str(user.id), secret=settings.jwt_secret,
                         expires_hours=settings.jwt_expires_hours, role=user.role)
    return TokenOut(access_token=token, expires_hours=settings.jwt_expires_hours,
                    user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return UserOut.model_validate(user)


@router.patch("/auth/me", response_model=UserOut)
async def update_me(
    body: ProfilePatch,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if body.name is not None:
        user.name = body.name.strip()
    if body.city is not None:
        user.city = body.city or None
    session.add(user)
    return UserOut.model_validate(user)
