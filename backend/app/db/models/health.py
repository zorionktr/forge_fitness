"""Body measurement history (docs/02 §3.2).

The profile holds the *latest* height/weight; every change (a real weigh-in OR a
correction of a previously-wrong value) is appended here so progress is tracked over
time and nothing is silently overwritten.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Measurement(Base):
    __tablename__ = "measurements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    source: Mapped[str] = mapped_column(String, default="profile_update")  # how it was recorded


class GymCheckin(Base):
    """A one-tap "I trained today" check-in. One row per user per day powers the gym streak
    and the friends leaderboard. (docs/02 §3.4 — lightweight activity signal.)"""

    __tablename__ = "gym_checkins"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_gym_checkin_day"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    # Muscle groups trained today, e.g. ["chest", "back"]. Logged at check-in time.
    muscles: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
