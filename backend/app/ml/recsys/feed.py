"""Blended "For You" feed builder (docs/06 §5, docs/07 §2).

Candidate generation (followed authors + embedding ANN over interests + trending) → feature
hydration → transparent weighted ranking (``ranker.score``) → diversity policy. Everything runs
in Postgres + pgvector; no learned model or Kafka fan-out yet. Degrades gracefully: with no
embeddings it falls back to followed + trending, and with no graph it falls back to trending.
"""
from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import Embedding
from app.db.models.social import Follow, Like, Post
from app.db.models.user import User
from app.ml.recsys.ranker import FeedFeatures, score

_POOL = 150          # max candidates to rank per request
_PER_RETRIEVER = 80  # cap per candidate source
_ENGAGEMENT_NORM = 25.0  # like_count that maps to ~max engagement signal
_RECENCY_HALFLIFE_H = 36.0


@dataclass
class Scored:
    post: Post
    author: User
    reason: str
    score: float


async def _following_ids(db: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = (
        await db.execute(select(Follow.followee_id).where(Follow.follower_id == user_id))
    ).scalars().all()
    return set(rows)


async def _interest(db: AsyncSession, user_id: uuid.UUID) -> tuple[list[float] | None, set[str]]:
    """Build the user's interest vector (mean of authored+liked post embeddings) + interest tags.

    Pure aggregation over already-stored vectors — no model inference on the request path.
    """
    authored = (
        await db.execute(select(Post.id).where(Post.author_id == user_id).limit(100))
    ).scalars().all()
    liked = (
        await db.execute(
            select(Like.entity_id).where(Like.user_id == user_id, Like.entity_type == "post").limit(100)
        )
    ).scalars().all()
    post_ids = list({*authored, *liked})
    if not post_ids:
        return None, set()

    # interest tags from those posts
    tag_rows = (await db.execute(select(Post.tags).where(Post.id.in_(post_ids)))).scalars().all()
    tags: set[str] = set()
    for t in tag_rows:
        tags.update(t or [])

    vec_rows = (
        await db.execute(
            select(Embedding.embedding).where(
                Embedding.owner_type == "post", Embedding.owner_id.in_(post_ids)
            )
        )
    ).scalars().all()
    if not vec_rows:
        return None, tags

    dim = len(vec_rows[0])
    mean = [0.0] * dim
    for v in vec_rows:
        for i in range(dim):
            mean[i] += float(v[i])
    norm = math.sqrt(sum(x * x for x in mean)) or 1.0
    return [x / norm for x in mean], tags


def _recency(created_at: datetime) -> float:
    age_h = max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 3600.0)
    return 0.5 ** (age_h / _RECENCY_HALFLIFE_H)


async def build_feed(
    db: AsyncSession, user: User, limit: int, offset: int
) -> list[tuple[Post, User, str]]:
    following = await _following_ids(db, user.id)
    interest_vec, interest_tags = await _interest(db, user.id)

    # reason priority: followed > interest match > trending (first source to add a post wins)
    pool: dict[uuid.UUID, Scored] = {}
    sims: dict[uuid.UUID, float] = {}  # post_id -> cosine similarity to interest vec (ANN only)

    def add(post: Post, author: User, reason: str) -> None:
        if post.author_id == user.id or post.id in pool:
            return
        pool[post.id] = Scored(post=post, author=author, reason=reason, score=0.0)

    # 1) followed authors' recent posts
    if following:
        rows = (
            await db.execute(
                select(Post, User)
                .join(User, User.id == Post.author_id)
                .where(Post.visibility == "public", Post.author_id.in_(following))
                .order_by(Post.created_at.desc())
                .limit(_PER_RETRIEVER)
            )
        ).all()
        for p, u in rows:
            add(p, u, "Followed")

    # 2) embedding ANN over interests
    if interest_vec is not None:
        rows = (
            await db.execute(
                select(Post, User, Embedding.embedding.cosine_distance(interest_vec).label("dist"))
                .join(User, User.id == Post.author_id)
                .join(Embedding, (Embedding.owner_id == Post.id) & (Embedding.owner_type == "post"))
                .where(Post.visibility == "public", Post.author_id != user.id)
                .order_by("dist")
                .limit(_PER_RETRIEVER)
            )
        ).all()
        for p, u, dist in rows:
            sims[p.id] = 1.0 - float(dist)
            shared = sorted(set(p.tags or []) & interest_tags)
            reason = f"Popular in #{shared[0]}" if shared else "Suggested for you"
            add(p, u, reason)

    # 3) trending — recent, by engagement
    rows = (
        await db.execute(
            select(Post, User)
            .join(User, User.id == Post.author_id)
            .where(Post.visibility == "public")
            .order_by(Post.like_count.desc(), Post.created_at.desc())
            .limit(_PER_RETRIEVER)
        )
    ).all()
    for p, u in rows:
        add(p, u, "Trending")

    # ---- score ----
    for s in list(pool.values())[:_POOL]:
        p = s.post
        sim = sims.get(p.id, 0.5)
        tag_overlap = 1.0 if (set(p.tags or []) & interest_tags) else 0.4
        f = FeedFeatures(
            goal_similarity=sim,
            fitness_level_similarity=0.5,
            community_affinity=tag_overlap,
            engagement_probability=min(p.like_count / _ENGAGEMENT_NORM, 1.0),
            content_quality=0.5,
            recency=_recency(p.created_at),
            trust_score=0.5,
            affinity_to_author=1.0 if p.author_id in following else 0.0,
        )
        s.score = score(f) + random.uniform(0, 0.02)  # tiny exploration jitter

    ranked = sorted(pool.values(), key=lambda s: s.score, reverse=True)
    ranked = _diversify(ranked)
    page = ranked[offset : offset + limit]
    return [(s.post, s.author, s.reason) for s in page]


def _diversify(items: list[Scored]) -> list[Scored]:
    """Avoid two posts from the same author back-to-back (defer the dup one slot)."""
    out: list[Scored] = []
    deferred: list[Scored] = []
    for s in items:
        if out and out[-1].post.author_id == s.post.author_id:
            deferred.append(s)
        else:
            out.append(s)
    out.extend(deferred)
    return out
