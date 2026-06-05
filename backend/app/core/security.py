"""Auth primitives: password hashing + JWT. See docs/11."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.rbac import Role

_ph = PasswordHasher()


def hash_password(raw: str) -> str:
    return _ph.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False


def generate_otp(digits: int = 6) -> str:
    """A cryptographically-random numeric one-time code (zero-padded)."""
    return f"{secrets.randbelow(10 ** digits):0{digits}d}"


def _encode(sub: str, ttl: timedelta, token_type: str, role: str) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), jti


def create_access_token(user_id: str, role: str = Role.USER.value) -> str:
    token, _ = _encode(user_id, timedelta(minutes=settings.access_token_ttl_min), "access", role)
    return token


def create_refresh_token(user_id: str, role: str = Role.USER.value) -> tuple[str, str]:
    """Returns (token, jti) so the jti can be tracked for rotation/revocation."""
    return _encode(user_id, timedelta(days=settings.refresh_token_ttl_days), "refresh", role)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # pragma: no cover - thin wrapper
        raise ValueError("invalid token") from exc
