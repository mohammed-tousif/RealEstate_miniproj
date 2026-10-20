import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.session import get_db
from app.models import Favorite, Property, User, UserPreference
from app.models.enums import ListingStatus
from app.schemas.auth import PreferencesIn, PreferencesOut, UserOut
from app.schemas.property import PropertySummary
from app.services import property_service as ps

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("", response_model=UserOut)
def me(user: User = Depends(require_user)):
    return user


@router.get("/preferences", response_model=PreferencesOut | None)
def get_preferences(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return db.get(UserPreference, user.id)


@router.put("/preferences", response_model=PreferencesOut)
def put_preferences(body: PreferencesIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pref = db.get(UserPreference, user.id) or UserPreference(user_id=user.id)
    for k, v in body.model_dump(mode="json").items():
        setattr(pref, k, v)
    pref.minimum_budget, pref.maximum_budget = body.minimum_budget, body.maximum_budget
    db.add(pref)
    db.commit()
    return pref


@router.get("/favorites", response_model=list[PropertySummary])
def list_favorites(user: User = Depends(require_user), db: Session = Depends(get_db)):
    ids = db.execute(select(Favorite.property_id).where(Favorite.user_id == user.id)
                     .order_by(Favorite.created_at.desc())).scalars().all()
    out = []
    for pid in ids:
        p = ps.load_property(db, pid)
        if p is not None and p.listing_status == ListingStatus.approved:
            out.append(ps.summary(p))
    return out


@router.put("/favorites/{property_id}", status_code=204)
def add_favorite(property_id: uuid.UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    prop = db.get(Property, property_id)
    if prop is None or prop.listing_status != ListingStatus.approved:
        from app.core.errors import not_found
        raise not_found("Property")
    if db.get(Favorite, (user.id, property_id)) is None:
        db.add(Favorite(user_id=user.id, property_id=property_id))
        db.commit()
    return Response(status_code=204)


@router.delete("/favorites/{property_id}", status_code=204)
def remove_favorite(property_id: uuid.UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    fav = db.get(Favorite, (user.id, property_id))
    if fav is not None:
        db.delete(fav)
        db.commit()
    return Response(status_code=204)
