"""Streaks + leaderboard schemas (docs/02 §3.4)."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.schemas.social import Author


class CheckinCreate(BaseModel):
    """Optional payload for a gym check-in: which muscle groups were trained."""

    muscles: list[str] = Field(default_factory=list, max_length=12)


class StreaksToday(BaseModel):
    """Where today stands for the two habits."""

    day: date
    gym_checked_in: bool
    muscles: list[str] = Field(default_factory=list)  # muscle groups logged today
    protein_target_g: float | None  # None when no bodyweight on file
    protein_logged_g: float
    protein_met: bool


class MyStreaks(BaseModel):
    gym_streak: int
    protein_streak: int
    today: StreaksToday


class CheckinResult(BaseModel):
    gym_checked_in: bool
    gym_streak: int
    muscles: list[str] = Field(default_factory=list)


class LeaderboardEntry(BaseModel):
    user: Author
    gym_streak: int
    protein_streak: int
    gym_days: int       # qualifying gym days in the window
    protein_days: int   # qualifying protein days in the window
    score: int          # gym_days + protein_days (ranking key)
    is_me: bool = False


class Leaderboard(BaseModel):
    window_days: int
    entries: list[LeaderboardEntry]
