"""User & profile ORM models. Mirrors docs/02 §3.1 (subset for scaffold)."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import ARRAY, Boolean, Date, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.rbac import Role
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String, default="password")
    provider_sub: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default=Role.USER.value, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)  # age derived from this
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String, nullable=True)
    training_age_mo: Mapped[int | None] = mapped_column(nullable=True)
    gym_access: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    equipment: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    diet_type: Mapped[str | None] = mapped_column(String, nullable=True)
    allergies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    injuries: Mapped[list] = mapped_column(JSONB, default=list)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    adherence_score: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    consistency_score: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    motivation_score: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    coach_persona: Mapped[str] = mapped_column(String, default="friendly")
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    user: Mapped[User] = relationship(back_populates="profile")
