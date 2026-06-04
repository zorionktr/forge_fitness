"""Nutrition models: user's custom foods (from label OCR) + meal logs (docs/05)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Food(Base):
    """A food the user captured (nutrition label OCR) and named, reusable in meals."""

    __tablename__ = "foods"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, index=True)  # user-given name
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    serving_size: Mapped[str | None] = mapped_column(String, nullable=True)  # "1 cup (240 ml)"
    calories: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    sugar_g: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    sodium_mg: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)  # full OCR/vision payload for traceability
    source: Mapped[str] = mapped_column(String, default="label_ocr")


class MealLog(Base):
    """A logged serving of a food on a given day/meal (docs/05 §4)."""

    __tablename__ = "meal_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    food_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("foods.id", ondelete="CASCADE")
    )
    meal_type: Mapped[str] = mapped_column(String, default="snack")  # breakfast|lunch|dinner|snack
    servings: Mapped[float] = mapped_column(Numeric(5, 2), default=1)
    logged_on: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
