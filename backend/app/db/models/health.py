"""Body measurement history (docs/02 §3.2).

The profile holds the *latest* height/weight; every change (a real weigh-in OR a
correction of a previously-wrong value) is appended here so progress is tracked over
time and nothing is silently overwritten.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
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
