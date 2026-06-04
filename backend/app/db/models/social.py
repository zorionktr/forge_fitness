"""Social models: posts, comments, likes (docs/02 §3.3, docs/06).

Simplified from docs/02 for the scaffold: non-partitioned, using the Base id/timestamp
convention. Keeps the core columns (kind, body, media, denormalized counts, visibility)
so the feed + posting flow works and can grow toward the full spec.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    author_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String, default="text")  # text|image|video|workout|...
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media: Mapped[list] = mapped_column(JSONB, default=list)  # [{url,type,w,h}]
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    visibility: Mapped[str] = mapped_column(String, default="public")  # public|followers|private


class Comment(Base):
    __tablename__ = "comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("comments.id"), nullable=True  # threaded
    )
    body: Mapped[str] = mapped_column(Text)
    like_count: Mapped[int] = mapped_column(Integer, default=0)


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_like_once"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String)  # post|comment
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
