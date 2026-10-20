"""Advisor (recommendation) and comparison request/response schemas."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AreaUnit, PropertyType
from app.schemas.property import AreaVal, Price, PropertySummary

Importance = Literal["very_important", "important", "somewhat", "not_important"]
Objective = Literal["build_house", "long_term_investment", "farming", "commercial_use"]
FactorName = Literal["budget", "location", "purpose", "connectivity", "documentation"]


class Preferences(BaseModel):
    """What the buyer wants. Each constraint is only a hard filter when its *_strict flag is set."""
    min_budget: Price | None = None
    max_budget: Price | None = None
    budget_strict: bool = True
    property_types: list[PropertyType] = Field(default_factory=list, max_length=5)
    types_strict: bool = True
    cities: list[Literal["Hubballi", "Dharwad"]] = Field(default_factory=list, max_length=2)
    locality_ids: list[int] = Field(default_factory=list, max_length=30)
    location_strict: bool = False
    min_area_value: AreaVal | None = None
    min_area_unit: AreaUnit = AreaUnit.sqft
    area_strict: bool = False
    objective: Objective | None = None
    importance: dict[FactorName, Importance] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _budget_order(self):
        if self.min_budget is not None and self.max_budget is not None and self.min_budget > self.max_budget:
            raise ValueError("min_budget must not be greater than max_budget")
        return self


class RecommendationRequest(Preferences):
    limit: int = Field(default=10, ge=1, le=50)


class FactorScore(BaseModel):
    factor: FactorName
    label: str
    weight: float = Field(description="share of the total score (0–1) after renormalisation")
    score: float = Field(description="0–1")
    contribution: float = Field(description="points out of 100")
    data_known: float = Field(description="share of this factor backed by real fields (0–1)")


class PriceCheck(BaseModel):
    position: Literal["below_range", "within_range", "above_range"]
    estimate_inr: Decimal
    note: str


class Recommendation(BaseModel):
    rank: int
    property: PropertySummary
    score: float
    data_coverage: float
    factors: list[FactorScore]
    reasons: list[str]
    tradeoffs: list[str]
    missing_info: list[str]
    verify_independently: list[str]
    price_check: PriceCheck | None = None


class ExcludedReason(BaseModel):
    reason: str
    count: int


class RecommendationResponse(BaseModel):
    results: list[Recommendation]
    candidates_considered: int
    matched: int
    excluded: list[ExcludedReason]
    weights_used: dict[str, float]
    factors_ignored: list[str]
    notes: list[str]
    engine_version: str
    score_label: str
    is_synthetic_data: bool


class CompareRequest(BaseModel):
    property_ids: list[uuid.UUID] = Field(min_length=2, max_length=3)
    preferences: Preferences | None = None


class CompareItem(BaseModel):
    property: PropertySummary
    match: Recommendation | None = None
    excluded_reason: str | None = None


class CompareResponse(BaseModel):
    items: list[CompareItem]
    warnings: list[str]
    engine_version: str
    score_label: str


class SimilarItem(BaseModel):
    property: PropertySummary
    distance: float
    similarities: list[str]


class SimilarResponse(BaseModel):
    items: list[SimilarItem]
    method: str
