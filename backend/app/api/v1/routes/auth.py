"""Auth routes (docs/10 §2). Email + password reset + (OAuth stubs)."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, update

from app.api.deps import DbDep
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.db.models.auth import PasswordResetCode
from app.db.models.user import Profile, User
from app.integrations.email import password_reset_email, send_email
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UsernameAvailability,
)

logger = logging.getLogger(__name__)

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


# --- Password reset (forgot password → OTP email → reset) — docs/11 §1 ---------------
# To avoid leaking which emails are registered, both endpoints return the same generic
# 200 message whether or not the account exists. The OTP is stored hashed (argon2) and is
# single-use, time-boxed, and rate-limited per code.

_RESET_ACK = MessageResponse(
    message="If an account exists for that email, a reset code has been sent."
)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: DbDep) -> MessageResponse:
    """Issue a one-time reset code and email it. Always returns the same ack."""
    user = (
        await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return _RESET_ACK

    # Invalidate any earlier outstanding codes for this user so only the newest works.
    await db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id, PasswordResetCode.consumed_at.is_(None))
        .values(consumed_at=datetime.now(timezone.utc))
    )

    code = generate_otp()
    ttl = settings.password_reset_otp_ttl_min
    db.add(
        PasswordResetCode(
            user_id=user.id,
            code_hash=hash_password(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl),
        )
    )
    await db.flush()

    subject, text, html = password_reset_email(code=code, ttl_min=ttl)
    try:
        await send_email(to=user.email, subject=subject, text=text, html=html)
    except Exception:  # don't 500 (and leak existence/SMTP state) on mail failure
        logger.exception("Failed to send password reset email to user %s", user.id)
    return _RESET_ACK


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(body: ResetPasswordRequest, db: DbDep) -> TokenResponse:
    """Verify the emailed OTP and set a new password. Returns a fresh token pair on success."""
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired code")

    user = (
        await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))
    ).scalar_one_or_none()
    if user is None:
        raise invalid

    rec = (
        await db.execute(
            select(PasswordResetCode)
            .where(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.consumed_at.is_(None),
            )
            .order_by(PasswordResetCode.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if rec is None or rec.expires_at <= datetime.now(timezone.utc):
        raise invalid
    if rec.attempts >= settings.password_reset_max_attempts:
        rec.consumed_at = datetime.now(timezone.utc)  # burn it; force a new request
        await db.commit()  # persist the burn (get_db rolls back when we raise below)
        raise invalid

    if not verify_password(body.otp, rec.code_hash):
        rec.attempts += 1
        await db.commit()  # persist the failed attempt before raising (else it's rolled back)
        raise invalid

    # Success: consume the code and rotate the password.
    rec.consumed_at = datetime.now(timezone.utc)
    user.password_hash = hash_password(body.new_password)
    await db.flush()

    refresh, _jti = create_refresh_token(str(user.id), user.role)
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role), refresh_token=refresh
    )


# POST /oauth/google, /oauth/apple, /logout — see docs/10 §2 + docs/11 §1.
