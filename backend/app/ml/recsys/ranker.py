"""Feed ranking (docs/07 §2). MVP: transparent weighted/GBM ranker over hydrated features."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeedFeatures:
    goal_similarity: float
    fitness_level_similarity: float
    community_affinity: float
    engagement_probability: float
    content_quality: float
    recency: float
    trust_score: float
    affinity_to_author: float


# MVP weights — replace with a trained LightGBM model on logged engagement (docs/07 §2).
_WEIGHTS = {
    "goal_similarity": 0.18,
    "fitness_level_similarity": 0.10,
    "community_affinity": 0.16,
    "engagement_probability": 0.22,
    "content_quality": 0.12,
    "recency": 0.10,
    "trust_score": 0.06,
    "affinity_to_author": 0.06,
}


def score(f: FeedFeatures) -> float:
    return sum(getattr(f, k) * w for k, w in _WEIGHTS.items())
