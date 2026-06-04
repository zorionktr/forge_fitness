"""Social feed routes: create/list posts, like, comment (docs/06, docs/10).

MVP global feed: returns recent public posts (no follow-graph fan-out yet — that's the
worker pipeline in docs/06 §5). Likes use the polymorphic `likes` table.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DbDep
from app.db.models.social import Comment, Like, Post
from app.db.models.user import User
from app.schemas.social import (
    Author,
    CommentCreate,
    CommentOut,
    PostCreate,
    PostOut,
)

router = APIRouter()


def _author(u: User) -> Author:
    return Author(id=u.id, username=u.username, display_name=u.display_name, avatar_url=u.avatar_url)


async def _liked_post_ids(db: DbDep, user_id: uuid.UUID, post_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not post_ids:
        return set()
    rows = (
        await db.execute(
            select(Like.entity_id).where(
                Like.user_id == user_id,
                Like.entity_type == "post",
                Like.entity_id.in_(post_ids),
            )
        )
    ).scalars().all()
    return set(rows)


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(body: PostCreate, user: CurrentUser, db: DbDep) -> PostOut:
    post = Post(author_id=user.id, kind=body.kind, body=body.body)
    db.add(post)
    await db.flush()
    return PostOut(
        id=post.id,
        author=_author(user),
        kind=post.kind,
        body=post.body,
        media=post.media or [],
        like_count=0,
        comment_count=0,
        liked_by_me=False,
        created_at=post.created_at,
    )


@router.get("/feed", response_model=list[PostOut])
async def feed(
    user: CurrentUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostOut]:
    rows = (
        await db.execute(
            select(Post, User)
            .join(User, User.id == Post.author_id)
            .where(Post.visibility == "public")
            .order_by(Post.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    liked = await _liked_post_ids(db, user.id, [p.id for p, _ in rows])
    return [
        PostOut(
            id=p.id,
            author=_author(u),
            kind=p.kind,
            body=p.body,
            media=p.media or [],
            like_count=p.like_count,
            comment_count=p.comment_count,
            liked_by_me=p.id in liked,
            created_at=p.created_at,
        )
        for p, u in rows
    ]


async def _get_post(db: DbDep, post_id: uuid.UUID) -> Post:
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
    return post


@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: uuid.UUID, user: CurrentUser, db: DbDep) -> dict:
    post = await _get_post(db, post_id)
    existing = (
        await db.execute(
            select(Like).where(
                Like.user_id == user.id, Like.entity_type == "post", Like.entity_id == post_id
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(Like(user_id=user.id, entity_type="post", entity_id=post_id))
        post.like_count += 1
        liked = True
    else:
        await db.execute(delete(Like).where(Like.id == existing.id))
        post.like_count = max(0, post.like_count - 1)
        liked = False
    await db.flush()
    return {"liked": liked, "like_count": post.like_count}


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
async def list_comments(post_id: uuid.UUID, user: CurrentUser, db: DbDep) -> list[CommentOut]:
    rows = (
        await db.execute(
            select(Comment, User)
            .join(User, User.id == Comment.author_id)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at)
        )
    ).all()
    return [
        CommentOut(id=c.id, author=_author(u), body=c.body, created_at=c.created_at) for c, u in rows
    ]


@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(post_id: uuid.UUID, body: CommentCreate, user: CurrentUser, db: DbDep) -> CommentOut:
    post = await _get_post(db, post_id)
    comment = Comment(post_id=post.id, author_id=user.id, body=body.body)
    db.add(comment)
    post.comment_count += 1
    await db.flush()
    return CommentOut(id=comment.id, author=_author(user), body=comment.body, created_at=comment.created_at)
