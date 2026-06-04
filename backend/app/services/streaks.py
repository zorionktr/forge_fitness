"""Streaks + leaderboard logic (docs/02 §3.4).

Two daily habits are tracked:
  * **gym**     — a one-tap GymCheckin row exists for that day.
  * **protein** — the day's logged protein hit the user's target.

The protein target is derived from bodyweight (no user-set goal): ~1.6 g per kg, a common
muscle-retention/building guideline. Without a weight on file we can't judge protein, so
those days never qualify.

A streak is the run of consecutive days ending today — with a one-day grace so you don't
lose it the instant midnight passes: if today isn't done yet but yesterday was, the streak
still stands (Snapchat-style).
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date, timedelta

from sqlalchemy import func, select

from app.api.deps import DbDep
from app.db.models.health import GymCheckin
from app.db.models.nutrition import Food, MealLog

PROTEIN_PER_KG = 1.6
# How far back we look. A streak longer than this many days won't be fully counted — an
# acceptable bound that keeps the queries cheap.
WINDOW_DAYS = 120


def protein_target_g(weight_kg: float | None) -> float | None:
    """Daily protein target in grams from bodyweight, or None if weight is unknown."""
    if not weight_kg:
        return None
    return round(float(weight_kg) * PROTEIN_PER_KG)


def compute_streak(days: set[date], today: date) -> int:
    """Length of the consecutive run ending today (or yesterday, via the grace day)."""
    cur = today
    if cur not in days:
        cur = today - timedelta(days=1)
        if cur not in days:
            return 0
    count = 0
    while cur in days:
        count += 1
        cur -= timedelta(days=1)
    return count


async def gym_days(db: DbDep, user_ids: Iterable[uuid.UUID], since: date) -> dict[uuid.UUID, set[date]]:
    ids = list(user_ids)
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(GymCheckin.user_id, GymCheckin.day).where(
                GymCheckin.user_id.in_(ids), GymCheckin.day >= since
            )
        )
    ).all()
    out: dict[uuid.UUID, set[date]] = {uid: set() for uid in ids}
    for uid, day in rows:
        out[uid].add(day)
    return out


async def protein_days(
    db: DbDep,
    targets: dict[uuid.UUID, float | None],
    since: date,
) -> dict[uuid.UUID, set[date]]:
    """Days each user's logged protein met their target. Users without a target get an empty set."""
    ids = [uid for uid, t in targets.items() if t]
    out: dict[uuid.UUID, set[date]] = {uid: set() for uid in targets}
    if not ids:
        return out
    rows = (
        await db.execute(
            select(
                MealLog.user_id,
                MealLog.logged_on,
                func.sum(func.coalesce(Food.protein_g, 0) * MealLog.servings),
            )
            .join(Food, Food.id == MealLog.food_id)
            .where(MealLog.user_id.in_(ids), MealLog.logged_on >= since)
            .group_by(MealLog.user_id, MealLog.logged_on)
        )
    ).all()
    for uid, day, total in rows:
        target = targets.get(uid)
        if target and float(total or 0) >= target:
            out[uid].add(day)
    return out
