"""Nutrition-label / ingredient OCR via DocTR (docs/05 §3.1).

Replaces the Claude-vision extractor with a fully on-box pipeline: a local **DocTR**
detection+recognition model reads the raw text off the label photo, and a heuristic
parser maps that text to per-serving macros. No LLM call, no API key, no per-request cost.

The model is heavy, so it's lazy-loaded once per process and cached (mirroring the BGE-M3
embedder). OCR inference is CPU-bound and synchronous, so the request-path wrapper offloads
it to a worker thread to avoid stalling the event loop.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import anyio

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from doctr.models.predictor import OCRPredictor

# Fields the route/schema expects (same contract the Claude extractor returned).
_FIELDS = (
    "name", "brand", "serving_size", "calories", "protein_g", "carbs_g",
    "fat_g", "fiber_g", "sugar_g", "sodium_mg", "ingredients",
)

_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


@lru_cache(maxsize=1)
def _get_predictor() -> "OCRPredictor":
    """Process-wide DocTR predictor singleton (loads/downloads weights on first call)."""
    from doctr.models import ocr_predictor

    logger.info("Loading DocTR OCR model (first call may download weights)…")
    return ocr_predictor(pretrained=True)


def read_text(image_bytes: bytes) -> str:
    """Run DocTR on an image and return its text as newline-separated lines (top→bottom)."""
    from doctr.io import DocumentFile

    doc = DocumentFile.from_images([image_bytes])
    result = _get_predictor()(doc)
    lines: list[str] = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                words = " ".join(w.value for w in line.words).strip()
                if words:
                    lines.append(words)
    return "\n".join(lines)


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _value_for(
    lines: list[str],
    includes: tuple[str, ...],
    *,
    excludes: tuple[str, ...] = (),
    unit: str | None = None,
) -> float | None:
    """First numeric value on a line that matches any `includes` regex and no `excludes` term.

    For unit'd fields (e.g. sodium 'mg') prefer the number immediately before the unit so a
    trailing "% Daily Value" column isn't picked up by mistake.
    """
    for ln in lines:
        low = ln.lower()
        if any(x in low for x in excludes):
            continue
        if not any(re.search(inc, low) for inc in includes):
            continue
        if unit:
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*" + unit, low)
            if m:
                return _to_float(m.group(1))
        m = _NUM_RE.search(low)
        if m:
            return _to_float(m.group(1))
    return None


def _first_line_value(lines: list[str], includes: tuple[str, ...]) -> str | None:
    """Text that follows the label on a matching line (used for serving size)."""
    for ln in lines:
        for inc in includes:
            m = re.search(inc + r"\s*[:\-]?\s*(.+)", ln, re.I)
            if m and m.group(1).strip():
                return m.group(1).strip()
    return None


def parse_nutrition_text(text: str) -> dict[str, Any]:
    """Heuristically map raw OCR text from a nutrition-facts panel to per-serving macros.

    Best-effort: any field that can't be confidently read stays None for the user to fill in
    on the review screen. The raw OCR text is returned under `raw_text` for debugging/audit.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    full = " ".join(lines)

    calories = _value_for(lines, (r"calorie",), excludes=("from fat",))
    fat = _value_for(lines, (r"\bfat\b",), excludes=("saturated", "trans", "calories from fat"))
    carbs = _value_for(lines, (r"carbohydrate", r"\bcarb"))
    fiber = _value_for(lines, (r"fiber", r"fibre"))
    sugar = _value_for(lines, (r"sugar",))
    protein = _value_for(lines, (r"protein",))
    sodium = _value_for(lines, (r"sodium", r"\bsalt\b"), unit="mg")

    serving_size = _first_line_value(lines, (r"serving size", r"per serving"))

    ingredients: str | None = None
    m = re.search(r"ingredients?\s*[:\-]?\s*(.+)", full, re.I)
    if m:
        ingredients = m.group(1).strip()[:600] or None

    return {
        "name": None,            # not reliably inferable from OCR — user names it on review
        "brand": None,
        "serving_size": serving_size,
        "calories": calories,
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
        "fiber_g": fiber,
        "sugar_g": sugar,
        "sodium_mg": sodium,
        "ingredients": ingredients,
        "raw_text": text,
    }


async def extract_food_label(image_bytes: bytes, media_type: str) -> dict[str, Any]:
    """OCR a label photo → normalized per-serving nutrition dict. Raises on hard failure.

    Drop-in replacement for the old Claude-vision extractor: same return contract. `media_type`
    is accepted for signature compatibility but unused (DocTR decodes the bytes directly).
    """
    text = await anyio.to_thread.run_sync(read_text, image_bytes)
    if not text.strip():
        raise RuntimeError("DocTR returned no text from the image")
    return parse_nutrition_text(text)


def parse_nutrition_label(s3_key: str) -> dict[str, Any]:
    """Celery-path entry: OCR an already-stored image. Kept for the worker scaffold."""
    raise NotImplementedError("Wire object fetch by key, then call read_text/parse — docs/05 §3.1.")
