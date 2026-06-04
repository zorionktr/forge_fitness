"""Nutrition (foods + meal log) schemas (docs/05, docs/10)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class FoodFields(BaseModel):
    """Editable nutrition fields shared by the OCR draft and the saved food."""

    brand: str | None = None
    serving_size: str | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    ingredients: str | None = None


class FoodDraft(FoodFields):
    """What the OCR endpoint returns for the user to review/name before saving."""

    name: str | None = None
    image_url: str | None = None
    raw: dict = {}


class FoodCreate(FoodFields):
    name: str = Field(min_length=1, max_length=120)
    image_url: str | None = None
    raw: dict = {}


class FoodOut(FoodFields):
    id: uuid.UUID
    name: str
    image_url: str | None
    created_at: datetime


class MealLogCreate(BaseModel):
    food_id: uuid.UUID
    meal_type: str = "snack"  # breakfast|lunch|dinner|snack
    servings: float = Field(default=1, gt=0, le=50)
    logged_on: date | None = None  # defaults to today; set to backfill a past day


class MealLogOut(BaseModel):
    id: uuid.UUID
    food_id: uuid.UUID
    food_name: str
    meal_type: str
    servings: float
    calories: float | None
    protein_g: float | None
    logged_at: datetime


class DayTotals(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class DayNutrition(BaseModel):
    day: date
    totals: DayTotals
    entries: list[MealLogOut]
