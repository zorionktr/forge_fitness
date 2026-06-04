"""Embedding generation task (docs/04 §3): embed memories/foods/posts -> pgvector.

Uses the shared BGE-M3 embedder (app.agent.embeddings). The Celery worker is synchronous, so
the DB upsert runs via a short-lived async engine (NullPool) inside asyncio.run — keeping pooled
asyncpg connections from leaking across the worker's task event loops.
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.agent.embeddings import get_embedder
from app.core.config import settings
from app.db.models.agent import Embedding
from app.workers.celery_app import celery_app


async def _upsert_embedding(
    *, owner_type: str, owner_id: uuid.UUID, vector: list[float], user_id: uuid.UUID | None
) -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine) as db:
            existing = (
                await db.execute(
                    select(Embedding).where(
                        Embedding.owner_type == owner_type, Embedding.owner_id == owner_id
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    Embedding(
                        owner_type=owner_type,
                        owner_id=owner_id,
                        user_id=user_id,
                        model=settings.embedding_model,
                        embedding=vector,
                    )
                )
            else:  # re-embed in place (e.g. model upgrade or edited content)
                existing.embedding = vector
                existing.model = settings.embedding_model
            await db.commit()
    finally:
        await engine.dispose()


@celery_app.task(name="tasks.embed", bind=True, max_retries=3)
def embed(self, *, owner_type: str, owner_id: str, text: str, user_id: str | None = None) -> dict:
    """Compute an embedding for an entity and upsert into the embeddings table."""
    try:
        vector = get_embedder().encode([text])[0]
        asyncio.run(
            _upsert_embedding(
                owner_type=owner_type,
                owner_id=uuid.UUID(owner_id),
                vector=vector,
                user_id=uuid.UUID(user_id) if user_id else None,
            )
        )
    except Exception as exc:  # transient model/DB error — let Celery retry
        raise self.retry(exc=exc)
    return {"owner_type": owner_type, "owner_id": owner_id, "dim": len(vector)}
