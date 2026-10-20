import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, require_seller, require_user
from app.core.config import get_settings
from app.core.errors import AppError, forbidden
from app.db.session import get_db
from app.models import PropertyImage, User
from app.schemas.property import (DocumentsUpdate, ImageOut, PropertyCreate, PropertyDetail, PropertyListResponse,
                                  PropertyUpdate)
from app.services import property_service as ps
from app.services import storage

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse)
def search(filters: Annotated[ps.PropertyFilters, Query()], db: Session = Depends(get_db),
           user: User | None = Depends(get_current_user_optional)):
    """Search approved listings. `mine=true` lists the caller's own listings (any review status);
    `status=` other than approved is for administrators."""
    return ps.list_properties(db, user, filters)


@router.get("/{property_id}", response_model=PropertyDetail)
def get_property(property_id: uuid.UUID, db: Session = Depends(get_db),
                 user: User | None = Depends(get_current_user_optional)):
    return ps.detail(ps.get_visible_property(db, property_id, user), user)


@router.post("", response_model=PropertyDetail, status_code=201)
def create(body: PropertyCreate, db: Session = Depends(get_db), user: User = Depends(require_seller)):
    """Create a listing. It is stored as `pending` until an administrator approves it."""
    prop = ps.create_property(db, user, body)
    db.commit()
    return ps.detail(ps.load_property(db, prop.id), user)


@router.patch("/{property_id}", response_model=PropertyDetail)
def update(property_id: uuid.UUID, body: PropertyUpdate, db: Session = Depends(get_db),
           user: User = Depends(require_user)):
    prop = ps.get_visible_property(db, property_id, user)
    ps.update_property(db, user, prop, body)
    db.commit()
    return ps.detail(ps.load_property(db, prop.id), user)


@router.delete("/{property_id}", status_code=204)
def archive(property_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Archive (soft-delete) a listing; it disappears from search but the record is kept."""
    prop = ps.get_visible_property(db, property_id, user)
    ps.archive_property(db, user, prop)
    db.commit()
    return Response(status_code=204)


@router.put("/{property_id}/documents", response_model=PropertyDetail)
def put_documents(property_id: uuid.UUID, body: DocumentsUpdate, db: Session = Depends(get_db),
                  user: User = Depends(require_user)):
    """Declare which documents are available. Declarations are never treated as verification."""
    prop = ps.get_visible_property(db, property_id, user)
    ps.set_documents(db, user, prop, body.documents)
    db.commit()
    return ps.detail(ps.load_property(db, prop.id), user)


@router.post("/{property_id}/images", response_model=ImageOut, status_code=201)
async def upload_image(property_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
                       user: User = Depends(require_user)):
    prop = ps.get_visible_property(db, property_id, user)
    if not ps.can_modify(prop, user):
        raise forbidden("You can only add photos to your own listings")
    if len(prop.images) >= get_settings().max_images_per_property:
        raise AppError(409, "conflict", f"A listing can have at most {get_settings().max_images_per_property} images")
    path, ctype = await storage.save_property_image(prop.id, file)
    img = PropertyImage(property_id=prop.id, storage_path=path, content_type=ctype, ordering=len(prop.images))
    db.add(img)
    db.commit()
    return ImageOut(id=img.id, url=ps.media_url(path), ordering=img.ordering)


@router.delete("/{property_id}/images/{image_id}", status_code=204)
def delete_image(property_id: uuid.UUID, image_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_user)):
    prop = ps.get_visible_property(db, property_id, user)
    if not ps.can_modify(prop, user):
        raise forbidden("You can only remove photos from your own listings")
    img = next((i for i in prop.images if i.id == image_id), None)
    if img is None:
        from app.core.errors import not_found
        raise not_found("Image")
    storage.delete_file(img.storage_path)
    db.delete(img)
    db.commit()
    return Response(status_code=204)
