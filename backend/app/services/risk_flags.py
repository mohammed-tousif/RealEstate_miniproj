"""Rule-based risk flags for a listing (BLUEPRINT R7): screening prompts for a buyer, not findings.

Each flag says what to check and why. None of them is a legal opinion or a valuation.
"""
from __future__ import annotations

import math

from pydantic import BaseModel

from app.ml import pricing
from app.ml.features import build_features
from app.models import Property
from app.models.enums import (ConversionStatus, DocumentAvailability, LandClassification, LayoutApprovalStatus,
                              PropertyType, RoadAccess)
from app.services import document_rules

Severity = str  # "high" | "medium" | "low"


class RiskFlag(BaseModel):
    code: str
    severity: str
    message: str


def _price_flag(p: Property) -> RiskFlag | None:
    from app.services.prediction_service import _record_from_property
    try:
        loaded = pricing.get_model()
    except pricing.ModelUnavailable:
        return None
    rec = _record_from_property(p)
    rec.pop("_coords_from_locality")
    v = float(loaded.model.predict(build_features([rec]))[0])
    iv = loaded.metadata["interval"]
    lo, hi = v * math.exp(iv["log_residual_low"]), v * math.exp(iv["log_residual_high"])
    price = float(p.asking_price_inr)
    if price < lo:
        return RiskFlag(code="price_below_model_range", severity="medium",
                        message="Asking price is below the demonstration price model's indicative range. An unusually "
                                "low price can point to title, access or document problems; ask why.")
    if price > hi:
        return RiskFlag(code="price_above_model_range", severity="low",
                        message="Asking price is above the demonstration price model's indicative range. Compare it "
                                "with similar listings before negotiating.")
    return None


def risk_flags(p: Property, include_price: bool = True) -> list[RiskFlag]:
    flags: list[RiskFlag] = []
    applicable = document_rules.applicable_documents(p.property_type, p.land_classification, p.conversion_status,
                                                     p.layout_approval_status)
    provided = {d.document_type for d in p.documents if d.availability == DocumentAvailability.provided}
    missing_key = [d for d in applicable if d in document_rules.KEY_DOCUMENTS and d not in provided]
    if missing_key:
        from app.models.enums import LABELS
        names = ", ".join(LABELS.get(("DocumentType", d.value), d.value) for d in missing_key)
        flags.append(RiskFlag(code="missing_key_documents", severity="high",
                              message=f"Key documents not declared as provided: {names}. Ask the seller for them "
                                      "and check them on the official portals."))
    if p.property_type != PropertyType.agricultural_land and (
            p.land_classification == LandClassification.agricultural
            or p.conversion_status in (ConversionStatus.not_converted, ConversionStatus.unknown)):
        flags.append(RiskFlag(code="conversion_not_established", severity="high",
                              message="Non-agricultural use is not established (no conversion claimed). Building or "
                                      "commercial use may not be permitted until the land is converted."))
    if p.property_type in (PropertyType.residential_plot, PropertyType.commercial_plot) and \
            p.layout_approval_status == LayoutApprovalStatus.unapproved_layout:
        flags.append(RiskFlag(code="unapproved_layout", severity="high",
                              message="The plot is in a layout described as unapproved; building permission and "
                                      "municipal services can be difficult."))
    if p.road_access == RoadAccess.no_direct_access:
        flags.append(RiskFlag(code="no_road_access", severity="high",
                              message="No direct road access is declared. Check for a recorded right of way."))
    elif p.road_access == RoadAccess.unknown:
        flags.append(RiskFlag(code="road_access_unknown", severity="medium",
                              message="Road access is not specified. Visit the site or ask the seller."))
    if include_price:
        f = _price_flag(p)
        if f:
            flags.append(f)
    if p.latitude is None:
        flags.append(RiskFlag(code="no_location", severity="low", message="No map location was provided."))
    return flags
