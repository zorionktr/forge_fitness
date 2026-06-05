"""Nutrition-label / ingredient OCR via DocTR + local Qwen (docs/05 §3.1).

Replaces the Claude-vision extractor with a fully on-box pipeline, in two stages:
  1. **DocTR** (detection+recognition) reads the raw text off the label photo — pixels → text.
  2. **Qwen 2.5 7B** (local, via Ollama) understands that messy text and structures it into
     per-serving macros — the "intelligence" Claude provided, but on-box and free. See
     ``llm_extract.py``.

DocTR has no understanding, so a **heuristic** parser is always computed as a safety net and
merged under the LLM result (it also covers the case where Ollama/Qwen isn't running). The
heuristic is geometry-aware: nutrition panels are tabular (label on the left, value on the
right, often emitted as *separate* DocTR lines), so it regroups words into rows by vertical
position and takes the first number to the right of each nutrient label, with a line-text
parser beneath that.

The DocTR model is heavy, so it's lazy-loaded once per process and cached (mirroring the
BGE-M3 embedder); its CPU-bound inference is offloaded to a worker thread. The Qwen call is
plain async HTTP to Ollama, so the 7B weights live outside the API process entirely.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import anyio

from app.core.config import settings
from app.ml.food.llm_extract import extract_fields_with_llm

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from doctr.models.predictor import OCRPredictor

# Numeric macro fields the geometry parser resolves (name/brand/ingredients handled separately).
_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


@lru_cache(maxsize=1)
def _get_predictor() -> "OCRPredictor":
    """Process-wide DocTR predictor singleton (loads/downloads weights on first call)."""
    from doctr.models import ocr_predictor

    logger.info("Loading DocTR OCR model (first call may download weights)…")
    return ocr_predictor(pretrained=True)


def _bbox(geometry: Any) -> tuple[float, float, float, float]:
    """Normalize a DocTR word geometry to (x0, y0, x1, y1).

    Straight pages give a ((x0,y0),(x1,y1)) rectangle; rotated pages give a 4-point polygon.
    """
    try:
        (x0, y0), (x1, y1) = geometry
        return x0, y0, x1, y1
    except (ValueError, TypeError):
        xs = [p[0] for p in geometry]
        ys = [p[1] for p in geometry]
        return min(xs), min(ys), max(xs), max(ys)


def read_document(image_bytes: bytes) -> tuple[str, list[dict[str, Any]]]:
    """Run DocTR → (newline-joined text, word list with relative bounding boxes).

    Each word dict: {text, x0, y0, x1, y1, cx, cy} where coords are in [0,1] page space.
    """
    from doctr.io import DocumentFile

    doc = DocumentFile.from_images([image_bytes])
    result = _get_predictor()(doc)

    lines_text: list[str] = []
    words: list[dict[str, Any]] = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                joined = " ".join(w.value for w in line.words).strip()
                if joined:
                    lines_text.append(joined)
                for w in line.words:
                    x0, y0, x1, y1 = _bbox(w.geometry)
                    words.append(
                        {
                            "text": w.value,
                            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                            "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0,
                        }
                    )
    return "\n".join(lines_text), words


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _group_rows(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cluster words into visual rows by vertical center, then sort each row left→right."""
    if not words:
        return []
    heights = [w["y1"] - w["y0"] for w in words]
    tol = max(sum(heights) / len(heights) * 0.6, 0.012)

    rows: list[dict[str, Any]] = []
    for w in sorted(words, key=lambda w: w["cy"]):
        for row in rows:
            if abs(row["cy"] - w["cy"]) <= tol:
                row["words"].append(w)
                row["cy"] = sum(x["cy"] for x in row["words"]) / len(row["words"])
                break
        else:
            rows.append({"cy": w["cy"], "words": [w]})
    for row in rows:
        row["words"].sort(key=lambda w: w["x0"])
        row["text"] = " ".join(w["text"] for w in row["words"])
    return rows


def _row_value(
    rows: list[dict[str, Any]],
    includes: tuple[str, ...],
    *,
    excludes: tuple[str, ...] = (),
    unit: str | None = None,
    target_x: float | None = None,
) -> float | None:
    """First number to the right of a label keyword on a matching row.

    `includes`/`excludes` match against the whole row text; the number must follow the
    label word. For unit'd fields (sodium 'mg') a value carrying the unit is preferred so the
    trailing "% Daily Value" column isn't picked up. When `target_x` is given (a multi-column
    label, e.g. "Per 100g | Per 50g"), the number nearest that column is chosen — so we read
    the per-serving column instead of just grabbing the first (per-100g) value.
    """
    for row in rows:
        low = row["text"].lower()
        if any(x in low for x in excludes):
            continue
        idx = next(
            (i for i, w in enumerate(row["words"]) if any(re.search(inc, w["text"].lower()) for inc in includes)),
            None,
        )
        if idx is None:
            continue
        nums = [(w, _to_float(m.group(1))) for w in row["words"][idx + 1:] if (m := _NUM_RE.search(w["text"]))]
        if not nums:
            # number may be glued onto the label word itself, e.g. "Calories230"
            m = _NUM_RE.search(row["words"][idx]["text"])
            if m:
                return _to_float(m.group(1))
            continue
        if unit:  # prefer a value carrying the unit (e.g. "160mg") when present
            unit_nums = [(w, v) for w, v in nums if unit in w["text"].lower()]
            if unit_nums:
                nums = unit_nums
        if target_x is not None:
            return min(nums, key=lambda nv: abs(nv[0]["cx"] - target_x))[1]
        return nums[0][1]
    return None


def _value_for(
    lines: list[str],
    includes: tuple[str, ...],
    *,
    excludes: tuple[str, ...] = (),
    unit: str | None = None,
) -> float | None:
    """Line-text fallback: first number on a line matching `includes` and no `excludes`."""
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


# (include patterns, exclude terms, unit) per macro — shared by row + line parsers.
# "calorie|energy" because many (esp. non-US) labels print "Energy (kcal)" not "Calories".
_MACROS: dict[str, tuple[tuple[str, ...], tuple[str, ...], str | None]] = {
    "calories": ((r"calorie", r"energy"), ("from fat",), None),
    "fat_g": ((r"\bfat\b",), ("saturated", "trans", "calories from fat"), None),
    "carbs_g": ((r"carbohydrate", r"\bcarb"), (), None),
    "fiber_g": ((r"fiber", r"fibre"), (), None),
    "sugar_g": ((r"sugar",), ("added",), None),  # want TOTAL sugar, not the "added sugar" row
    "protein_g": ((r"protein",), (), None),
    "sodium_mg": ((r"sodium", r"\bsalt\b"), (), "mg"),
}


def _serving_grams(serving: str | None) -> float | None:
    """Grams from a serving-size string, e.g. "2/3 cup (55 g)" → 55, "50g" → 50."""
    if not serving:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", serving, re.I)
    return float(m.group(1)) if m else None


def _serving_column_x(rows: list[dict[str, Any]], grams: float | None) -> float | None:
    """x-center of the "Per <serving>g" column on a multi-column label, else None.

    Labels like this one have Per 100g | Per 50g | Per 50g+250ml Milk | %RDA. We want the
    pure per-serving column (matching the serving grams), not per-100g or the with-milk one.
    """
    if not grams:
        return None
    gstr = str(int(grams)) if float(grams).is_integer() else str(grams)
    want = re.compile(rf"\b{re.escape(gstr)}\s*g\b", re.I)
    for row in rows:
        low = row["text"].lower()
        if "100" not in low or "per" not in low:  # only the header row has both
            continue
        cells = [
            w for w in row["words"]
            if want.search(w["text"]) and not re.search(r"100|250|ml|milk|cow|\+", w["text"], re.I)
        ]
        if cells:
            return min(cells, key=lambda w: w["x0"])["cx"]  # leftmost pure per-serving cell
    return None


def parse_document(text: str, words: list[dict[str, Any]]) -> dict[str, Any]:
    """Map OCR output to per-serving macros. Geometry-first, line-text as fallback.

    Best-effort: any field that can't be confidently read stays None for the user to fill in
    on the review screen. The raw OCR text is returned under `raw_text` for debugging/audit.
    """
    rows = _group_rows(words)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    full = " ".join(lines)

    # Serving size first — it tells us which column to read on multi-column labels.
    serving = None
    for src in (rows, [{"text": ln} for ln in lines]):
        for r in src:
            m = re.search(r"serving size\s*[:\-]?\s*(.+)", r["text"], re.I)
            if m and m.group(1).strip():
                serving = m.group(1).strip()
                break
        if serving:
            break
    out: dict[str, Any] = {"name": None, "brand": None, "serving_size": serving}

    target_x = _serving_column_x(rows, _serving_grams(serving))
    if target_x is not None:
        logger.info("Multi-column label: reading the per-serving column (x≈%.2f).", target_x)
    for field, (inc, exc, unit) in _MACROS.items():
        val = _row_value(rows, inc, excludes=exc, unit=unit, target_x=target_x)
        if val is None:
            val = _value_for(lines, inc, excludes=exc, unit=unit)
        out[field] = val

    # Ingredients: everything after the "Ingredients" keyword (capped).
    ingredients = None
    m = re.search(r"ingredients?\s*[:\-]?\s*(.+)", full, re.I)
    if m:
        ingredients = m.group(1).strip()[:600] or None
    out["ingredients"] = ingredients

    out["raw_text"] = text
    return out


# Back-compat alias for the line-only parser (used by tests / callers).
def parse_nutrition_text(text: str) -> dict[str, Any]:
    return parse_document(text, [])


async def extract_food_label(image_bytes: bytes, media_type: str) -> dict[str, Any]:
    """OCR a label photo → normalized per-serving nutrition dict. Raises on hard failure.

    Drop-in replacement for the old Claude-vision extractor: same return contract. `media_type`
    is accepted for signature compatibility but unused (DocTR decodes the bytes directly).
    """
    text, words = await anyio.to_thread.run_sync(read_document, image_bytes)
    logger.info("DocTR OCR read %d words / %d chars of text", len(words), len(text))
    if not text.strip() and not words:
        raise RuntimeError("DocTR returned no text from the image")

    # Heuristic (geometry + regex) parse is always computed as a safety net.
    heuristic = parse_document(text, words)

    # Primary: let the local LLM (Qwen) understand the OCR text. Merge field-by-field,
    # preferring the LLM but falling back to the heuristic for anything it left null.
    parsed = heuristic
    if settings.ocr_use_llm:
        llm = await extract_fields_with_llm(text)
        if llm is not None:
            merged = dict(heuristic)
            for k, v in llm.items():
                if v is not None:
                    merged[k] = v
            merged["raw_text"] = text
            parsed = merged
            logger.info("Qwen structured the label; merged with heuristic fallback.")

    logger.info(
        "Parsed label → cal=%s protein=%s carbs=%s fat=%s sodium=%s serving=%r",
        parsed.get("calories"), parsed.get("protein_g"), parsed.get("carbs_g"),
        parsed.get("fat_g"), parsed.get("sodium_mg"), parsed.get("serving_size"),
    )
    # If nothing macro-ish was found, surface what DocTR actually read so it's debuggable.
    macro_keys = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")
    if all(parsed.get(k) is None for k in macro_keys):
        logger.warning("No macros parsed from label. DocTR text was:\n%s", text[:1500])
    return parsed


def parse_nutrition_label(s3_key: str) -> dict[str, Any]:
    """Celery-path entry: OCR an already-stored image. Kept for the worker scaffold."""
    raise NotImplementedError("Wire object fetch by key, then call read_document/parse — docs/05 §3.1.")
