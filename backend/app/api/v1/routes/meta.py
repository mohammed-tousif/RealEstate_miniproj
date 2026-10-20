from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Amenity, Locality
from app.models import enums as E
from app.schemas.property import LocalityOut
from app.services.area_units import SQFT_PER_UNIT
from app.services.document_rules import DISPLAY_LABELS, DOCUMENT_GUIDANCE

router = APIRouter(tags=["reference data"])


@router.get("/localities", response_model=list[LocalityOut])
def localities(city: str | None = Query(default=None, max_length=80), db: Session = Depends(get_db)):
    stmt = select(Locality).order_by(Locality.city, Locality.locality_name)
    if city:
        stmt = stmt.where(Locality.city == city)
    return db.execute(stmt).scalars().all()


@router.get("/meta/enums")
def enums(db: Session = Depends(get_db)):
    """Every enum value with its display label: the single source of truth for the frontend."""
    groups = {cls.__name__: cls.labels() for cls in (
        E.PropertyType, E.IntendedLandUse, E.LandClassification, E.ConversionStatus, E.LayoutApprovalStatus,
        E.AreaUnit, E.RoadAccess, E.ListingStatus, E.DocumentType, E.DocumentAvailability,
        E.VerificationStatus, E.UserRole, E.AmenityCategory)}
    amenities = [{"code": a.code, "label": a.label, "category": a.category.value}
                 for a in db.execute(select(Amenity).order_by(Amenity.category, Amenity.label)).scalars()]
    return {
        "enums": groups,
        "document_display_status": DISPLAY_LABELS,
        "document_guidance": {k.value: v for k, v in DOCUMENT_GUIDANCE.items()},
        "area_unit_sqft_factor": {k.value: str(v) for k, v in SQFT_PER_UNIT.items()},
        "amenities": amenities,
    }
