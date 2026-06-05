"""Profile read/update + measurement schemas (docs/10)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    first_name: str | None
    last_name: str | None
    display_name: str | None
    avatar_url: str | None
    role: str
    # profile fields
    bio: str | None = None
    sex: str | None
    goals: list[str] = []
    dob: date | None
    age: int | None
    height_cm: float | None
    weight_kg: float | None
    body_fat_pct: float | None
    activity_level: str | None
    coach_persona: str | None
    streaks_public: bool = True


class ProfileUpdate(BaseModel):
    """All optional — only the provided fields are changed (PATCH semantics)."""

    first_name: str | None = Field(default=None, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)
    bio: str | None = Field(default=None, max_length=500)
    sex: str | None = Field(default=None, max_length=20)
    goals: list[str] | None = Field(default=None, max_length=10)
    dob: date | None = None
    height_cm: float | None = Field(default=None, gt=0, lt=300)
    weight_kg: float | None = Field(default=None, gt=0, lt=600)
    body_fat_pct: float | None = Field(default=None, ge=0, le=80)
    activity_level: str | None = None
    coach_persona: str | None = None
    streaks_public: bool | None = None


class MeasurementOut(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    weight_kg: float | None
    height_cm: float | None
    body_fat_pct: float | None
    source: str
