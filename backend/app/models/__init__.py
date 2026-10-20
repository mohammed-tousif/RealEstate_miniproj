"""SQLAlchemy ORM models (BLUEPRINT Part D)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer,
                        Numeric, String, Text, UniqueConstraint, Uuid)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow
from app.models.enums import (AmenityCategory, AreaUnit, ConversionStatus, DocumentAvailability, DocumentType,
                              IntendedLandUse, LandClassification, LayoutApprovalStatus, ListingStatus,
                              PropertyType, RoadAccess, UserRole, VerificationStatus)


def str_enum(enum_cls, name: str):
    """Portable enum column: VARCHAR + CHECK constraint, stores the .value."""
    return Enum(enum_cls, name=name, native_enum=False, create_constraint=True, length=40,
                values_callable=lambda e: [m.value for m in e], validate_strings=True)


MONEY = Numeric(14, 2)
AREA = Numeric(16, 4)
COORD = Numeric(9, 6)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    auth_provider_id: Mapped[str | None] = mapped_column(String(200))  # for a future external provider (FUT-6)
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "user_role"), default=UserRole.buyer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo_account: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    properties: Mapped[list[Property]] = relationship(back_populates="owner")


class Locality(Base):
    __tablename__ = "localities"
    __table_args__ = (UniqueConstraint("locality_name", "city", name="uq_localities_name_city"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    locality_name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(80), default="Karnataka")
    center_lat: Mapped[Decimal | None] = mapped_column(COORD)
    center_lng: Mapped[Decimal | None] = mapped_column(COORD)
    coordinates_approximate: Mapped[bool] = mapped_column(Boolean, default=True)
    is_rural: Mapped[bool] = mapped_column(Boolean, default=False)


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("asking_price_inr > 0", name="price_positive"),
        CheckConstraint("area_value > 0", name="area_positive"),
        CheckConstraint("normalized_area_sqft > 0", name="norm_area_positive"),
        CheckConstraint("latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="lat_range"),
        CheckConstraint("longitude IS NULL OR (longitude BETWEEN -180 AND 180)", name="lng_range"),
        CheckConstraint("road_frontage_ft IS NULL OR road_frontage_ft > 0", name="frontage_positive"),
        Index("ix_properties_status_type", "listing_status", "property_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    locality_id: Mapped[int] = mapped_column(ForeignKey("localities.id", ondelete="RESTRICT"), index=True)

    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    property_type: Mapped[PropertyType] = mapped_column(str_enum(PropertyType, "property_type"))
    intended_land_use: Mapped[IntendedLandUse] = mapped_column(str_enum(IntendedLandUse, "intended_land_use"),
                                                               default=IntendedLandUse.unknown)
    land_classification: Mapped[LandClassification] = mapped_column(
        str_enum(LandClassification, "land_classification"), default=LandClassification.unknown)
    conversion_status: Mapped[ConversionStatus] = mapped_column(str_enum(ConversionStatus, "conversion_status"),
                                                                default=ConversionStatus.unknown)
    layout_approval_status: Mapped[LayoutApprovalStatus] = mapped_column(
        str_enum(LayoutApprovalStatus, "layout_approval_status"), default=LayoutApprovalStatus.unknown)

    asking_price_inr: Mapped[Decimal] = mapped_column(MONEY, index=True)

    area_value: Mapped[Decimal] = mapped_column(AREA)
    area_unit: Mapped[AreaUnit] = mapped_column(str_enum(AreaUnit, "area_unit"))
    normalized_area_sqft: Mapped[Decimal] = mapped_column(AREA, index=True)
    plot_width_ft: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    plot_length_ft: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    road_frontage_ft: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    road_access: Mapped[RoadAccess] = mapped_column(str_enum(RoadAccess, "road_access"), default=RoadAccess.unknown)
    is_corner_plot: Mapped[bool | None] = mapped_column(Boolean)

    general_address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[Decimal | None] = mapped_column(COORD)
    longitude: Mapped[Decimal | None] = mapped_column(COORD)
    coordinates_approximate: Mapped[bool] = mapped_column(Boolean, default=True)

    listing_status: Mapped[ListingStatus] = mapped_column(str_enum(ListingStatus, "listing_status"),
                                                          default=ListingStatus.pending)
    review_reason: Mapped[str | None] = mapped_column(Text)  # admin's reason for reject/flag
    restriction_notes: Mapped[str | None] = mapped_column(Text)  # restrictions/uncertainties declared by seller
    additional_notes: Mapped[str | None] = mapped_column(Text)
    relevant_authorities: Mapped[str | None] = mapped_column(String(300))

    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    data_source: Mapped[str] = mapped_column(String(80), default="user_submitted")
    source_record_id: Mapped[str | None] = mapped_column(String(80))
    last_verified_on: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="properties")
    locality: Mapped[Locality] = relationship(lazy="joined")
    images: Mapped[list[PropertyImage]] = relationship(back_populates="property", cascade="all, delete-orphan",
                                                       order_by="PropertyImage.ordering")
    documents: Mapped[list[PropertyDocument]] = relationship(back_populates="property", cascade="all, delete-orphan")
    amenity_links: Mapped[list[PropertyAmenity]] = relationship(back_populates="property",
                                                                cascade="all, delete-orphan")


class PropertyImage(Base):
    __tablename__ = "property_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(40))
    ordering: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    property: Mapped[Property] = relationship(back_populates="images")


class PropertyDocument(Base):
    """A document the seller declares. `availability` says whether it was provided;
    `verification_status` says whether anyone checked it. Neither establishes clear title."""
    __tablename__ = "property_documents"
    __table_args__ = (UniqueConstraint("property_id", "document_type", name="uq_property_documents_prop_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[DocumentType] = mapped_column(str_enum(DocumentType, "document_type"))
    availability: Mapped[DocumentAvailability] = mapped_column(str_enum(DocumentAvailability, "doc_availability"),
                                                               default=DocumentAvailability.unknown)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        str_enum(VerificationStatus, "verification_status"), default=VerificationStatus.unverified)
    storage_path: Mapped[str | None] = mapped_column(String(300))  # private storage; not served publicly
    verification_notes: Mapped[str | None] = mapped_column(Text)
    applicable_authority: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    property: Mapped[Property] = relationship(back_populates="documents")


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    category: Mapped[AmenityCategory] = mapped_column(str_enum(AmenityCategory, "amenity_category"))


class PropertyAmenity(Base):
    __tablename__ = "property_amenities"

    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"),
                                                   primary_key=True)
    amenity_id: Mapped[int] = mapped_column(ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True)
    approx_distance_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    distance_is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    property: Mapped[Property] = relationship(back_populates="amenity_links")
    amenity: Mapped[Amenity] = relationship(lazy="joined")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    minimum_budget: Mapped[Decimal | None] = mapped_column(MONEY)
    maximum_budget: Mapped[Decimal | None] = mapped_column(MONEY)
    preferred_locality_ids: Mapped[list | None] = mapped_column(JSON)
    preferred_cities: Mapped[list | None] = mapped_column(JSON)
    preferred_property_types: Mapped[list | None] = mapped_column(JSON)
    objective: Mapped[str | None] = mapped_column(String(40))
    investment_horizon_years: Mapped[int | None] = mapped_column(Integer)
    other: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"),
                                                   primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    session_ref: Mapped[str | None] = mapped_column(String(80))
    input_criteria: Mapped[dict] = mapped_column(JSON)
    engine_version: Mapped[str] = mapped_column(String(40))
    result_property_ids: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(40))
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dataset_version: Mapped[str] = mapped_column(String(80))
    feature_schema: Mapped[dict] = mapped_column(JSON)
    evaluation_metrics: Mapped[dict] = mapped_column(JSON)
    trained_on_synthetic: Mapped[bool] = mapped_column(Boolean)
    artifact_path: Mapped[str] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
