"""Role-based access control policy (docs/11 §2).

Framework-free on purpose: the `Role` enum and the privilege hierarchy live here so
the service layer, the agent tool layer, and the API all share one source of truth.
The FastAPI wiring (dependencies that turn this policy into 401/403s) lives in
``app.api.deps`` — keep this module free of `fastapi`/`db` imports to avoid cycles.
"""
from __future__ import annotations

import enum


class Role(str, enum.Enum):
    """Account roles stored in ``users.role`` (docs/11 §2)."""

    USER = "user"
    CREATOR = "creator"
    COACH = "coach"
    MODERATOR = "moderator"
    ADMIN = "admin"


# Privilege ordering — higher index == more privilege. This is a deliberate
# linear simplification of an otherwise mixed model (creator/coach are account
# *types* more than escalations); it exists to back `require_min_role` for the
# staff escalation path. For non-hierarchical needs use an explicit role set via
# `has_any_role` / `require_roles`.
_ORDER: tuple[Role, ...] = (Role.USER, Role.CREATOR, Role.COACH, Role.MODERATOR, Role.ADMIN)
_RANK: dict[Role, int] = {role: rank for rank, role in enumerate(_ORDER)}


def normalize_role(value: str | Role | None) -> Role:
    """Coerce a stored role string to a `Role`.

    Unknown / missing values deny-by-default to the lowest privilege (`USER`) so a
    bad row can never silently satisfy an elevated check.
    """
    if isinstance(value, Role):
        return value
    if value is None:
        return Role.USER
    try:
        return Role(value)
    except ValueError:
        return Role.USER


def has_min_role(user_role: str | Role, minimum: str | Role) -> bool:
    """True if `user_role` is at least as privileged as `minimum` (linear hierarchy)."""
    return _RANK[normalize_role(user_role)] >= _RANK[normalize_role(minimum)]


def has_any_role(user_role: str | Role, allowed, *, allow_admin: bool = True) -> bool:
    """True if `user_role` is in `allowed`. Admin is a superuser unless `allow_admin=False`."""
    role = normalize_role(user_role)
    if allow_admin and role is Role.ADMIN:
        return True
    return role in {normalize_role(r) for r in allowed}
