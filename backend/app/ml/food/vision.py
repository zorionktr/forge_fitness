"""Nutrition-label OCR + extraction via Claude vision (docs/05 §3.1-3.2).

MVP: send the label photo to a vision LLM and get back strict JSON (per-serving macros +
ingredients). Scale path: AWS Textract / in-house CV, but a vision LLM handles messy
real-world labels well and needs no extra infra.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_PROMPT = """You are a nutrition-label OCR engine. Read the photo of a food package
(nutrition facts panel and/or ingredients list) and extract the data.

Return ONLY a JSON object (no markdown, no prose) with exactly these keys:
{
  "name": string|null,            // product name if visible, else null
  "brand": string|null,
  "serving_size": string|null,    // e.g. "1 cup (240 ml)" or "30 g"
  "calories": number|null,        // per serving (kcal)
  "protein_g": number|null,
  "carbs_g": number|null,
  "fat_g": number|null,
  "fiber_g": number|null,
  "sugar_g": number|null,
  "sodium_mg": number|null,
  "ingredients": string|null      // comma-separated ingredients list as printed
}
Use per-serving values. If a field is not legible/present, use null. Numbers only (no units) for numeric fields."""

_FIELDS = (
    "name", "brand", "serving_size", "calories", "protein_g", "carbs_g",
    "fat_g", "fiber_g", "sugar_g", "sodium_mg", "ingredients",
)


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):  # strip ```json fences if present
        text = text.split("```", 2)[1].removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in vision response")
    data = json.loads(text[start : end + 1])
    return {k: data.get(k) for k in _FIELDS}


async def extract_food_label(image_bytes: bytes, media_type: str) -> dict[str, Any]:
    """OCR a label photo → normalized per-serving nutrition dict. Raises on hard failure."""
    if not settings.anthropic_api_key:
        raise RuntimeError("no LLM API key configured for vision OCR")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    resp = await client.messages.create(
        model=settings.model_chat,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return _parse_json(text)
