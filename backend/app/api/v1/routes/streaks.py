"""Streaks + friends leaderboard routes (docs/02 §3.4).

A one-tap gym check-in plus a protein-from-bodyweight target drive two daily streaks and a
leaderboard scoped to the people you follow. Users can hide their streaks (profiles.streaks_public);
hidden users drop out of other people's leaderboards but always see their own numbers.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DbDep
from app.db.models.health import GymCheckin
from app.db.models.nutrition import Food, MealLog
from app.db.models.social import Follow
from app.db.models.user import Profile, User
from app.schemas.social import Author
from app.schemas.streaks import (
    CheckinResult,
    Leaderboard,
    LeaderboardEntry,
    MyStreaks,
    StreaksToday,
)
from app.services.streaks import (
    WINDOW_DAYS,
    compute_streak,
    gym_days,
    protein_days,
    protein_target_g,
)

router = APIRouter()

LEADERBOARD_WINDOW = 30  # days the leaderboard counts span


def _author(u: User) -> Author:
    return Author(id=u.id, username=u.username, display_name=u.display_name, avatar_url=u.avatar_url)


async def _protein_logged_on(db: DbDep, user_id: uuid.UUID, day: date) -> float:
    """Total grams of protein the user logged on a single day."""
    total = (
        await db.execute(
            select(func.sum(func.coalesce(Food.protein_g, 0) * MealLog.servings))
            .join(Food, Food.id == MealLog.food_id)
            .where(MealLog.user_id == user_id, MealLog.logged_on == day)
        )
    ).scalar_one_or_none()
    return float(total or 0)


async def _gym_streak(db: DbDep, user_id: uuid.UUID, today: date) -> int:
    since = today - timedelta(days=WINDOW_DAYS)
    days = (await gym_days(db, [user_id], since)).get(user_id, set())
    return compute_streak(days, today)


@router.post("/checkin", response_model=CheckinResult)
async def gym_checkin(user: CurrentUser, db: DbDep) -> CheckinResult:
    """Record today's gym check-in (idempotent — checking in twice is a no-op)."""
    today = date.today()
    existing = (
        await db.execute(
            select(GymCheckin).where(GymCheckin.user_id == user.id, GymCheckin.day == today)
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(GymCheckin(user_id=user.id, day=today))
        await db.flush()
    return CheckinResult(gym_checked_in=True, gym_streak=await _gym_streak(db, user.id, today))


@router.delete("/checkin", response_model=CheckinResult)
async def undo_gym_checkin(user: CurrentUser, db: DbDep) -> CheckinResult:
    """Undo today's gym check-in (in case it was a mistap)."""
    today = date.today()
    await db.execute(
        delete(GymCheckin).where(GymCheckin.user_id == user.id, GymCheckin.day == today)
    )
    await db.flush()
    return CheckinResult(gym_checked_in=False, gym_streak=await _gym_streak(db, user.id, today))


@router.get("/me", response_model=MyStreaks)
async def my_streaks(user: CurrentUser, db: DbDep) -> MyStreaks:
    today = date.today()
    since = today - timedelta(days=WINDOW_DAYS)

    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalar_one_or_none()
    weight = float(profile.weight_kg) if profile and profile.weight_kg is not None else None
    target = protein_target_g(weight)

    gd = (await gym_days(db, [user.id], since)).get(user.id, set())
    pd = (await protein_days(db, {user.id: target}, since)).get(user.id, set())

    logged_today = await _protein_logged_on(db, user.id, today)
    return MyStreaks(
        gym_streak=compute_streak(gd, today),
        protein_streak=compute_streak(pd, today),
        today=StreaksToday(
            day=today,
            gym_checked_in=today in gd,
            protein_target_g=target,
            protein_logged_g=round(logged_today, 1),
            protein_met=today in pd,
        ),
    )


@router.get("/leaderboard", response_model=Leaderboard)
async def leaderboard(
    user: CurrentUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Leaderboard:
    """Ranked board of you + the people you follow (who haven't hidden their streaks)."""
    today = date.today()
    since = today - timedelta(days=WINDOW_DAYS)
    window_start = today - timedelta(days=LEADERBOARD_WINDOW - 1)

    followee_ids = set(
        (
            await db.execute(select(Follow.followee_id).where(Follow.follower_id == user.id))
        ).scalars().all()
    )
    candidate_ids = followee_ids | {user.id}

    rows = (
        await db.execute(
            select(User, Profile)
            .join(Profile, Profile.user_id == User.id)
            .where(User.id.in_(candidate_ids), User.is_active.is_(True))
        )
    ).all()
    # Self always visible; followed users only if they keep streaks public.
    included = [
        (u, p) for u, p in rows if u.id == user.id or p.streaks_public
    ]
    if not included:
        return Leaderboard(window_days=LEADERBOARD_WINDOW, entries=[])

    ids = [u.id for u, _ in included]
    targets = {
        u.id: protein_target_g(float(p.weight_kg) if p.weight_kg is not None else None)
        for u, p in included
    }
    gd_map = await gym_days(db, ids, since)
    pd_map = await protein_days(db, targets, since)

    entries: list[LeaderboardEntry] = []
    for u, _ in included:
        gd = gd_map.get(u.id, set())
        pd = pd_map.get(u.id, set())
        gym_window = sum(1 for d in gd if d >= window_start)
        protein_window = sum(1 for d in pd if d >= window_start)
        entries.append(
            LeaderboardEntry(
                user=_author(u),
                gym_streak=compute_streak(gd, today),
                protein_streak=compute_streak(pd, today),
                gym_days=gym_window,
                protein_days=protein_window,
                score=gym_window + protein_window,
                is_me=u.id == user.id,
            )
        )

    entries.sort(
        key=lambda e: (-e.score, -(e.gym_streak + e.protein_streak), e.user.username.lower())
    )
    return Leaderboard(window_days=LEADERBOARD_WINDOW, entries=entries[:limit])
