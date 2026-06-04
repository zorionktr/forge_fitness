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
    # Either body or media (or both) must be present — enforced in the route.
    body: str | None = Field(default=None, max_length=5000)
    media: list = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=10)
    kind: str = "text"


class PostOut(BaseModel):
    id: uuid.UUID
    author: Author
    kind: str
    body: str | None
    media: list
    tags: list[str]
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: datetime
    # Why this post is in the feed ("Followed", "Popular in #legday", …). Read-only.
    reason: str | None = None


class MediaOut(BaseModel):
    url: str
    type: str = "image"


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: uuid.UUID
    author: Author
    body: str
    created_at: datetime


# ---- Social graph: follows / discover ----


class UserCard(BaseModel):
    """A user as shown in search / suggestions, with the viewer's follow state."""

    id: uuid.UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    follower_count: int = 0
    is_following: bool = False


class FollowState(BaseModel):
    following: bool
    follower_count: int


class PublicProfile(BaseModel):
    """Another user's profile as seen when 'stalking' from search (read-only)."""

    id: uuid.UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    age: int | None = None
    sex: str | None = None
    goals: list[str] = []
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    is_following: bool = False
    is_me: bool = False
    # Streaks are None when the user has hidden them (and it isn't you).
    streaks_public: bool = True
    gym_streak: int | None = None
    protein_streak: int | None = None


# ---- Stories ----


class StoryCreate(BaseModel):
    media: list = Field(min_length=1)  # at least one image
    caption: str | None = Field(default=None, max_length=500)


class StoryItem(BaseModel):
    id: uuid.UUID
    author: Author
    media: list
    caption: str | None
    created_at: datetime
    expires_at: datetime
    like_count: int
    comment_count: int
    liked_by_me: bool


class StoryTray(BaseModel):
    """All active stories from one author, grouped for the feed tray."""

    author: Author
    items: list[StoryItem]


class StoryCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class StoryCommentOut(BaseModel):
    id: uuid.UUID
    author: Author
    body: str
    created_at: datetime
