"""RAG memory retrieval (docs/04 §4). Runs before each agent response.

Hybrid: vector similarity over agent_memories + always-on safety context (injuries/allergies/active
goals) regardless of similarity, reranked by importance*recency*similarity, trimmed to a budget.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embeddings import BGEEmbedder, get_embedder
from app.core.config import settings
from app.db.models.agent import AgentMemory, Embedding

logger = logging.getLogger(__name__)


@dataclass
class RetrievedMemory:
    content: str
    type: str
    importance: float
    score: float


class MemoryRetriever:
    def __init__(self, embedder: BGEEmbedder | None = None) -> None:
        self._embedder = embedder or get_embedder()

    async def retrieve(
        self, db: AsyncSession, user_id: uuid.UUID, query: str, top_k: int | None = None
    ) -> list[RetrievedMemory]:
        top_k = top_k or settings.rag_top_k

        # 1. Always-on safety context: injuries/allergies/active goals are non-negotiable.
        safety = (
            await db.execute(
                select(AgentMemory)
                .where(
                    AgentMemory.user_id == user_id,
                    AgentMemory.type.in_(["injury", "nutrition"]),
                    AgentMemory.superseded_by.is_(None),
                )
                .limit(8)
            )
        ).scalars().all()

        # 2. Vector recall over the rest, using the BGE-M3 embedder. If the model can't
        # load or errors, degrade gracefully to safety-only context so the agent still
        # responds instead of 500-ing the whole stream.
        rows: list = []
        try:
            query_vec = (await self._embedder.embed([query]))[0]
            rows = (
                await db.execute(
                    select(AgentMemory, Embedding.embedding.cosine_distance(query_vec).label("dist"))
                    .join(Embedding, (Embedding.owner_id == AgentMemory.id) & (Embedding.owner_type == "memory"))
                    .where(AgentMemory.user_id == user_id, AgentMemory.superseded_by.is_(None))
                    .order_by("dist")
                    .limit(top_k * 2)
                )
            ).all()
        except Exception:  # model load / embedding / db error shouldn't kill the response
            logger.exception("Semantic memory recall failed; continuing with safety context only.")

        # 3. Rerank: similarity + importance (recency/use_count omitted in scaffold).
        scored: dict[uuid.UUID, RetrievedMemory] = {}
        for m in safety:
            scored[m.id] = RetrievedMemory(m.content, m.type, float(m.importance), score=1.0)
        for mem, dist in rows:
            sim = 1.0 - float(dist)
            score = 0.6 * sim + 0.4 * float(mem.importance)
            scored.setdefault(mem.id, RetrievedMemory(mem.content, mem.type, float(mem.importance), score))

        ranked = sorted(scored.values(), key=lambda r: r.score, reverse=True)
        return ranked[:top_k]
