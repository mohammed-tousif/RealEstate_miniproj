"""Request/response schemas for properties. Money and area are Decimals and
serialise as strings in JSON so no precision is lost."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (AreaUnit, ConversionStatus, DocumentAvailability, DocumentType, IntendedLandUse,
                              LandClassification, LayoutApprovalStatus, ListingStatus, PropertyType, RoadAccess,
                              VerificationStatus)

Price = Annotated[Decimal, Field(gt=0, le=Decimal("99999999999.99"), max_digits=14, decimal_places=2)]
AreaVal = Annotated[Decimal, Field(gt=0, le=Decimal("999999999"), max_digits=16, decimal_places=4)]
Feet = Annotated[Decimal, Field(gt=0, le=Decimal("100000"), max_digits=10, decimal_places=2)]


class LocalityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    locality_name: str
    city: str
    district: str
    state: str
    center_lat: Decimal | None = None
    center_lng: Decimal | None = None
    coordinates_approximate: bool


class DocumentIn(BaseModel):
    document_type: DocumentType
    availability: DocumentAvailability
    applicable_authority: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)


class DocumentOut(BaseModel):
    document_type: DocumentType
    label: str
    applicable: bool
    availability: DocumentAvailability
    verification_status: VerificationStatus
    display_status: str
    display_label: str
    applicable_authority: str | None = None
    guidance: str


class AmenityOut(BaseModel):
    code: str
    label: str
    category: str
    approx_distance_km: Decimal | None = None
    distance_is_synthetic: bool = False


class ImageOut(BaseModel):
    id: int
    url: str
    ordering: int


class _PropertyFields(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(default="", max_length=5000)
    property_type: PropertyType
    intended_land_use: IntendedLandUse = IntendedLandUse.unknown
    land_classification: LandClassification = LandClassification.unknown
    conversion_status: ConversionStatus = ConversionStatus.unknown
    layout_approval_status: LayoutApprovalStatus = LayoutApprovalStatus.unknown
    asking_price_inr: Price
    area_value: AreaVal
    area_unit: AreaUnit
    plot_width_ft: Feet | None = None
    plot_length_ft: Feet | None = None
    road_frontage_ft: Feet | None = None
    road_access: RoadAccess = RoadAccess.unknown
    is_corner_plot: bool | None = None
    locality_id: int = Field(gt=0)
    general_address: str | None = Field(default=None, max_length=300)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    restriction_notes: str | None = Field(default=None, max_length=2000)
    additional_notes: str | None = Field(default=None, max_length=2000)
    relevant_authorities: str | None = Field(default=None, max_length=300)
    amenities: list[str] = Field(default_factory=list, max_length=30)
    documents: list[DocumentIn] = Field(default_factory=list, max_length=len(DocumentType))

    @field_validator("title", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _check(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        types = [d.document_type for d in self.documents]
        if len(types) != len(set(types)):
            raise ValueError("each document type may appear only once")
        return self


class PropertyCreate(_PropertyFields):
    consent_to_store: bool = Field(description="Seller confirms consent to store and publish this information")

    @field_validator("consent_to_store")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("consent is required to submit a listing")
        return v


class PropertyUpdate(BaseModel):
    """Partial update; same validation rules as create for each provided field."""
    title: str | None = Field(default=None, min_length=5, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    property_type: PropertyType | None = None
    intended_land_use: IntendedLandUse | None = None
    land_classification: LandClassification | None = None
    conversion_status: ConversionStatus | None = None
    layout_approval_status: LayoutApprovalStatus | None = None
    asking_price_inr: Price | None = None
    area_value: AreaVal | None = None
    area_unit: AreaUnit | None = None
    plot_width_ft: Feet | None = None
    plot_length_ft: Feet | None = None
    road_frontage_ft: Feet | None = None
    road_access: RoadAccess | None = None
    is_corner_plot: bool | None = None
    locality_id: int | None = Field(default=None, gt=0)
    general_address: str | None = Field(default=None, max_length=300)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    restriction_notes: str | None = Field(default=None, max_length=2000)
    additional_notes: str | None = Field(default=None, max_length=2000)
    relevant_authorities: str | None = Field(default=None, max_length=300)
    amenities: list[str] | None = Field(default=None, max_length=30)


class DocumentsUpdate(BaseModel):
    documents: list[DocumentIn] = Field(max_length=len(DocumentType))


class AdminDocumentVerification(BaseModel):
    document_type: DocumentType
    verification_status: VerificationStatus
    verification_reference: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=1000)


class RiskFlagOut(BaseModel):
    code: str
    severity: str = Field(description="high | medium | low")
    message: str


class PropertySummary(BaseModel):
    id: uuid.UUID
    title: str
    property_type: PropertyType
    land_classification: LandClassification
    intended_land_use: IntendedLandUse
    asking_price_inr: Decimal
    area_value: Decimal
    area_unit: AreaUnit
    normalized_area_sqft: Decimal
    price_per_sqft_inr: Decimal
    road_access: RoadAccess
    locality: LocalityOut
    latitude: Decimal | None
    longitude: Decimal | None
    listing_status: ListingStatus
    documentation_completeness: float
    documents_provided: int
    documents_applicable: int
    cover_image_url: str | None
    is_synthetic: bool
    created_at: datetime


class PropertyDetail(PropertySummary):
    description: str
    conversion_status: ConversionStatus
    layout_approval_status: LayoutApprovalStatus
    plot_width_ft: Decimal | None
    plot_length_ft: Decimal | None
    road_frontage_ft: Decimal | None
    is_corner_plot: bool | None
    general_address: str | None
    coordinates_approximate: bool
    restriction_notes: str | None
    additional_notes: str | None
    relevant_authorities: str | None
    data_source: str
    last_verified_on: date | None
    updated_at: datetime
    images: list[ImageOut]
    documents: list[DocumentOut]
    amenities: list[AmenityOut]
    distance_to_city_centre_km: float | None
    data_warnings: list[str]
    risk_flags: list["RiskFlagOut"] = []
    is_owner: bool
    review_reason: str | None = None  # visible to owner/admin only


class Page(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PropertyListResponse(Page):
    items: list[PropertySummary]
    applied_filters: dict
