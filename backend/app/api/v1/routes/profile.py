"""Profile routes: view/edit profile, weight/height history, avatar upload (docs/10)."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.db.models.health import Measurement
from app.db.models.user import Profile, User
from app.integrations.storage import upload_bytes
from app.schemas.profile import MeasurementOut, ProfileOut, ProfileUpdate

router = APIRouter()

_MAX_AVATAR_BYTES = 5 * 1024 * 1024
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _age(dob: date | None) -> int | None:
    if dob is None:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _as_float(v) -> float | None:
    return float(v) if v is not None else None


async def _profile_of(db: DbDep, user_id: uuid.UUID) -> Profile:
    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None:  # safety net — registration normally creates this
        profile = Profile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


def _to_out(user: User, profile: Profile) -> ProfileOut:
    return ProfileOut(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=user.role,
        bio=profile.bio,
        sex=profile.sex,
        goals=list(profile.goals or []),
        dob=profile.dob,
        age=_age(profile.dob),
        height_cm=_as_float(profile.height_cm),
        weight_kg=_as_float(profile.weight_kg),
        body_fat_pct=_as_float(profile.body_fat_pct),
        activity_level=profile.activity_level,
        coach_persona=profile.coach_persona,
        streaks_public=profile.streaks_public,
    )


@router.get("/me", response_model=ProfileOut)
async def get_me(user: CurrentUser, db: DbDep) -> ProfileOut:
    return _to_out(user, await _profile_of(db, user.id))


@router.patch("/me", response_model=ProfileOut)
async def update_me(body: ProfileUpdate, user: CurrentUser, db: DbDep) -> ProfileOut:
    profile = await _profile_of(db, user.id)

    # --- identity (on the user row) ---
    if body.first_name is not None:
        user.first_name = body.first_name.strip() or None
    if body.last_name is not None:
        user.last_name = body.last_name.strip() or None
    if body.first_name is not None or body.last_name is not None:
        user.display_name = " ".join(p for p in [user.first_name, user.last_name] if p) or None
    if body.bio is not None:
        profile.bio = body.bio.strip() or None

    # --- profile fields; detect height/weight/body-fat changes for history ---
    old = (_as_float(profile.weight_kg), _as_float(profile.height_cm), _as_float(profile.body_fat_pct))
    for field in ("sex", "goals", "dob", "height_cm", "weight_kg", "body_fat_pct", "activity_level", "coach_persona", "streaks_public"):
        val = getattr(body, field)
        if val is not None:
            setattr(profile, field, val)
    new = (_as_float(profile.weight_kg), _as_float(profile.height_cm), _as_float(profile.body_fat_pct))

    # Append a measurement whenever a body metric actually changed (new weigh-in OR a
    # correction) so nothing is silently overwritten and progress is trackable.
    metric_provided = any(getattr(body, f) is not None for f in ("weight_kg", "height_cm", "body_fat_pct"))
    if metric_provided and new != old:
        db.add(
            Measurement(
                user_id=user.id,
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                body_fat_pct=profile.body_fat_pct,
                source="profile_update",
            )
        )

    await db.commit()
    return _to_out(user, profile)


@router.get("/measurements", response_model=list[MeasurementOut])
async def list_measurements(user: CurrentUser, db: DbDep) -> list[Measurement]:
    rows = (
        await db.execute(
            select(Measurement)
            .where(Measurement.user_id == user.id)
            .order_by(Measurement.measured_at.desc())
            .limit(200)
        )
    ).scalars().all()
    return list(rows)


@router.post("/avatar", response_model=ProfileOut)
async def upload_avatar(user: CurrentUser, db: DbDep, file: UploadFile = File(...)) -> ProfileOut:
    if (file.content_type or "") not in _EXT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "avatar must be a JPEG, PNG, WEBP, or GIF image")
    data = await file.read()
    if len(data) > _MAX_AVATAR_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "avatar must be ≤ 5 MB")

    key = f"avatars/{user.id}/{uuid.uuid4().hex}.{_EXT[file.content_type]}"
    user.avatar_url = await upload_bytes(data, key, file.content_type)
    await db.commit()
    return _to_out(user, await _profile_of(db, user.id))
