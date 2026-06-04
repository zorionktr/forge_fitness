"""Social feed routes: create/list posts, like, comment (docs/06, docs/10).

MVP global feed: returns recent public posts (no follow-graph fan-out yet — that's the
worker pipeline in docs/06 §5). Likes use the polymorphic `likes` table.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, or_, select

from app.api.deps import CurrentUser, DbDep
from app.db.models.social import Comment, Follow, Like, Post, Story, StoryComment
from app.db.models.user import User
from app.integrations.storage import upload_bytes
from app.ml.recsys.feed import build_feed
from app.schemas.social import (
    Author,
    CommentCreate,
    CommentOut,
    FollowState,
    MediaOut,
    PostCreate,
    PostOut,
    StoryCommentCreate,
    StoryCommentOut,
    StoryCreate,
    StoryItem,
    StoryTray,
    UserCard,
)

logger = logging.getLogger(__name__)
router = APIRouter()
STORY_TTL = timedelta(hours=24)

# Post image uploads (mirrors the avatar limits in routes/profile.py).
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_IMAGES = 10
_IMG_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _author(u: User) -> Author:
    return Author(id=u.id, username=u.username, display_name=u.display_name, avatar_url=u.avatar_url)


def _normalize_tags(tags: list[str]) -> list[str]:
    """Lowercase, strip a leading '#', keep [a-z0-9_-], dedupe (order-preserving), cap at 10."""
    out: list[str] = []
    for raw in tags:
        t = re.sub(r"[^a-z0-9_-]", "", (raw or "").strip().lstrip("#").lower())
        if t and t not in out:
            out.append(t)
        if len(out) >= 10:
            break
    return out


async def _liked_ids(
    db: DbDep, user_id: uuid.UUID, entity_type: str, ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    if not ids:
        return set()
    rows = (
        await db.execute(
            select(Like.entity_id).where(
                Like.user_id == user_id,
                Like.entity_type == entity_type,
                Like.entity_id.in_(ids),
            )
        )
    ).scalars().all()
    return set(rows)


def _post_out(p: Post, author: User, liked: bool, reason: str | None = None) -> PostOut:
    return PostOut(
        id=p.id,
        author=_author(author),
        kind=p.kind,
        body=p.body,
        media=p.media or [],
        tags=p.tags or [],
        like_count=p.like_count,
        comment_count=p.comment_count,
        liked_by_me=liked,
        created_at=p.created_at,
        reason=reason,
    )


def _enqueue_embed(owner_type: str, owner_id: uuid.UUID, text: str) -> None:
    """Best-effort: queue an embedding job so the post joins the recsys ANN index. No-op
    without a Celery broker (the feed degrades to followed + trending)."""
    text = (text or "").strip()
    if not text:
        return
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task(
            "tasks.embed",
            kwargs={"owner_type": owner_type, "owner_id": str(owner_id), "text": text},
        )
    except Exception:  # broker down / not configured — fine, recsys falls back
        logger.debug("embed enqueue skipped for %s %s", owner_type, owner_id)


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreate, user: CurrentUser, db: DbDep) -> PostOut:
    text = (payload.body or "").strip() or None
    media = payload.media or []
    if not text and not media:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "a post needs text or at least one image")

    tags = _normalize_tags(payload.tags)
    kind = "image" if media else "text"
    post = Post(author_id=user.id, kind=kind, body=text, media=media, tags=tags)
    db.add(post)
    await db.flush()
    # Index for the recsys ANN (best-effort): post text + its tags.
    _enqueue_embed("post", post.id, " ".join(filter(None, [text, *tags])))
    return _post_out(post, user, liked=False)


@router.post("/media", response_model=list[MediaOut], status_code=status.HTTP_201_CREATED)
async def upload_media(
    user: CurrentUser,
    files: Annotated[list[UploadFile], File(...)],
) -> list[MediaOut]:
    """Upload up to 10 post images and return their public URLs (then attach via /posts)."""
    if len(files) > _MAX_IMAGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"at most {_MAX_IMAGES} images per post")
    out: list[MediaOut] = []
    for file in files:
        if (file.content_type or "") not in _IMG_EXT:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "images must be JPEG, PNG, WEBP, or GIF")
        data = await file.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "each image must be ≤ 5 MB")
        key = f"posts/{user.id}/{uuid.uuid4().hex}.{_IMG_EXT[file.content_type]}"
        url = await upload_bytes(data, key, file.content_type)
        out.append(MediaOut(url=url, type="image"))
    return out


@router.get("/feed", response_model=list[PostOut])
async def feed(
    user: CurrentUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostOut]:
    """Blended 'For You' feed: followed + interest (embedding ANN) + trending, ranked (docs/07)."""
    ranked = await build_feed(db, user, limit, offset)
    liked = await _liked_ids(db, user.id, "post", [p.id for p, _, _ in ranked])
    return [_post_out(p, u, p.id in liked, reason) for p, u, reason in ranked]


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


# ---------------------------------------------------------------------------
# Social graph: follows + discover
# ---------------------------------------------------------------------------


async def _following_ids(db: DbDep, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = (
        await db.execute(select(Follow.followee_id).where(Follow.follower_id == user_id))
    ).scalars().all()
    return set(rows)


async def _follower_count(db: DbDep, user_id: uuid.UUID) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Follow).where(Follow.followee_id == user_id)
        )
    ).scalar_one()


async def _to_cards(db: DbDep, viewer: User, users: list[User]) -> list[UserCard]:
    ids = [u.id for u in users]
    if not ids:
        return []
    following = set(
        (
            await db.execute(
                select(Follow.followee_id).where(
                    Follow.follower_id == viewer.id, Follow.followee_id.in_(ids)
                )
            )
        ).scalars().all()
    )
    count_rows = (
        await db.execute(
            select(Follow.followee_id, func.count())
            .where(Follow.followee_id.in_(ids))
            .group_by(Follow.followee_id)
        )
    ).all()
    counts = {fid: c for fid, c in count_rows}
    return [
        UserCard(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            follower_count=counts.get(u.id, 0),
            is_following=u.id in following,
        )
        for u in users
    ]


@router.post("/users/{user_id}/follow", response_model=FollowState)
async def follow_user(user_id: uuid.UUID, user: CurrentUser, db: DbDep) -> FollowState:
    if user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "you can't follow yourself")
    if await db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    existing = (
        await db.execute(
            select(Follow).where(Follow.follower_id == user.id, Follow.followee_id == user_id)
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(Follow(follower_id=user.id, followee_id=user_id))
        await db.flush()
    return FollowState(following=True, follower_count=await _follower_count(db, user_id))


@router.delete("/users/{user_id}/follow", response_model=FollowState)
async def unfollow_user(user_id: uuid.UUID, user: CurrentUser, db: DbDep) -> FollowState:
    await db.execute(
        delete(Follow).where(Follow.follower_id == user.id, Follow.followee_id == user_id)
    )
    await db.flush()
    return FollowState(following=False, follower_count=await _follower_count(db, user_id))


@router.get("/users/search", response_model=list[UserCard])
async def search_users(
    user: CurrentUser,
    db: DbDep,
    q: Annotated[str, Query(min_length=1, max_length=50)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[UserCard]:
    pattern = f"%{q.strip()}%"
    users = (
        await db.execute(
            select(User)
            .where(
                User.id != user.id,
                User.is_active.is_(True),
                or_(User.username.ilike(pattern), User.display_name.ilike(pattern)),
            )
            .order_by(func.length(User.username))  # closer-length matches first
            .limit(limit)
        )
    ).scalars().all()
    return await _to_cards(db, user, list(users))


@router.get("/users/suggested", response_model=list[UserCard])
async def suggested_users(
    user: CurrentUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[UserCard]:
    """People to follow — most-followed accounts you don't already follow (popularity cold start)."""
    exclude = (await _following_ids(db, user.id)) | {user.id}
    popularity = (
        select(Follow.followee_id.label("uid"), func.count().label("c"))
        .group_by(Follow.followee_id)
        .subquery()
    )
    users = (
        await db.execute(
            select(User)
            .outerjoin(popularity, popularity.c.uid == User.id)
            .where(User.id.notin_(exclude), User.is_active.is_(True))
            .order_by(func.coalesce(popularity.c.c, 0).desc(), User.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return await _to_cards(db, user, list(users))


# ---------------------------------------------------------------------------
# Stories (ephemeral, 24h)
# ---------------------------------------------------------------------------


def _story_item(s: Story, author: User, liked: bool) -> StoryItem:
    return StoryItem(
        id=s.id,
        author=_author(author),
        media=s.media or [],
        caption=s.caption,
        created_at=s.created_at,
        expires_at=s.expires_at,
        like_count=s.like_count,
        comment_count=s.comment_count,
        liked_by_me=liked,
    )


async def _get_story(db: DbDep, story_id: uuid.UUID) -> Story:
    story = (await db.execute(select(Story).where(Story.id == story_id))).scalar_one_or_none()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "story not found")
    return story


@router.post("/stories", response_model=StoryItem, status_code=status.HTTP_201_CREATED)
async def create_story(payload: StoryCreate, user: CurrentUser, db: DbDep) -> StoryItem:
    if not payload.media:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "a story needs at least one image")
    story = Story(
        author_id=user.id,
        media=payload.media,
        caption=payload.caption,
        expires_at=datetime.now(timezone.utc) + STORY_TTL,
    )
    db.add(story)
    await db.flush()
    return _story_item(story, user, liked=False)


@router.get("/stories", response_model=list[StoryTray])
async def list_stories(user: CurrentUser, db: DbDep) -> list[StoryTray]:
    """Active stories from you + people you follow, grouped by author (yours first)."""
    author_ids = (await _following_ids(db, user.id)) | {user.id}
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(Story, User)
            .join(User, User.id == Story.author_id)
            .where(Story.author_id.in_(author_ids), Story.expires_at > now)
            .order_by(Story.created_at.asc())
        )
    ).all()
    liked = await _liked_ids(db, user.id, "story", [s.id for s, _ in rows])

    trays: dict[uuid.UUID, StoryTray] = {}
    for s, author in rows:
        tray = trays.get(author.id)
        if tray is None:
            tray = StoryTray(author=_author(author), items=[])
            trays[author.id] = tray
        tray.items.append(_story_item(s, author, s.id in liked))

    ordered = list(trays.values())
    # Surface the viewer's own story first (IG-style), keep the rest newest-author-first.
    ordered.sort(key=lambda t: (t.author.id != user.id, -t.items[-1].created_at.timestamp()))
    return ordered


@router.post("/stories/{story_id}/like")
async def like_story(story_id: uuid.UUID, user: CurrentUser, db: DbDep) -> dict:
    story = await _get_story(db, story_id)
    existing = (
        await db.execute(
            select(Like).where(
                Like.user_id == user.id, Like.entity_type == "story", Like.entity_id == story_id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(Like(user_id=user.id, entity_type="story", entity_id=story_id))
        story.like_count += 1
        liked = True
    else:
        await db.execute(delete(Like).where(Like.id == existing.id))
        story.like_count = max(0, story.like_count - 1)
        liked = False
    await db.flush()
    return {"liked": liked, "like_count": story.like_count}


@router.get("/stories/{story_id}/comments", response_model=list[StoryCommentOut])
async def list_story_comments(
    story_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> list[StoryCommentOut]:
    rows = (
        await db.execute(
            select(StoryComment, User)
            .join(User, User.id == StoryComment.author_id)
            .where(StoryComment.story_id == story_id)
            .order_by(StoryComment.created_at)
        )
    ).all()
    return [
        StoryCommentOut(id=c.id, author=_author(u), body=c.body, created_at=c.created_at)
        for c, u in rows
    ]


@router.post(
    "/stories/{story_id}/comments",
    response_model=StoryCommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_story_comment(
    story_id: uuid.UUID, body: StoryCommentCreate, user: CurrentUser, db: DbDep
) -> StoryCommentOut:
    story = await _get_story(db, story_id)
    comment = StoryComment(story_id=story.id, author_id=user.id, body=body.body)
    db.add(comment)
    story.comment_count += 1
    await db.flush()
    return StoryCommentOut(
        id=comment.id, author=_author(user), body=comment.body, created_at=comment.created_at
    )
