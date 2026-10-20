"""Feature builder shared by training (scripts/train_price_model.py) and inference
(app/ml/pricing.py), so the model always sees features computed the same way.

Only fields that genuinely exist in the data are used (BLUEPRINT Part E). The
target is the observed *asking* price, not a transaction price or a valuation.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

import pandas as pd

from app.services.geo import distance_to_city_centre_km

# Ordinal encoding of road access (higher = better access). "unknown" is NOT given
# a value: it becomes missing, is imputed with the training median, and gets its
# own indicator column so the model can tell "unknown" apart from a real value.
ROAD_ORDINAL = {"no_direct_access": 0, "unpaved": 1, "paved_internal": 2, "main_road": 3, "highway": 4}

CATEGORICAL = ["city", "locality", "property_type", "land_classification", "conversion_status",
               "layout_approval_status"]
NUMERIC = ["log_area_sqft", "road_access_ord", "road_frontage_ft", "amenity_count", "distance_to_centre_km"]
BINARY = ["is_corner_plot", "road_access_unknown", "road_frontage_missing"]
FEATURES = CATEGORICAL + NUMERIC + BINARY

FEATURE_DESCRIPTIONS = {
    "city": "City (Hubballi or Dharwad)",
    "locality": "Locality, one-hot encoded; localities with fewer than 5 training rows are grouped as 'infrequent'",
    "property_type": "Property category",
    "land_classification": "Land classification as declared by the seller",
    "conversion_status": "DC conversion status as claimed by the seller",
    "layout_approval_status": "Layout approval as claimed by the seller",
    "log_area_sqft": "Natural log of the area in sq ft (after unit conversion)",
    "road_access_ord": "Road access, ordinal 0 (no direct access) to 4 (highway); unknown is imputed",
    "road_frontage_ft": "Road frontage in feet; median-imputed when missing",
    "amenity_count": "Number of nearby amenities the seller listed",
    "distance_to_centre_km": "Straight-line km from approximate coordinates to an approximate city centre",
    "is_corner_plot": "1 if the seller marked a corner plot, else 0 (also 0 when not stated)",
    "road_access_unknown": "1 if road access is unknown",
    "road_frontage_missing": "1 if road frontage was not given",
}


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _bool(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return False
    return bool(v)


def _cat(v: Any) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "unknown"
    v = getattr(v, "value", v)  # enums
    v = str(v).strip()
    return v or "unknown"


def feature_row(rec: dict[str, Any]) -> dict[str, Any]:
    """One raw record (CSV row, API input or DB property as a dict) → one feature row.

    Required keys: city, locality, property_type, normalized_area_sqft (> 0).
    Everything else is optional and handled as missing.
    """
    area = _num(rec.get("normalized_area_sqft"))
    if area is None or area <= 0:
        raise ValueError("normalized_area_sqft must be a positive number")
    road = _cat(rec.get("road_access"))
    frontage = _num(rec.get("road_frontage_ft"))
    lat, lng = _num(rec.get("latitude")), _num(rec.get("longitude"))
    dist = distance_to_city_centre_km(_cat(rec.get("city")), lat, lng)
    return {
        "city": _cat(rec.get("city")),
        "locality": _cat(rec.get("locality")),
        "property_type": _cat(rec.get("property_type")),
        "land_classification": _cat(rec.get("land_classification")),
        "conversion_status": _cat(rec.get("conversion_status")),
        "layout_approval_status": _cat(rec.get("layout_approval_status")),
        "log_area_sqft": math.log(area),
        "road_access_ord": float(ROAD_ORDINAL[road]) if road in ROAD_ORDINAL else math.nan,
        "road_frontage_ft": frontage if frontage is not None else math.nan,
        "amenity_count": float(_num(rec.get("amenity_count")) or 0.0),
        "distance_to_centre_km": dist if dist is not None else math.nan,
        "is_corner_plot": 1.0 if _bool(rec.get("is_corner_plot")) else 0.0,
        "road_access_unknown": 0.0 if road in ROAD_ORDINAL else 1.0,
        "road_frontage_missing": 1.0 if frontage is None else 0.0,
    }


def build_features(records: Iterable[dict[str, Any]]) -> pd.DataFrame:
    rows = [feature_row(r) for r in records]
    return pd.DataFrame(rows, columns=FEATURES)


def count_amenities(amenities: Any) -> int:
    """CSV stores amenities as 'code:km;code:km'."""
    if amenities is None or (isinstance(amenities, float) and math.isnan(amenities)):
        return 0
    return len([a for a in str(amenities).split(";") if a.strip()])
