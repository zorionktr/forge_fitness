"""Admin/RBAC request & response schemas (docs/11 §2)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.core.rbac import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool


class RoleUpdate(BaseModel):
    role: Role
