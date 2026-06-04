"""Notification delivery task (docs/06 §8): persist + push via APNs/FCM, respect prefs/quiet hours."""
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.notify", bind=True, max_retries=3)
def notify(self, *, user_id: str, type: str, payload: dict) -> dict:
    raise NotImplementedError("Wire notifications insert + push provider — docs/06 §8.")
