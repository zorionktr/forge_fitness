"""Social (feed) request/response schemas (docs/06, docs/10)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Author(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class PostCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    kind: str = "text"


class PostOut(BaseModel):
    id: uuid.UUID
    author: Author
    kind: str
    body: str | None
    media: list
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: datetime


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: uuid.UUID
    author: Author
    body: str
    created_at: datetime
