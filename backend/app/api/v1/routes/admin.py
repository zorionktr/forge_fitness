"""Admin routes — gated by RBAC (docs/11 §2).

These exist to exercise the authorization layer end-to-end: every handler takes an
`AdminUser` dependency, so a valid token with a non-admin role gets 403 while an
invalid/absent token gets 401. Mutating actions here are the kind docs/11 §2 wants
audit-logged once `audit_logs` lands.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import AdminUser, DbDep
from app.core.rbac import Role
from app.db.models.user import User
from app.schemas.admin import RoleUpdate, UserOut

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _admin: AdminUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    rows = await db.execute(select(User).order_by(User.created_at).limit(limit).offset(offset))
    return list(rows.scalars().all())


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(user_id: uuid.UUID, body: RoleUpdate, admin: AdminUser, db: DbDep) -> User:
    if user_id == admin.id:
        # Guard against an admin locking themselves out of admin actions.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot change your own role")

    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

    target.role = Role(body.role).value  # validated by the schema; normalize to the stored string
    # TODO(docs/11 §2): write an audit_logs entry (actor=admin.id, action=role_change, target=user_id).
    return target
