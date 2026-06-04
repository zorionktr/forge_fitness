"""Feed fan-out task (docs/06 §5): push new posts into follower feed caches (Redis)."""
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.fanout_post", bind=True)
def fanout_post(self, *, post_id: str, author_id: str) -> dict:
    """Fan-out-on-write for normal accounts; large accounts handled pull-side at read time."""
    raise NotImplementedError("Wire follower lookup + capped Redis LPUSH — docs/06 §5.")
