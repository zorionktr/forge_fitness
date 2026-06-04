"""Shared FastAPI dependencies: auth, db session, current user (docs/09 §6)."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Role, has_any_role, has_min_role
from app.core.security import decode_token
from app.db.models.user import User
from app.db.session import get_db

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# --- Authorization / RBAC (docs/11 §2) -------------------------------------------------
# Policy lives in app.core.rbac; these factories turn it into 403-raising dependencies.
# Both build on get_current_user, so a missing/invalid token still surfaces as 401 first.

_RoleGuard = Callable[[User], Awaitable[User]]


def require_roles(*allowed: Role, allow_admin: bool = True) -> _RoleGuard:
    """Dependency: allow only the listed roles (admin is a superuser unless disabled)."""

    async def _guard(user: CurrentUser) -> User:
        if has_any_role(user.role, allowed, allow_admin=allow_admin):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")

    return _guard


def require_min_role(minimum: Role) -> _RoleGuard:
    """Dependency: allow any role at least as privileged as `minimum` (linear hierarchy)."""

    async def _guard(user: CurrentUser) -> User:
        if has_min_role(user.role, minimum):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")

    return _guard


# Convenience typed deps for the common gates.
AdminUser = Annotated[User, Depends(require_min_role(Role.ADMIN))]
ModeratorUser = Annotated[User, Depends(require_min_role(Role.MODERATOR))]
StaffUser = Annotated[User, Depends(require_roles(Role.MODERATOR, Role.ADMIN))]


def ensure_owner(
    user: User,
    owner_id: uuid.UUID,
    *,
    allow_roles: tuple[Role, ...] = (Role.MODERATOR, Role.ADMIN),
) -> None:
    """Ownership check for the service layer (docs/11 §2): caller owns the resource,
    or holds an elevated role. Raises 403 otherwise. The agent's tools call the same
    helper, so the agent can never exceed the user's own permissions."""
    if user.id == owner_id:
        return
    if has_any_role(user.role, allow_roles):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "not the resource owner")
