"""Structure DocTR OCR text into nutrition fields with a local LLM (docs/05 §3.1).

DocTR only reads pixels → text; it has no understanding. A small **local** model (Qwen 2.5 7B
via Ollama) turns that messy OCR text into clean, per-serving macros — the "intelligence" the
old Claude-vision path provided, but on-box and free. Served by Ollama so the 7B weights live
outside the API process; the request path just makes an HTTP call.

Best-effort: any failure (Ollama down, bad JSON, model not pulled) returns None so the caller
falls back to the heuristic geometry parser.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_KEYS = (
    "name", "brand", "serving_size", "calories", "protein_g", "carbs_g",
    "fat_g", "fiber_g", "sugar_g", "sodium_mg", "ingredients",
)
_NUMERIC = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")
_STRING = ("name", "brand", "serving_size", "ingredients")

_PROMPT = """You are a nutrition-label parser. Below is raw OCR text from a photo of a food \
package (nutrition facts panel and/or ingredients list). The text may be noisy, out of order, \
or contain extra columns.

Extract the data and return ONLY a JSON object (no markdown, no prose) with exactly these keys:
{
  "name": string|null,            // product name if present, else null
  "brand": string|null,
  "serving_size": string|null,    // e.g. "2/3 cup (55 g)" or "50 g"
  "calories": number|null,        // energy PER SERVING (kcal)
  "protein_g": number|null,
  "carbs_g": number|null,         // total carbohydrate
  "fat_g": number|null,           // total fat
  "fiber_g": number|null,
  "sugar_g": number|null,         // total sugars (NOT "added sugars")
  "sodium_mg": number|null,
  "ingredients": string|null      // comma-separated, as printed
}

Rules:
- "Energy (kcal)" IS calories.
- IMPORTANT: many labels have multiple value columns (e.g. "Per 100g", "Per <serving>g", \
"Per <serving>g + milk", "%RDA"). Always use the column that matches the stated SERVING SIZE — \
NOT the "Per 100g" column and NOT any "+ milk" column. Ignore the "% Daily Value"/"%RDA" column.
- Numbers only (no units) for numeric fields. Use null for anything missing or illegible.
- For ingredients, fix obvious OCR typos (e.g. "DrvP Fruits" → "Dry Fruits").

OCR TEXT:
\"\"\"
{ocr_text}
\"\"\"
"""


def _to_number(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
    return float(m.group().replace(",", ".")) if m else None


def _to_text(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _coerce(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in _KEYS:
        v = data.get(k)
        out[k] = _to_number(v) if k in _NUMERIC else _to_text(v)
    return out


async def extract_fields_with_llm(ocr_text: str) -> dict[str, Any] | None:
    """Ask the local Qwen model to structure OCR text → nutrition dict. None on any failure."""
    if not ocr_text.strip():
        return None
    url = f"{settings.local_llm_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ocr_model,
        "prompt": _PROMPT.replace("{ocr_text}", ocr_text[:4000]),
        "stream": False,
        "format": "json",  # force valid JSON output
        "options": {"temperature": 0, "num_predict": 512},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ocr_llm_timeout_s) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            content = resp.json().get("response", "")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM did not return a JSON object")
        return _coerce(parsed)
    except Exception as exc:
        logger.warning("Local LLM (%s) OCR parse failed: %s", settings.ocr_model, exc)
        return None
