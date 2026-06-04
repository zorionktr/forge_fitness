"""Local text embeddings via BGE-M3 (docs/04 §3).

Replaces the Voyage-3 stub with an in-process sentence-transformers model. BAAI/bge-m3 emits
1024-dim dense vectors — matching ``settings.embedding_dim`` and the pgvector column — and we
L2-normalize them so cosine distance (used in the retriever) behaves well.

The model is heavy (~2 GB) so it's lazy-loaded once per process and cached; the async wrapper
runs the blocking encode on a worker thread so it never stalls the event loop.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import anyio

from app.core.config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class BGEEmbedder:
    """BGE-M3 dense embedder. `encode` is sync (Celery); `embed` is the async request-path wrapper."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model %s (first call may download weights)…", self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Synchronous encode → list of normalized 1024-dim dense vectors."""
        vecs = self._ensure_model().encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Async wrapper for the request path; offloads the blocking encode to a thread."""
        return await anyio.to_thread.run_sync(self.encode, texts)


@lru_cache(maxsize=1)
def get_embedder() -> BGEEmbedder:
    """Process-wide singleton so the model loads at most once."""
    return BGEEmbedder()
