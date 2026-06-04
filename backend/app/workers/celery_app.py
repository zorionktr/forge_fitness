"""Celery application (docs/09 §4). Workers consume Kafka/queues + run scheduled jobs."""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "forge",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.food_analyze",
        "app.workers.tasks.embeddings",
        "app.workers.tasks.fanout",
        "app.workers.tasks.notify",
        "app.workers.tasks.insights",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=5,
    task_serializer="json",
    result_expires=3600,
)

# Scheduled jobs (docs/03 §7, docs/04 §2, docs/02 §5)
celery_app.conf.beat_schedule = {
    "weekly-insights": {"task": "tasks.generate_weekly_insights", "schedule": 24 * 3600},
    "memory-decay": {"task": "tasks.decay_memories", "schedule": 24 * 3600},
    "ensure-partitions": {"task": "tasks.ensure_partitions", "schedule": 24 * 3600},
}
