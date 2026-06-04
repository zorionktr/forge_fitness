"""Scheduled agent reflections & maintenance (docs/03 §7, docs/04 §2, docs/02 §5)."""
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.generate_weekly_insights")
def generate_weekly_insights() -> dict:
    """Per active user: summarize week (lifts/weight/adherence) -> insight + memory + notification."""
    raise NotImplementedError("Wire weekly insight generation — docs/03 §7.")


@celery_app.task(name="tasks.decay_memories")
def decay_memories() -> dict:
    """Decay unused low-importance episodic memories; compact into reflections — docs/04 §2."""
    raise NotImplementedError("Wire memory decay/compaction — docs/04 §2.")


@celery_app.task(name="tasks.ensure_partitions")
def ensure_partitions() -> dict:
    """Pre-create next month's partitions; archive cold ones to S3 — docs/02 §5."""
    raise NotImplementedError("Wire pg_partman/cron partition maintenance — docs/02 §5.")
