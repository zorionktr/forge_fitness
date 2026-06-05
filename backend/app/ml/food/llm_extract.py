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
        "keep_alive": "30m",  # keep the model resident so later scans skip the cold load
        "options": {"temperature": 0, "num_predict": 512},
    }
    # Fail fast on a genuinely unreachable Ollama, but allow a long read window: the first
    # request also loads ~5 GB of weights, and CPU generation is slow.
    timeout = httpx.Timeout(settings.ocr_llm_timeout_s, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            content = resp.json().get("response", "")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM did not return a JSON object")
        return _coerce(parsed)
    except Exception as exc:
        # str(exc) is empty for httpx timeouts — log the type so failures are diagnosable.
        logger.warning(
            "Local LLM (%s @ %s) OCR parse failed: %s",
            settings.ocr_model, settings.local_llm_base_url, repr(exc) or type(exc).__name__,
        )
        return None


async def warm_up() -> None:
    """Best-effort: load the model into Ollama at startup so the first scan isn't a cold start.

    Verifies the model is pulled and triggers a load (keep_alive keeps it resident). Logs a
    clear OK / warning so a misconfig (Ollama down, model not pulled) is visible in boot logs.
    """
    if not settings.ocr_use_llm:
        return
    base = settings.local_llm_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=5.0)) as client:
            tags = (await client.get(f"{base}/api/tags")).json().get("models", [])
            names = {m.get("name", "") for m in tags}
            if not any(n == settings.ocr_model or n.startswith(settings.ocr_model) for n in names):
                logger.warning(
                    "Ollama reachable at %s but model %r is not pulled (have: %s). "
                    "Run: ollama pull %s",
                    base, settings.ocr_model, sorted(names) or "none", settings.ocr_model,
                )
                return
            # Empty prompt just loads the model; keep_alive holds it in memory.
            await client.post(
                f"{base}/api/generate",
                json={"model": settings.ocr_model, "prompt": "", "stream": False, "keep_alive": "30m"},
            )
        logger.info("Ollama OK: model %s loaded and warm at %s.", settings.ocr_model, base)
    except Exception as exc:
        logger.warning(
            "Ollama warm-up failed (%s @ %s): %s — scans will fall back to the heuristic parser.",
            settings.ocr_model, base, repr(exc) or type(exc).__name__,
        )
