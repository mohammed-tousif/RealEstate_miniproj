"""Price estimates for the API: input resolution, warnings, comparables (BLUEPRINT Part E)."""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.ml import pricing
from app.ml.features import FEATURE_DESCRIPTIONS
from app.models import Locality, Property, User
from app.models.enums import ListingStatus
from app.schemas.prediction import (Comparable, FactorOut, ModelRef, PriceEstimateIn, PriceEstimateOut,
                                    PriceRange)
from app.services import property_service as ps
from app.services.area_units import to_sqft

DISCLAIMER = ("Indicative estimate of an asking price from a demonstration model. It is not a valuation, "
              "not legal or financial advice, and must not be used to set or judge a real price.")
SYNTHETIC_WARNING = "Demonstration model trained on synthetic data. Not a valuation."
TWO = Decimal("0.01")


def _money(v: float) -> Decimal:
    step = 1000 if v >= 1e6 else 100
    return Decimal(int(round(v / step) * step)).quantize(TWO)


def _record_from_property(p: Property) -> dict:
    lat, lng = p.latitude, p.longitude
    return {
        "city": p.locality.city, "locality": p.locality.locality_name, "property_type": p.property_type.value,
        "land_classification": p.land_classification.value, "conversion_status": p.conversion_status.value,
        "layout_approval_status": p.layout_approval_status.value, "road_access": p.road_access.value,
        "normalized_area_sqft": float(p.normalized_area_sqft),
        "road_frontage_ft": float(p.road_frontage_ft) if p.road_frontage_ft is not None else None,
        "is_corner_plot": p.is_corner_plot, "amenity_count": len(p.amenity_links),
        "latitude": float(lat if lat is not None else p.locality.center_lat),
        "longitude": float(lng if lng is not None else p.locality.center_lng),
        "_coords_from_locality": lat is None,
    }


def _record_from_fields(db: Session, body: PriceEstimateIn) -> dict:
    loc = db.get(Locality, body.locality_id)
    if loc is None:
        raise AppError(422, "validation_error", "Unknown locality",
                       [{"field": "locality_id", "issue": "no such locality"}])
    try:
        sqft = to_sqft(body.area_value, body.area_unit)
    except ValueError as e:
        raise AppError(422, "validation_error", str(e), [{"field": "area_value", "issue": str(e)}])
    use_loc = body.latitude is None or body.longitude is None
    return {
        "city": loc.city, "locality": loc.locality_name, "property_type": body.property_type.value,
        "land_classification": body.land_classification.value, "conversion_status": body.conversion_status.value,
        "layout_approval_status": body.layout_approval_status.value, "road_access": body.road_access.value,
        "normalized_area_sqft": float(sqft),
        "road_frontage_ft": float(body.road_frontage_ft) if body.road_frontage_ft is not None else None,
        "is_corner_plot": body.is_corner_plot, "amenity_count": body.amenity_count,
        "latitude": float(loc.center_lat if use_loc else body.latitude),
        "longitude": float(loc.center_lng if use_loc else body.longitude),
        "_coords_from_locality": use_loc,
    }


def comparables(db: Session, record: dict, exclude_id=None, limit: int = 5) -> list[Comparable]:
    """Approved listings of the same type in the same city with area within 0.5×–2×,
    same locality first, then closest in area. Asking prices, not sale prices."""
    area = record["normalized_area_sqft"]
    rows = db.execute(
        select(Property).join(Property.locality)
        .where(Property.listing_status == ListingStatus.approved,
               Property.property_type == record["property_type"], Locality.city == record["city"],
               Property.normalized_area_sqft >= Decimal(str(area * 0.5)),
               Property.normalized_area_sqft <= Decimal(str(area * 2.0)))
    ).scalars().all()
    rows = [p for p in rows if p.id != exclude_id]
    rows.sort(key=lambda p: (p.locality.locality_name != record["locality"],
                             abs(math.log(float(p.normalized_area_sqft) / area))))
    return [Comparable(id=p.id, title=p.title, property_type=p.property_type, locality=p.locality.locality_name,
                       city=p.locality.city, asking_price_inr=p.asking_price_inr,
                       normalized_area_sqft=p.normalized_area_sqft,
                       price_per_sqft=(Decimal(p.asking_price_inr) / Decimal(p.normalized_area_sqft)).quantize(
                           TWO, rounding=ROUND_HALF_UP),
                       is_synthetic=p.is_synthetic) for p in rows[:limit]]


def estimate_price(db: Session, body: PriceEstimateIn, user: User | None) -> PriceEstimateOut:
    try:
        loaded = pricing.get_model()
    except pricing.ModelUnavailable as e:
        raise AppError(503, "model_unavailable", str(e))
    meta = loaded.metadata

    quoted, exclude_id, extra_warnings = body.asking_price_inr, None, []
    if body.property_id is not None:
        prop = ps.get_visible_property(db, body.property_id, user)
        record = _record_from_property(prop)
        quoted = quoted or prop.asking_price_inr
        exclude_id = prop.id
        if prop.source_record_id and prop.is_synthetic:
            extra_warnings.append("This synthetic listing may have been part of the model's training data, "
                                  "so the estimate can look closer to the asking price than it would for a new listing.")
    else:
        record = _record_from_fields(db, body)

    est = pricing.estimate(loaded, record)
    warnings = ([SYNTHETIC_WARNING] if meta.get("trained_on_synthetic") else []) \
        + pricing.input_warnings(meta, record) + extra_warnings
    if record.pop("_coords_from_locality"):
        warnings.append("No coordinates given; the locality's approximate centre was used for distance.")

    quoted_pct = position = None
    if quoted is not None:
        q = float(quoted)
        quoted_pct = round((q - est.value) / est.value * 100, 1)
        position = "below_range" if q < est.low else "above_range" if q > est.high else "within_range"

    sqft = Decimal(str(record["normalized_area_sqft"])).quantize(Decimal("0.0001"))
    value = _money(est.value)
    iv = meta["interval"]
    return PriceEstimateOut(
        predicted_asking_price_inr=value,
        indicative_range_inr=PriceRange(low=_money(est.low), high=_money(est.high), nominal_coverage=iv["nominal"],
                                        measured_test_coverage=round(iv["measured_test_coverage"], 3),
                                        method=iv["method"]),
        normalized_area_sqft=sqft,
        predicted_price_per_sqft=(value / sqft).quantize(TWO, rounding=ROUND_HALF_UP),
        quoted_price_inr=Decimal(quoted).quantize(TWO) if quoted is not None else None,
        quoted_vs_estimate_pct=quoted_pct, quoted_position=position,
        comparables=comparables(db, record, exclude_id),
        top_factors=[FactorOut(feature=f["feature"], description=FEATURE_DESCRIPTIONS.get(f["feature"], f["feature"]),
                               mae_increase_inr=Decimal(str(round(f["mae_increase_inr"]))))
                     for f in meta["permutation_importance"][:5] if f["mae_increase_inr"] > 0],
        top_factors_note=("Features that matter most to the model overall (permutation importance on the test "
                          "set). They are not specific to this property."),
        model=ModelRef(name=meta["model_name"], label=meta["model_label"], version=meta["model_version"],
                       trained_on_synthetic=meta["trained_on_synthetic"]),
        warnings=warnings,
        disclaimer=DISCLAIMER,
    )


def model_info() -> dict:
    try:
        meta = pricing.get_model().metadata
    except pricing.ModelUnavailable as e:
        return {"price_model": None, "message": str(e)}
    keep = ("model_name", "model_label", "model_version", "trained_at", "target", "trained_on_synthetic", "seed",
            "tuned", "dataset", "split", "selection", "validation_metrics", "test_metrics", "tuning", "interval",
            "error_by_property_type", "locality_holdout", "permutation_importance", "library_versions", "caveat")
    info = {k: meta[k] for k in keep if k in meta}
    info["features"] = [{"name": f, "description": meta["feature_schema"]["descriptions"].get(f, f)}
                        for f in meta["feature_schema"]["features"]]
    return {"price_model": info, "message": None}
