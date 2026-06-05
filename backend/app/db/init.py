"""Idempotent schema bootstrap (docs/09 §8).

For simple/single-instance deploys this creates the pgvector extension and any MISSING tables
on startup; existing tables are left untouched (`create_all` is check-first). A Postgres
advisory lock serializes concurrent app workers so they don't race on first boot.

This is a convenience for `FORGE_AUTO_INIT_DB=true`. For versioned, production-grade schema
changes prefer Alembic (`alembic upgrade head`) — don't mix the two on the same database.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.base import Base, engine

logger = logging.getLogger(__name__)

_LOCK_KEY = 991_021  # arbitrary, stable app-wide key for pg_advisory_xact_lock


async def init_db() -> None:
    # Import models so every table is registered on Base.metadata before create_all.
    from app.db.models import agent, auth, health, nutrition, social, user  # noqa: F401

    async with engine.begin() as conn:
        # Serialize across workers/replicas; released automatically at transaction end.
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=_LOCK_KEY))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)  # checkfirst=True → skips existing tables
    logger.info("Database schema ensured (auto-init).")
