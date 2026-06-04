"""Unit tests for the RBAC policy (app.core.rbac)."""
from __future__ import annotations

from app.core.rbac import Role, has_any_role, has_min_role, normalize_role


def test_normalize_role_known_and_unknown():
    assert normalize_role("admin") is Role.ADMIN
    assert normalize_role(Role.COACH) is Role.COACH
    # Unknown / missing deny-by-default to the lowest privilege.
    assert normalize_role("superuser") is Role.USER
    assert normalize_role(None) is Role.USER


def test_has_min_role_hierarchy():
    assert has_min_role(Role.ADMIN, Role.MODERATOR) is True
    assert has_min_role(Role.MODERATOR, Role.MODERATOR) is True
    assert has_min_role(Role.USER, Role.MODERATOR) is False
    assert has_min_role("coach", "user") is True


def test_has_any_role_membership_and_admin_override():
    assert has_any_role(Role.COACH, [Role.COACH, Role.CREATOR]) is True
    assert has_any_role(Role.USER, [Role.COACH]) is False
    # Admin is a superuser by default...
    assert has_any_role(Role.ADMIN, [Role.COACH]) is True
    # ...unless explicitly disabled.
    assert has_any_role(Role.ADMIN, [Role.COACH], allow_admin=False) is False
