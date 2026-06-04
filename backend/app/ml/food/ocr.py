"""Nutrition-label / ingredient OCR (docs/05 §3.1). AWS Textract primary; PaddleOCR fallback."""
from __future__ import annotations

from typing import Any


def parse_nutrition_label(s3_key: str) -> dict[str, Any]:
    """OCR a nutrition-facts panel and normalize to per-serving macros.

    Returns: {name?, serving_size, serving_unit, calories, protein_g, carbs_g, fat_g,
              fiber_g, sugar_g, sodium_mg, confidence}
    """
    raise NotImplementedError("Wire AWS Textract (tables) + unit normalization — docs/05 §3.1.")
