"""Async food-image analysis task (docs/05).

Orchestrates: OCR / vision -> nutrition parse -> food matching -> candidate log. Each step is a
pluggable component under app/ml/food/. This is the scaffold wiring.
"""
from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.analyze_food", bind=True, max_retries=3)
def analyze_food(self, *, s3_key: str, user_id: str, input_type: str = "meal_photo") -> dict:
    """Returns structured nutrition + confidence; result delivered to client via WS/poll.

    input_type: barcode | label_image | ingredient_image | meal_photo | text
    """
    from app.ml.food import matcher, ocr, vision  # local import keeps worker import light

    try:
        if input_type == "barcode":
            parsed = matcher.lookup_barcode(s3_key)  # s3_key carries the code for this path
        elif input_type in ("label_image", "ingredient_image"):
            parsed = ocr.parse_nutrition_label(s3_key)
        else:  # meal_photo
            parsed = vision.analyze_meal(s3_key)

        result = matcher.match_and_stage(user_id=user_id, parsed=parsed, image_s3_key=s3_key)
        # emit food.logged on confirm (done by API), enqueue embedding for any new food.
        return result
    except Exception as exc:  # pragma: no cover - scaffold
        raise self.retry(exc=exc, countdown=2**self.request.retries)
