"""Nutrition routes: label OCR → custom foods DB → meal logging (docs/05, docs/10)."""
from __future__ import annotations

import logging
import uuid
from datetime import date

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.db.models.nutrition import Food, MealLog
from app.integrations.storage import upload_bytes
from app.ml.food.ocr import extract_food_label
from app.schemas.nutrition import (
    DayNutrition,
    DayTotals,
    FoodCreate,
    FoodDraft,
    FoodOut,
    MealLogCreate,
    MealLogOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MAX_BYTES = 8 * 1024 * 1024
_NUM = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")


def _f(v) -> float | None:
    return float(v) if v is not None else None


def _food_out(f: Food) -> FoodOut:
    return FoodOut(
        id=f.id, name=f.name, brand=f.brand, serving_size=f.serving_size,
        calories=_f(f.calories), protein_g=_f(f.protein_g), carbs_g=_f(f.carbs_g), fat_g=_f(f.fat_g),
        fiber_g=_f(f.fiber_g), sugar_g=_f(f.sugar_g), sodium_mg=_f(f.sodium_mg),
        ingredients=f.ingredients, image_url=f.image_url, created_at=f.created_at,
    )


@router.post("/analyze", response_model=FoodDraft)
async def analyze_label(user: CurrentUser, db: DbDep, file: UploadFile = File(...)) -> FoodDraft:
    """OCR a nutrition-label photo. Returns a draft for the user to review/name (not saved yet)."""
    ctype = file.content_type or ""
    if ctype not in _EXT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "image must be JPEG, PNG, or WEBP")
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "image must be ≤ 8 MB")

    key = f"foods/{user.id}/{uuid.uuid4().hex}.{_EXT[ctype]}"
    image_url = await upload_bytes(data, key, ctype)

    try:
        extracted = await extract_food_label(data, ctype)
    except Exception:
        # OCR failed — still return the image so the user can fill fields manually.
        logger.exception("Label OCR failed; returning empty draft.")
        return FoodDraft(image_url=image_url, raw={"ocr_error": True})

    return FoodDraft(
        name=extracted.get("name"),
        brand=extracted.get("brand"),
        serving_size=extracted.get("serving_size"),
        calories=extracted.get("calories"),
        protein_g=extracted.get("protein_g"),
        carbs_g=extracted.get("carbs_g"),
        fat_g=extracted.get("fat_g"),
        fiber_g=extracted.get("fiber_g"),
        sugar_g=extracted.get("sugar_g"),
        sodium_mg=extracted.get("sodium_mg"),
        ingredients=extracted.get("ingredients"),
        image_url=image_url,
        raw=extracted,
    )


@router.post("/foods", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
async def create_food(body: FoodCreate, user: CurrentUser, db: DbDep) -> FoodOut:
    food = Food(
        user_id=user.id, name=body.name, brand=body.brand, serving_size=body.serving_size,
        calories=body.calories, protein_g=body.protein_g, carbs_g=body.carbs_g, fat_g=body.fat_g,
        fiber_g=body.fiber_g, sugar_g=body.sugar_g, sodium_mg=body.sodium_mg,
        ingredients=body.ingredients, image_url=body.image_url, raw=body.raw or {},
    )
    db.add(food)
    await db.flush()
    return _food_out(food)


@router.get("/foods", response_model=list[FoodOut])
async def list_foods(user: CurrentUser, db: DbDep) -> list[FoodOut]:
    rows = (
        await db.execute(
            select(Food).where(Food.user_id == user.id).order_by(Food.created_at.desc())
        )
    ).scalars().all()
    return [_food_out(f) for f in rows]


@router.delete("/foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(food_id: uuid.UUID, user: CurrentUser, db: DbDep) -> None:
    food = (await db.execute(select(Food).where(Food.id == food_id))).scalar_one_or_none()
    if food is None or food.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "food not found")
    await db.delete(food)


@router.post("/log", response_model=MealLogOut, status_code=status.HTTP_201_CREATED)
async def log_meal(body: MealLogCreate, user: CurrentUser, db: DbDep) -> MealLogOut:
    food = (await db.execute(select(Food).where(Food.id == body.food_id))).scalar_one_or_none()
    if food is None or food.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "food not found")
    entry = MealLog(
        user_id=user.id, food_id=food.id, meal_type=body.meal_type, servings=body.servings,
        logged_on=body.logged_on or date.today(),
    )
    db.add(entry)
    await db.flush()
    s = float(entry.servings)
    cal, pro = _f(food.calories), _f(food.protein_g)
    return MealLogOut(
        id=entry.id, food_id=food.id, food_name=food.name, meal_type=entry.meal_type, servings=s,
        calories=(cal * s) if cal is not None else None,
        protein_g=(pro * s) if pro is not None else None,
        logged_at=entry.logged_at,
    )


@router.get("/day", response_model=DayNutrition)
async def day(
    user: CurrentUser,
    db: DbDep,
    on: Annotated[date | None, Query(description="day to view (YYYY-MM-DD); defaults today")] = None,
) -> DayNutrition:
    target = on or date.today()
    rows = (
        await db.execute(
            select(MealLog, Food)
            .join(Food, Food.id == MealLog.food_id)
            .where(MealLog.user_id == user.id, MealLog.logged_on == target)
            .order_by(MealLog.logged_at)
        )
    ).all()

    entries: list[MealLogOut] = []
    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for log, food in rows:
        s = float(log.servings)
        for k in ("calories", "protein_g", "carbs_g", "fat_g"):
            totals[k] += (_f(getattr(food, k)) or 0.0) * s
        entries.append(
            MealLogOut(
                id=log.id, food_id=food.id, food_name=food.name, meal_type=log.meal_type, servings=s,
                calories=(_f(food.calories) or 0.0) * s, protein_g=(_f(food.protein_g) or 0.0) * s,
                logged_at=log.logged_at,
            )
        )
    return DayNutrition(day=target, totals=DayTotals(**{k: round(v, 1) for k, v in totals.items()}), entries=entries)


@router.delete("/log/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_log(log_id: uuid.UUID, user: CurrentUser, db: DbDep) -> None:
    entry = (await db.execute(select(MealLog).where(MealLog.id == log_id))).scalar_one_or_none()
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "log entry not found")
    await db.delete(entry)
