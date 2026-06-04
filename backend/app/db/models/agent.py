"""Agent conversation, message, and memory models. Mirrors docs/02 §3.6, docs/04."""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    persona: Mapped[str] = mapped_column(String, default="friendly")


class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String)  # user|assistant|tool|system
    content: Mapped[list | dict] = mapped_column(JSONB)  # content blocks
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String, index=True)  # see memory_type in docs/02
    content: Mapped[str] = mapped_column(Text)
    structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    importance: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.8)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agent_memories.id"), nullable=True
    )


class Embedding(Base):
    __tablename__ = "embeddings"

    owner_type: Mapped[str] = mapped_column(String)  # memory|food|post|exercise|profile
    owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
