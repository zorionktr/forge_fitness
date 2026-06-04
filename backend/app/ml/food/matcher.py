"""Food matching engine (docs/05 §3.5): barcode -> lexical(trigram) -> semantic -> create."""
from __future__ import annotations

from typing import Any


def lookup_barcode(code: str) -> dict[str, Any]:
    """Resolve a GTIN/UPC/EAN against `foods`, then OpenFoodFacts/USDA; cache 24h."""
    raise NotImplementedError("Wire barcode lookup + external nutrition DBs — docs/05 §3.5.")


def match_and_stage(*, user_id: str, parsed: dict[str, Any], image_s3_key: str | None) -> dict[str, Any]:
    """Resolve parsed nutrition to a canonical `foods` row (or create one), then stage a candidate
    UserFoodLog with macro snapshot + confidence for user confirmation (docs/05 §4)."""
    raise NotImplementedError("Wire trigram + embedding match + foods upsert — docs/05 §3.5.")
