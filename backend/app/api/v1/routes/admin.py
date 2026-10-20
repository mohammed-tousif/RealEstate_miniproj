import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import Locality, Property, User
from app.models.enums import ListingStatus
from app.schemas.property import AdminDocumentVerification, PropertyDetail, PropertyListResponse
from app.services import property_service as ps

router = APIRouter(prefix="/admin", tags=["admin"])


class ReviewBody(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


@router.get("/properties", response_model=PropertyListResponse)
def review_queue(status: ListingStatus = ListingStatus.pending, page: int = Query(1, ge=1),
                 page_size: int = Query(20, ge=1, le=50), db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    f = ps.PropertyFilters(status=status, sort=ps.SortOption.oldest, page=page, page_size=page_size)
    return ps.list_properties(db, admin, f)


@router.get("/properties/pending", response_model=PropertyListResponse)
def pending(page: int = Query(1, ge=1), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return review_queue(ListingStatus.pending, page, 20, db, admin)


def _review(action: Literal["approve", "reject", "flag"], property_id: uuid.UUID, body: ReviewBody,
            db: Session, admin: User) -> PropertyDetail:
    prop = ps.get_visible_property(db, property_id, admin)
    ps.review(db, admin, prop, action, body.reason)
    db.commit()
    return ps.detail(ps.load_property(db, prop.id), admin)


@router.post("/properties/{property_id}/approve", response_model=PropertyDetail)
def approve(property_id: uuid.UUID, body: ReviewBody | None = None, db: Session = Depends(get_db),
            admin: User = Depends(require_admin)):
    return _review("approve", property_id, body or ReviewBody(), db, admin)


@router.post("/properties/{property_id}/reject", response_model=PropertyDetail)
def reject(property_id: uuid.UUID, body: ReviewBody, db: Session = Depends(get_db),
           admin: User = Depends(require_admin)):
    return _review("reject", property_id, body, db, admin)


@router.post("/properties/{property_id}/flag", response_model=PropertyDetail)
def flag(property_id: uuid.UUID, body: ReviewBody, db: Session = Depends(get_db),
         admin: User = Depends(require_admin)):
    return _review("flag", property_id, body, db, admin)


@router.post("/properties/{property_id}/documents/verification", response_model=PropertyDetail)
def set_verification(property_id: uuid.UUID, body: AdminDocumentVerification, db: Session = Depends(get_db),
                     admin: User = Depends(require_admin)):
    prop = ps.get_visible_property(db, property_id, admin)
    ps.admin_set_verification(db, admin, prop, body.document_type, body.verification_status,
                              body.verification_reference, body.notes)
    db.commit()
    return ps.detail(ps.load_property(db, prop.id), admin)


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    def grouped(*cols):
        return db.execute(select(*cols, func.count()).select_from(Property)
                          .join(Locality, Property.locality_id == Locality.id).group_by(*cols)).all()
    by_status = {s.value: n for s, n in grouped(Property.listing_status)}
    by_type = {t.value: n for t, n in grouped(Property.property_type)}
    by_city = {c: n for c, n in grouped(Locality.city)}
    synthetic = {("synthetic" if s else "genuine"): n for s, n in grouped(Property.is_synthetic)}
    users = {r.value: n for r, n in db.execute(select(User.role, func.count()).group_by(User.role)).all()}
    return {"listings_by_status": by_status, "listings_by_type": by_type, "listings_by_city": by_city,
            "listings_by_origin": synthetic, "users_by_role": users,
            "total_listings": sum(by_status.values())}
