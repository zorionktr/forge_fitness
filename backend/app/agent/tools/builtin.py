"""Built-in agent tools (docs/03 §5.2). Scaffold implementations — wire to repositories/services.

Each handler is `async def handler(ctx: ToolContext, **kwargs)` and is strictly user-scoped.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import select

from app.agent.embeddings import get_embedder
from app.agent.tools.registry import ToolContext, tool
from app.core.config import settings
from app.db.models.agent import AgentMemory, Embedding
from app.db.models.nutrition import Food, MealLog
from app.db.models.user import Profile

logger = logging.getLogger(__name__)


@tool(
    name="get_user_profile",
    description="Return the user's structured fitness profile and completeness. Call before giving "
    "personalized advice so facts are real, not assumed.",
    schema={"type": "object", "properties": {}},
)
async def get_user_profile(ctx: ToolContext) -> dict[str, Any]:
    row = (await ctx.db.execute(select(Profile).where(Profile.user_id == ctx.user_id))).scalar_one_or_none()
    if row is None:
        return {"known": False}
    return {
        "known": True,
        "sex": row.sex,
        "height_cm": float(row.height_cm) if row.height_cm else None,
        "weight_kg": float(row.weight_kg) if row.weight_kg else None,
        "body_fat_pct": float(row.body_fat_pct) if row.body_fat_pct else None,
        "activity_level": row.activity_level,
        "gym_access": row.gym_access,
        "equipment": row.equipment,
        "injuries": row.injuries,
        "allergies": row.allergies,
        "coach_persona": row.coach_persona,
        "completeness": row.completeness,
    }


@tool(
    name="update_profile",
    description="Persist fitness facts learned in conversation (e.g. bodyweight, goal, injury). "
    "Only set fields you have explicit information for.",
    schema={
        "type": "object",
        "properties": {
            "weight_kg": {"type": "number"},
            "height_cm": {"type": "number"},
            "body_fat_pct": {"type": "number"},
            "gym_access": {"type": "boolean"},
            "equipment": {"type": "array", "items": {"type": "string"}},
            "allergies": {"type": "array", "items": {"type": "string"}},
        },
    },
    writes=True,
)
async def update_profile(ctx: ToolContext, **fields: Any) -> dict[str, Any]:
    row = (await ctx.db.execute(select(Profile).where(Profile.user_id == ctx.user_id))).scalar_one_or_none()
    if row is None:
        return {"ok": False, "error": "profile not found"}
    for k, v in fields.items():
        if v is not None and hasattr(row, k):
            setattr(row, k, v)
    await ctx.db.flush()
    return {"ok": True, "updated": list(fields.keys())}


@tool(
    name="get_recent_workouts",
    description="Return recent workout sessions with sets so training feedback uses real numbers.",
    schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 5, "maximum": 20},
            "since_days": {"type": "integer", "default": 30},
        },
    },
)
async def get_recent_workouts(ctx: ToolContext, limit: int = 5, since_days: int = 30) -> dict[str, Any]:
    # Wire to WorkoutRepository.recent(ctx.user_id, limit, since_days)
    return {"sessions": [], "note": "scaffold — wire to workout repository"}


def _food_macros(f: Food) -> dict[str, Any]:
    num = lambda v: float(v) if v is not None else None  # noqa: E731
    return {
        "id": str(f.id),
        "name": f.name,
        "serving_size": f.serving_size,
        "calories": num(f.calories),
        "protein_g": num(f.protein_g),
        "carbs_g": num(f.carbs_g),
        "fat_g": num(f.fat_g),
        "ingredients": f.ingredients,
    }


@tool(
    name="list_my_foods",
    description="List the foods the user has saved (from nutrition-label scans), with per-serving "
    "macros and ingredients. Use this to know what foods the user actually has when answering "
    "nutrition questions or building a meal from their items.",
    schema={"type": "object", "properties": {"query": {"type": "string", "description": "optional name filter"}}},
)
async def list_my_foods(ctx: ToolContext, query: str | None = None) -> dict[str, Any]:
    stmt = select(Food).where(Food.user_id == ctx.user_id)
    if query:
        stmt = stmt.where(Food.name.ilike(f"%{query}%"))
    rows = (await ctx.db.execute(stmt.order_by(Food.created_at.desc()).limit(50))).scalars().all()
    return {"foods": [_food_macros(f) for f in rows]}


@tool(
    name="get_today_nutrition",
    description="Return the foods the user has logged today with running calorie/macro totals. "
    "Use to assess remaining budget before recommending or building a meal.",
    schema={"type": "object", "properties": {}},
)
async def get_today_nutrition(ctx: ToolContext) -> dict[str, Any]:
    rows = (
        await ctx.db.execute(
            select(MealLog, Food)
            .join(Food, Food.id == MealLog.food_id)
            .where(MealLog.user_id == ctx.user_id, MealLog.logged_on == date.today())
        )
    ).all()
    num = lambda v: float(v) if v is not None else 0.0  # noqa: E731
    entries, totals = [], {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for log, food in rows:
        s = float(log.servings)
        for k in totals:
            totals[k] += num(getattr(food, k)) * s
        entries.append({"food": food.name, "meal": log.meal_type, "servings": s})
    return {"entries": entries, "totals": {k: round(v, 1) for k, v in totals.items()}}


@tool(
    name="log_food",
    description="Log a serving of one of the user's saved foods into today's meal. Pass the food's "
    "id (from list_my_foods), the meal (breakfast/lunch/dinner/snack), and number of servings.",
    schema={
        "type": "object",
        "properties": {
            "food_id": {"type": "string"},
            "meal_type": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]},
            "servings": {"type": "number", "default": 1},
        },
        "required": ["food_id"],
    },
    writes=True,
)
async def log_food(ctx: ToolContext, food_id: str, meal_type: str = "snack", servings: float = 1) -> dict[str, Any]:
    import uuid as _uuid

    try:
        fid = _uuid.UUID(food_id)
    except ValueError:
        return {"ok": False, "error": "invalid food_id"}
    food = (await ctx.db.execute(select(Food).where(Food.id == fid))).scalar_one_or_none()
    if food is None or food.user_id != ctx.user_id:
        return {"ok": False, "error": "food not found"}
    ctx.db.add(MealLog(user_id=ctx.user_id, food_id=food.id, meal_type=meal_type, servings=servings))
    await ctx.db.flush()
    return {"ok": True, "logged": food.name, "meal": meal_type, "servings": servings}


@tool(
    name="remember",
    description="Store a durable long-term memory about the user (preference, goal, injury, habit).",
    schema={
        "type": "object",
        "properties": {
            "fact": {"type": "string"},
            "type": {"type": "string", "enum": ["preference", "goal", "injury", "behavior", "nutrition"]},
            "importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.6},
        },
        "required": ["fact", "type"],
    },
    writes=True,
)
async def remember(ctx: ToolContext, fact: str, type: str, importance: float = 0.6) -> dict[str, Any]:
    """Persist a durable memory + its BGE-M3 embedding so it's recalled via RAG (docs/04 §2)."""
    memory = AgentMemory(
        user_id=ctx.user_id, type=type, content=fact, importance=importance, source="agent"
    )
    ctx.db.add(memory)
    await ctx.db.flush()
    # Embed inline so the fact is immediately searchable in this same conversation.
    try:
        vec = (await get_embedder().embed([fact]))[0]
        ctx.db.add(
            Embedding(
                owner_type="memory",
                owner_id=memory.id,
                user_id=ctx.user_id,
                model=settings.embedding_model,
                embedding=vec,
            )
        )
        await ctx.db.flush()
    except Exception:  # store the memory even if embedding fails; safety recall still works by type
        logger.exception("Failed to embed memory %s; stored without vector.", memory.id)
    return {"ok": True, "stored": fact, "type": type, "importance": importance}
