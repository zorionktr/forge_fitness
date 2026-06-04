# 07 — Recommendation & Feed Ranking System

Powers the personalized feed and recommendations for communities, creators, posts, workout
partners, and challenges. Designed to work at **cold start** (content-based) and improve with
behavioral signal (collaborative + learned ranking).

## 1. Recommendation surfaces

| Surface | Output | Signals |
|---|---|---|
| **Home feed** | ranked posts | goal/level/community affinity, engagement prob, quality, recency, trust, follows |
| **Communities** | join suggestions | goal/interest similarity, friends' communities, popularity |
| **Creators** | follow suggestions | content affinity, similar users follow, niche match |
| **Posts (discover)** | non-followed content | embeddings + engagement prediction |
| **Workout partners** | people | goal + level + location + schedule + persona compatibility |
| **Challenges** | join suggestions | goal alignment, social proof, difficulty fit |

## 2. Two-stage architecture (candidate generation → ranking)

```mermaid
flowchart TD
    subgraph Candidate Generation (recall, cheap, ~thousands)
      F1[Followed authors recent posts]
      F2[Joined community recent posts]
      F3[Embedding ANN: posts similar to user vector]
      F4[Trending / popular - per community]
      F5[Collaborative: liked-by-similar-users]
    end
    F1 & F2 & F3 & F4 & F5 --> POOL[Candidate pool + dedup]
    POOL --> FEAT[Feature hydration]
    FEAT --> RANK[Ranking model -> score]
    RANK --> POL[Policy layer: diversity, freshness, dedup author, safety]
    POL --> PAGE[Cursor-paginated feed]
```

### Stage 1 — Candidate generation (recall)
Cheap retrievers union into a candidate pool (~hundreds–thousands), deduped:
- **Follow/community** recent posts (from feed caches, `docs/06`).
- **Embedding ANN**: user interest vector vs post embeddings (Qdrant/pgvector).
- **Trending**: time-decayed engagement per community.
- **Collaborative**: posts liked by users similar to you (ALS/implicit MF or co-engagement).

### Stage 2 — Ranking
A learned model scores each candidate for the target user:

```
score = f(
  goal_similarity,            # user goal vs post topic/author goal
  fitness_level_similarity,   # training age / strength bucket
  community_affinity,         # membership + dwell history in topic
  engagement_probability,     # P(like|comment|share|dwell) predicted
  content_quality,            # posts.quality_score (ML)
  recency,                    # time decay
  trust_score,                # author/content trust
  affinity_to_author,         # follow + past interactions
  diversity_penalty           # avoid same-author/topic clustering
)
```

- **MVP ranker**: transparent weighted linear / gradient-boosted model (LightGBM) over the features
  above — easy to ship, debug, and explain. Reason features stored in `recommendations.reason`.
- **Scale ranker**: two-tower retrieval + a DLRM/wide-and-deep ranking network trained on logged
  impressions/engagements; multi-task heads (P(like), P(comment), P(dwell)).

### Policy layer (post-ranking)
Diversity (cap consecutive same-author/topic), freshness injection, already-seen suppression,
safety/quality floor, and a small **exploration** slot (ε-greedy / Thompson) so new content and
creators get discovered and the model keeps learning.

## 3. Feature store & signals

| Feature family | Source | Freshness |
|---|---|---|
| User profile/goal/level | `profiles`, `goals` | on change (event) |
| User interest vector | rolling embedding of engaged content | hourly batch + online updates |
| Engagement history | `likes`, `comments`, dwell events | near-real-time (Kafka) |
| Post features | `posts` (kind, media, quality, trust) | at create + recompute |
| Community affinity | membership + interaction counts | hourly |
| Graph features | follows, mutuals | on edge change |

Implemented as an offline feature table + Redis online cache. Impression and engagement logs are
the training data (closed loop).

## 4. Cold start

- **New user**: rely on conversational onboarding (goal, level, interests) → seed interest vector →
  content-based recs (communities/creators by goal) before any behavioral signal exists.
- **New post**: use author trust + content embedding + small exploration budget until it has
  engagement signal.
- **New community**: surfaced via category match + manual curation/seeding.

## 5. Workout partner & challenge matching

- **Partner**: candidate = users with overlapping goal, similar level, compatible schedule, and
  (optional) proximity; rank by complementary persona + activity overlap; respect privacy/opt-in.
- **Challenge**: match by goal alignment + difficulty fit (from current capacity) + social proof
  (friends joined). Challenges drive engagement and are a monetization surface (sponsored).

## 6. Agent ↔ recsys integration

The agent calls `recommend_content()` / `recommend_people()` (tools) so it can weave suggestions
into conversation ("Want to join *r/StrongLifts*? People with your goals are active there.") The
agent provides **explainable** reasons sourced from `recommendations.reason`.

## 7. Serving & performance

- Feed request: read precomputed candidates + cached features → rank inline (p95 < 150ms for the
  rank step) → policy → page. Heavy candidate generation runs async/precomputed where possible.
- `recommendations` table holds precomputed people/community/challenge recs (refreshed by workers,
  `expires_at` TTL); feed is computed more dynamically with cached inputs.

## 8. Evaluation

- **Offline**: NDCG/AUC on held-out engagement; counterfactual replay.
- **Online**: A/B feed CTR, dwell, session length, D7/D30 retention, downstream
  workouts/meals logged (guard against engagement-bait that doesn't improve fitness outcomes).
- **Guardrail metric**: don't optimize engagement at the expense of healthy-behavior outcomes.
