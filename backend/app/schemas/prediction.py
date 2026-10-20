"""Price-estimate request/response. Money is serialised as decimal strings."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (AreaUnit, ConversionStatus, LandClassification, LayoutApprovalStatus, PropertyType,
                              RoadAccess)
from app.schemas.property import AreaVal, Feet, Price


class PriceEstimateIn(BaseModel):
    """Either `property_id` (estimate an existing listing) or the property fields."""
    property_id: uuid.UUID | None = None
    locality_id: int | None = None
    property_type: PropertyType | None = None
    area_value: AreaVal | None = None
    area_unit: AreaUnit | None = None
    land_classification: LandClassification = LandClassification.unknown
    conversion_status: ConversionStatus = ConversionStatus.unknown
    layout_approval_status: LayoutApprovalStatus = LayoutApprovalStatus.unknown
    road_access: RoadAccess = RoadAccess.unknown
    road_frontage_ft: Feet | None = None
    is_corner_plot: bool | None = None
    amenity_count: int | None = Field(default=None, ge=0, le=50)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    asking_price_inr: Price | None = Field(default=None, description="optional: compare a quoted price")

    @model_validator(mode="after")
    def _either_id_or_fields(self):
        if self.property_id is None:
            missing = [f for f in ("locality_id", "property_type", "area_value", "area_unit")
                       if getattr(self, f) is None]
            if missing:
                raise ValueError(f"provide property_id, or all of: {', '.join(missing)}")
        return self


class PriceRange(BaseModel):
    low: Decimal
    high: Decimal
    nominal_coverage: float
    measured_test_coverage: float
    method: str


class Comparable(BaseModel):
    id: uuid.UUID
    title: str
    property_type: PropertyType
    locality: str
    city: str
    asking_price_inr: Decimal
    normalized_area_sqft: Decimal
    price_per_sqft: Decimal
    is_synthetic: bool


class FactorOut(BaseModel):
    feature: str
    description: str
    mae_increase_inr: Decimal


class ModelRef(BaseModel):
    name: str
    label: str
    version: str
    trained_on_synthetic: bool


class PriceEstimateOut(BaseModel):
    predicted_asking_price_inr: Decimal
    indicative_range_inr: PriceRange
    normalized_area_sqft: Decimal
    predicted_price_per_sqft: Decimal
    quoted_price_inr: Decimal | None = None
    quoted_vs_estimate_pct: float | None = None
    quoted_position: str | None = Field(default=None, description="below_range | within_range | above_range")
    comparables: list[Comparable]
    top_factors: list[FactorOut]
    top_factors_note: str
    model: ModelRef
    warnings: list[str]
    disclaimer: str
