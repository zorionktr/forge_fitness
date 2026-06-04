"""Auth routes (docs/10 §2). Email + (OAuth stubs)."""
from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbDep
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import Profile, User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UsernameAvailability,
)

router = APIRouter()

# Mirror RegisterRequest's username rule (3–30 chars, letters/digits/underscore).
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


@router.get("/username-available", response_model=UsernameAvailability)
async def username_available(
    db: DbDep,
    username: Annotated[str, Query(min_length=1, max_length=30)],
) -> UsernameAvailability:
    """Live availability check for the sign-up form. Validates format (underscores allowed)
    and that no existing account already has the username (case-insensitive)."""
    uname = username.strip()
    if len(uname) < 3:
        return UsernameAvailability(username=uname, available=False, reason="At least 3 characters")
    if not _USERNAME_RE.match(uname):
        return UsernameAvailability(
            username=uname, available=False, reason="Only letters, numbers, and underscores"
        )
    taken = (
        await db.execute(
            select(User.id).where(func.lower(User.username) == uname.lower()).limit(1)
        )
    ).scalar_one_or_none()
    if taken is not None:
        return UsernameAvailability(username=uname, available=False, reason="Already taken")
    return UsernameAvailability(username=uname, available=True)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbDep) -> TokenResponse:
    clashes = (
        await db.execute(
            select(User.email, User.username).where(
                (func.lower(User.email) == body.email.lower())
                | (func.lower(User.username) == body.username.lower())
            )
        )
    ).all()
    if clashes:
        email_taken = any(e.lower() == body.email.lower() for e, _ in clashes)
        username_taken = any(u.lower() == body.username.lower() for _, u in clashes)
        if email_taken and username_taken:
            detail = "email and username are already in use"
        elif email_taken:
            detail = "email is already in use"
        else:
            detail = "username is already taken"
        raise HTTPException(status.HTTP_409_CONFLICT, detail)

    display_name = " ".join(p for p in [body.first_name, body.last_name] if p) or None
    user = User(
        email=body.email,
        username=body.username,
        first_name=body.first_name,
        last_name=body.last_name,
        display_name=display_name,
        password_hash=hash_password(body.password),
        auth_provider="password",
    )
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id))  # empty profile; the agent fills it conversationally
    await db.flush()

    refresh, _jti = create_refresh_token(str(user.id), user.role)
    return TokenResponse(access_token=create_access_token(str(user.id), user.role), refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbDep) -> TokenResponse:
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    refresh, _jti = create_refresh_token(str(user.id), user.role)
    return TokenResponse(access_token=create_access_token(str(user.id), user.role), refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbDep) -> TokenResponse:
    """Exchange a valid refresh token for a fresh access + refresh pair (docs/11 §1).

    Rotates the refresh token on every use. NOTE: a Redis `jti` blocklist for reuse
    detection (stolen-refresh → revoke family) is still TODO (docs/11 §1).
    """
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token") from exc

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")

    new_refresh, _jti = create_refresh_token(str(user.id), user.role)
    return TokenResponse(access_token=create_access_token(str(user.id), user.role), refresh_token=new_refresh)


# POST /oauth/google, /oauth/apple, /logout — see docs/10 §2 + docs/11 §1.
