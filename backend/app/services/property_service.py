"""Listing business rules: visibility, ownership, validation beyond field types,
search/filter/sort/paginate, document declarations and admin review."""
from __future__ import annotations

import math
import uuid
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError, bad_request, forbidden, not_found
from app.models import Amenity, Locality, Property, PropertyAmenity, PropertyDocument, User
from app.models.enums import (ConversionStatus, DocumentAvailability, DocumentType, IntendedLandUse,
                              LandClassification, LayoutApprovalStatus, ListingStatus, PropertyType, RoadAccess,
                              UserRole, VerificationStatus)
from app.schemas.property import (AmenityOut, DocumentIn, DocumentOut, ImageOut, LocalityOut, PropertyCreate,
                                  PropertyDetail, PropertyListResponse, PropertySummary, PropertyUpdate)
from app.services import document_rules
from app.services.area_units import to_sqft
from app.services.geo import distance_to_city_centre_km
from app.services.risk_flags import risk_flags


class SortOption(str, Enum):
    price_asc = "price_asc"
    price_desc = "price_desc"
    area_asc = "area_asc"
    area_desc = "area_desc"
    newest = "newest"
    oldest = "oldest"


class PropertyFilters(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, gt=0)
    city: str | None = Field(default=None, max_length=80)
    locality_id: int | None = None
    property_type: list[PropertyType] | None = None
    land_classification: list[LandClassification] | None = None
    intended_land_use: list[IntendedLandUse] | None = None
    layout_approval_status: list[LayoutApprovalStatus] | None = None
    conversion_status: list[ConversionStatus] | None = None
    road_access: list[RoadAccess] | None = None
    has_document: list[DocumentType] | None = None
    min_area_sqft: Decimal | None = Field(default=None, ge=0)
    max_area_sqft: Decimal | None = Field(default=None, gt=0)
    is_synthetic: bool | None = None
    status: ListingStatus | None = None  # admins only (owners via mine=true)
    mine: bool = False
    sort: SortOption = SortOption.newest
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=50)


# ---------------------------------------------------------------- visibility

def is_admin(user: User | None) -> bool:
    return user is not None and user.role == UserRole.admin


def can_view(prop: Property, user: User | None) -> bool:
    if prop.listing_status == ListingStatus.approved:
        return True
    return user is not None and (is_admin(user) or prop.owner_id == user.id)


def can_modify(prop: Property, user: User) -> bool:
    return is_admin(user) or prop.owner_id == user.id


def _with_children(stmt: Select) -> Select:
    return stmt.options(selectinload(Property.images), selectinload(Property.documents),
                        selectinload(Property.amenity_links).joinedload(PropertyAmenity.amenity))


def load_property(db: Session, property_id: uuid.UUID) -> Property | None:
    return db.execute(_with_children(select(Property).where(Property.id == property_id))).scalar_one_or_none()


def get_visible_property(db: Session, property_id: uuid.UUID, user: User | None) -> Property:
    prop = load_property(db, property_id)
    if prop is None or not can_view(prop, user):
        raise not_found("Property")  # 404 (not 403) so hidden listings are not revealed
    return prop


# ---------------------------------------------------------------- serialisation

def media_url(storage_path: str) -> str:
    return f"/media/{storage_path}"


def _price_per_sqft(p: Property) -> Decimal:
    return (Decimal(p.asking_price_inr) / Decimal(p.normalized_area_sqft)).quantize(Decimal("0.01"),
                                                                                  rounding=ROUND_HALF_UP)


def document_view(p: Property) -> tuple[list[DocumentOut], float, int, int]:
    applicable = document_rules.applicable_documents(p.property_type, p.land_classification, p.conversion_status,
                                                     p.layout_approval_status)
    by_type = {d.document_type: d for d in p.documents}
    provided = [t for t, d in by_type.items() if d.availability == DocumentAvailability.provided and t in applicable]
    labels = DocumentType.labels()
    out: list[DocumentOut] = []
    for t in DocumentType:
        d = by_type.get(t)
        is_applicable = t in applicable
        if d is None and not is_applicable:
            continue
        availability = d.availability if d else DocumentAvailability.unknown
        verification = d.verification_status if d else VerificationStatus.unverified
        if not is_applicable and d is not None and availability != DocumentAvailability.provided:
            availability, verification = DocumentAvailability.not_applicable, VerificationStatus.not_applicable
        status = document_rules.display_status(availability, verification)
        out.append(DocumentOut(document_type=t, label=labels[t.value], applicable=is_applicable,
                               availability=availability, verification_status=verification,
                               display_status=status, display_label=document_rules.DISPLAY_LABELS[status],
                               applicable_authority=d.applicable_authority if d else None,
                               guidance=document_rules.DOCUMENT_GUIDANCE[t]))
    return out, document_rules.completeness(applicable, provided), len(provided), len(applicable)


def summary(p: Property, docs: tuple | None = None) -> PropertySummary:
    _, comp, n_prov, n_app = docs or document_view(p)
    cover = media_url(p.images[0].storage_path) if p.images else None
    return PropertySummary(
        id=p.id, title=p.title, property_type=p.property_type, land_classification=p.land_classification,
        intended_land_use=p.intended_land_use, asking_price_inr=p.asking_price_inr, area_value=p.area_value,
        area_unit=p.area_unit, normalized_area_sqft=p.normalized_area_sqft, price_per_sqft_inr=_price_per_sqft(p),
        road_access=p.road_access, locality=LocalityOut.model_validate(p.locality), latitude=p.latitude,
        longitude=p.longitude, listing_status=p.listing_status, documentation_completeness=comp,
        documents_provided=n_prov, documents_applicable=n_app, cover_image_url=cover, is_synthetic=p.is_synthetic,
        created_at=p.created_at)


def consistency_warnings(p: Property) -> list[str]:
    """Data-quality observations shown to users and admins. Screening aids only."""
    w: list[str] = []
    if p.property_type == PropertyType.agricultural_land and p.land_classification in (
            LandClassification.non_agricultural_residential, LandClassification.non_agricultural_commercial):
        w.append("Listed as agricultural land but the land classification says non-agricultural.")
    if p.property_type in (PropertyType.residential_plot, PropertyType.independent_house) and \
            p.land_classification == LandClassification.agricultural:
        w.append("Residential listing on land classified as agricultural: conversion status needs checking.")
    if p.property_type != PropertyType.agricultural_land and p.conversion_status in (
            ConversionStatus.unknown, ConversionStatus.not_converted):
        w.append("Conversion (non-agricultural use) status is not established for a non-agricultural listing.")
    if p.plot_width_ft and p.plot_length_ft:
        dims = Decimal(p.plot_width_ft) * Decimal(p.plot_length_ft)
        if abs(dims - Decimal(p.normalized_area_sqft)) / Decimal(p.normalized_area_sqft) > Decimal("0.10"):
            w.append(f"Plot dimensions ({p.plot_width_ft} × {p.plot_length_ft} ft) do not match the stated area.")
    if p.road_access == RoadAccess.unknown:
        w.append("Road access is not specified.")
    if p.latitude is None:
        w.append("No map location provided.")
    elif p.coordinates_approximate:
        w.append("Map location is approximate.")
    return w


def detail(p: Property, user: User | None) -> PropertyDetail:
    docs = document_view(p)
    base = summary(p, docs).model_dump()
    privileged = user is not None and can_modify(p, user)
    return PropertyDetail(
        **base, description=p.description, conversion_status=p.conversion_status,
        layout_approval_status=p.layout_approval_status, plot_width_ft=p.plot_width_ft,
        plot_length_ft=p.plot_length_ft, road_frontage_ft=p.road_frontage_ft, is_corner_plot=p.is_corner_plot,
        general_address=p.general_address, coordinates_approximate=p.coordinates_approximate,
        restriction_notes=p.restriction_notes, additional_notes=p.additional_notes,
        relevant_authorities=p.relevant_authorities, data_source=p.data_source,
        last_verified_on=p.last_verified_on, updated_at=p.updated_at,
        images=[ImageOut(id=i.id, url=media_url(i.storage_path), ordering=i.ordering) for i in p.images],
        documents=docs[0],
        amenities=[AmenityOut(code=a.amenity.code, label=a.amenity.label, category=a.amenity.category.value,
                              approx_distance_km=a.approx_distance_km, distance_is_synthetic=a.distance_is_synthetic)
                   for a in p.amenity_links],
        distance_to_city_centre_km=distance_to_city_centre_km(p.locality.city, p.latitude, p.longitude),
        data_warnings=consistency_warnings(p),
        risk_flags=[f.model_dump() for f in risk_flags(p)], is_owner=user is not None and p.owner_id == user.id,
        review_reason=p.review_reason if privileged else None)


# ---------------------------------------------------------------- search

def list_properties(db: Session, user: User | None, f: PropertyFilters) -> PropertyListResponse:
    stmt = select(Property).join(Locality, Property.locality_id == Locality.id)

    if f.mine:
        if user is None:
            raise AppError(401, "not_authenticated", "Sign in to see your listings")
        stmt = stmt.where(Property.owner_id == user.id)
        stmt = stmt.where(Property.listing_status == f.status) if f.status else \
            stmt.where(Property.listing_status != ListingStatus.archived)
    elif f.status and f.status != ListingStatus.approved:
        if not is_admin(user):
            raise forbidden("Only administrators can browse listings by review status")
        stmt = stmt.where(Property.listing_status == f.status)
    else:
        stmt = stmt.where(Property.listing_status == ListingStatus.approved)

    if f.min_price is not None and f.max_price is not None and f.min_price > f.max_price:
        raise bad_request("min_price cannot be greater than max_price", "min_price")
    if f.min_area_sqft is not None and f.max_area_sqft is not None and f.min_area_sqft > f.max_area_sqft:
        raise bad_request("min_area_sqft cannot be greater than max_area_sqft", "min_area_sqft")

    if f.q:
        like = f"%{f.q.strip()}%"
        stmt = stmt.where(or_(Property.title.ilike(like), Property.description.ilike(like),
                              Locality.locality_name.ilike(like), Locality.city.ilike(like)))
    if f.min_price is not None:
        stmt = stmt.where(Property.asking_price_inr >= f.min_price)
    if f.max_price is not None:
        stmt = stmt.where(Property.asking_price_inr <= f.max_price)
    if f.city:
        stmt = stmt.where(func.lower(Locality.city) == f.city.strip().lower())
    if f.locality_id:
        stmt = stmt.where(Property.locality_id == f.locality_id)
    for col, values in ((Property.property_type, f.property_type),
                        (Property.land_classification, f.land_classification),
                        (Property.intended_land_use, f.intended_land_use),
                        (Property.layout_approval_status, f.layout_approval_status),
                        (Property.conversion_status, f.conversion_status),
                        (Property.road_access, f.road_access)):
        if values:
            stmt = stmt.where(col.in_(values))
    if f.min_area_sqft is not None:
        stmt = stmt.where(Property.normalized_area_sqft >= f.min_area_sqft)
    if f.max_area_sqft is not None:
        stmt = stmt.where(Property.normalized_area_sqft <= f.max_area_sqft)
    if f.is_synthetic is not None:
        stmt = stmt.where(Property.is_synthetic == f.is_synthetic)
    for doc_type in f.has_document or []:
        stmt = stmt.where(select(PropertyDocument.id).where(
            PropertyDocument.property_id == Property.id, PropertyDocument.document_type == doc_type,
            PropertyDocument.availability == DocumentAvailability.provided).exists())

    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()

    order = {
        SortOption.price_asc: [Property.asking_price_inr.asc()],
        SortOption.price_desc: [Property.asking_price_inr.desc()],
        SortOption.area_asc: [Property.normalized_area_sqft.asc()],
        SortOption.area_desc: [Property.normalized_area_sqft.desc()],
        SortOption.newest: [Property.created_at.desc()],
        SortOption.oldest: [Property.created_at.asc()],
    }[f.sort]
    stmt = stmt.order_by(*order, Property.id.asc())  # id tiebreak keeps pagination stable
    stmt = _with_children(stmt).offset((f.page - 1) * f.page_size).limit(f.page_size)
    rows = db.execute(stmt).scalars().unique().all()

    applied = f.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    return PropertyListResponse(items=[summary(p) for p in rows], page=f.page, page_size=f.page_size, total=total,
                                total_pages=max(1, math.ceil(total / f.page_size)), applied_filters=applied)


# ---------------------------------------------------------------- write operations

def _check_geo(lat: Decimal | None, lng: Decimal | None) -> None:
    if lat is None:
        return
    s = get_settings()
    if not (s.geo_lat_min <= float(lat) <= s.geo_lat_max and s.geo_lng_min <= float(lng) <= s.geo_lng_max):
        raise AppError(422, "validation_error", "Coordinates are outside the supported region (Karnataka)",
                       [{"field": "latitude", "issue": "outside supported region"}])


def _resolve_amenities(db: Session, codes: list[str]) -> list[Amenity]:
    codes = list(dict.fromkeys(codes))
    if not codes:
        return []
    found = db.execute(select(Amenity).where(Amenity.code.in_(codes))).scalars().all()
    missing = set(codes) - {a.code for a in found}
    if missing:
        raise AppError(422, "validation_error", "Unknown amenity codes",
                       [{"field": "amenities", "issue": f"unknown: {', '.join(sorted(missing))}"}])
    return list(found)


_QUANT = {"asking_price_inr": Decimal("0.01"), "area_value": Decimal("0.0001"), "plot_width_ft": Decimal("0.01"),
          "plot_length_ft": Decimal("0.01"), "road_frontage_ft": Decimal("0.01"), "latitude": Decimal("0.000001"),
          "longitude": Decimal("0.000001")}


def _quantize(fields: dict) -> dict:
    """Match the database scale so API responses are identical before and after a reload."""
    return {k: (v.quantize(_QUANT[k], rounding=ROUND_HALF_UP) if k in _QUANT and isinstance(v, Decimal) else v)
            for k, v in fields.items()}


def _apply_documents(prop: Property, docs: list[DocumentIn]) -> None:
    existing = {d.document_type: d for d in prop.documents}
    for d in docs:
        row = existing.get(d.document_type)
        if row is None:
            row = PropertyDocument(document_type=d.document_type)
            prop.documents.append(row)
        if row.availability != d.availability:
            # A changed declaration resets any review that was in progress.
            row.verification_status = (VerificationStatus.not_applicable
                                       if d.availability == DocumentAvailability.not_applicable
                                       else VerificationStatus.unverified)
        row.availability = d.availability
        row.applicable_authority = d.applicable_authority
        if d.notes is not None:
            row.verification_notes = d.notes


def create_property(db: Session, user: User, data: PropertyCreate, *, status: ListingStatus = ListingStatus.pending,
                    is_synthetic: bool = False, data_source: str = "user_submitted",
                    source_record_id: str | None = None, coordinates_approximate: bool = False) -> Property:
    if user.role not in (UserRole.seller, UserRole.admin):
        raise forbidden("Only sellers can submit listings")
    locality = db.get(Locality, data.locality_id)
    if locality is None:
        raise AppError(422, "validation_error", "Unknown locality",
                       [{"field": "locality_id", "issue": "does not exist"}])
    _check_geo(data.latitude, data.longitude)
    amenities = _resolve_amenities(db, data.amenities)

    fields = _quantize(data.model_dump(exclude={"amenities", "documents", "consent_to_store"}))
    prop = Property(**fields, owner_id=user.id, normalized_area_sqft=to_sqft(data.area_value, data.area_unit),
                    listing_status=status, is_synthetic=is_synthetic, data_source=data_source,
                    source_record_id=source_record_id, coordinates_approximate=coordinates_approximate)
    prop.amenity_links = [PropertyAmenity(amenity=a) for a in amenities]
    _apply_documents(prop, data.documents)
    db.add(prop)
    db.flush()
    return prop


def update_property(db: Session, user: User, prop: Property, data: PropertyUpdate) -> Property:
    if not can_modify(prop, user):
        raise forbidden("You can only edit your own listings")
    if prop.listing_status == ListingStatus.archived:
        raise AppError(409, "conflict", "Archived listings cannot be edited")
    changes = _quantize(data.model_dump(exclude_unset=True))
    for key in ("title", "property_type", "asking_price_inr", "area_value", "area_unit", "locality_id"):
        if key in changes and changes[key] is None:
            raise bad_request(f"{key} cannot be empty", key)
    if "locality_id" in changes and db.get(Locality, changes["locality_id"]) is None:
        raise AppError(422, "validation_error", "Unknown locality", [{"field": "locality_id", "issue": "does not exist"}])
    lat = changes.get("latitude", prop.latitude)
    lng = changes.get("longitude", prop.longitude)
    if (lat is None) != (lng is None):
        raise bad_request("latitude and longitude must be provided together", "latitude")
    _check_geo(lat, lng)

    if "amenities" in changes:
        amenities = _resolve_amenities(db, changes.pop("amenities") or [])
        prop.amenity_links = [PropertyAmenity(amenity=a) for a in amenities]
    for key, value in changes.items():
        setattr(prop, key, value)
    if {"area_value", "area_unit"} & changes.keys():
        prop.normalized_area_sqft = to_sqft(prop.area_value, prop.area_unit)
    if "latitude" in changes and not is_admin(user):
        prop.coordinates_approximate = False

    # Seller edits to a reviewed listing send it back for review.
    if not is_admin(user) and prop.listing_status != ListingStatus.pending:
        prop.listing_status = ListingStatus.pending
        prop.review_reason = None
    db.flush()
    return prop


def archive_property(db: Session, user: User, prop: Property) -> None:
    if not can_modify(prop, user):
        raise forbidden("You can only archive your own listings")
    prop.listing_status = ListingStatus.archived
    db.flush()


def set_documents(db: Session, user: User, prop: Property, docs: list[DocumentIn]) -> Property:
    if not can_modify(prop, user):
        raise forbidden("You can only update documents of your own listings")
    if len({d.document_type for d in docs}) != len(docs):
        raise bad_request("each document type may appear only once", "documents")
    _apply_documents(prop, docs)
    if not is_admin(user) and prop.listing_status == ListingStatus.approved:
        prop.listing_status = ListingStatus.pending
    db.flush()
    return prop


def admin_set_verification(db: Session, admin: User, prop: Property, document_type: DocumentType,
                           status: VerificationStatus, reference: str | None, notes: str | None) -> Property:
    if not is_admin(admin):
        raise forbidden()
    row = next((d for d in prop.documents if d.document_type == document_type), None)
    if row is None or row.availability != DocumentAvailability.provided:
        raise AppError(409, "conflict", "Only documents declared as provided can enter verification")
    if status == VerificationStatus.verified:
        if not get_settings().document_verification_process_enabled:
            raise AppError(409, "verification_unavailable",
                           "No authorised document-verification process is configured, so documents cannot be "
                           "marked verified. Use 'pending' to record that a review has started.")
        if not reference:
            raise bad_request("A verification reference is required to mark a document verified",
                              "verification_reference")
    row.verification_status = status
    if notes or reference:
        row.verification_notes = " | ".join(x for x in (notes, f"ref: {reference}" if reference else None) if x)
    db.flush()
    return prop


def review(db: Session, admin: User, prop: Property, action: str, reason: str | None) -> Property:
    if not is_admin(admin):
        raise forbidden()
    target = {"approve": ListingStatus.approved, "reject": ListingStatus.rejected,
              "flag": ListingStatus.flagged}[action]
    if prop.listing_status == ListingStatus.archived:
        raise AppError(409, "conflict", "Archived listings cannot be reviewed")
    if target != ListingStatus.approved and not (reason and reason.strip()):
        raise bad_request("A reason is required to reject or flag a listing", "reason")
    prop.listing_status = target
    prop.review_reason = reason.strip() if reason else None
    db.flush()
    return prop
