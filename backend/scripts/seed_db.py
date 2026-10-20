"""Load reference data, demo accounts and the SYNTHETIC listings into the database.

Run after `alembic upgrade head`:
    python scripts/seed_db.py            # idempotent: skips listings if already loaded
    python scripts/seed_db.py --reset    # removes previously seeded synthetic listings first

Demo accounts use the password from SEED_DEMO_PASSWORD (default shown below). They are
demo-only identities (…@demo.propwise.example), never real people.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, time, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Amenity, Locality, Property, PropertyAmenity, PropertyDocument, User  # noqa: E402
from app.models.enums import (DocumentAvailability, DocumentType, ListingStatus, UserRole,  # noqa: E402
                              VerificationStatus)
from app.schemas.property import DocumentIn, PropertyCreate  # noqa: E402
from app.services import property_service as ps  # noqa: E402
from app.services.reference_data import AMENITIES, DISTRICT, LOCALITIES, STATE  # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "raw" / "synthetic_properties_v1.csv"
DEFAULT_DEMO_PASSWORD = "DemoPass123"

DEMO_USERS = [
    ("Demo Admin", "admin@demo.propwise.example", UserRole.admin),
    ("Demo Seller One", "seller1@demo.propwise.example", UserRole.seller),
    ("Demo Seller Two", "seller2@demo.propwise.example", UserRole.seller),
    ("Demo Seller Three", "seller3@demo.propwise.example", UserRole.seller),
    ("Demo Buyer", "buyer@demo.propwise.example", UserRole.buyer),
]


def upsert_reference(db: Session) -> dict[tuple[str, str], Locality]:
    existing = {(l.locality_name, l.city): l for l in db.execute(select(Locality)).scalars()}
    for name, city, lat, lng, rural in LOCALITIES:
        if (name, city) not in existing:
            loc = Locality(locality_name=name, city=city, district=DISTRICT, state=STATE,
                           center_lat=Decimal(str(lat)), center_lng=Decimal(str(lng)),
                           coordinates_approximate=True, is_rural=rural)
            db.add(loc)
            existing[(name, city)] = loc
    codes = {a.code for a in db.execute(select(Amenity)).scalars()}
    for code, label, cat in AMENITIES:
        if code not in codes:
            db.add(Amenity(code=code, label=label, category=cat))
    db.flush()
    return existing


def upsert_users(db: Session, password: str) -> dict[str, User]:
    users = {}
    for name, email, role in DEMO_USERS:
        u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if u is None:
            u = User(name=name, email=email, role=role, password_hash=hash_password(password), is_demo_account=True)
            db.add(u)
        users[email] = u
    db.flush()
    return users


def _opt_dec(v: str) -> Decimal | None:
    return Decimal(v) if v not in ("", None) else None


def _opt_bool(v: str) -> bool | None:
    return None if v == "" else v == "True"


def load_listings(db: Session, csv_path: Path, localities, sellers: list[User]) -> int:
    amenity_ids = {a.code: a for a in db.execute(select(Amenity)).scalars()}
    count = 0
    with csv_path.open(encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            loc = localities[(row["locality"], row["city"])]
            docs = [DocumentIn(document_type=t, availability=DocumentAvailability(row[f"doc_{t.value}"]))
                    for t in DocumentType if row.get(f"doc_{t.value}")]
            data = PropertyCreate(
                title=row["title"], description=row["description"], property_type=row["property_type"],
                intended_land_use=row["intended_land_use"], land_classification=row["land_classification"],
                conversion_status=row["conversion_status"], layout_approval_status=row["layout_approval_status"],
                asking_price_inr=Decimal(row["asking_price_inr"]), area_value=Decimal(row["area_value"]),
                area_unit=row["area_unit"], plot_width_ft=_opt_dec(row["plot_width_ft"]),
                plot_length_ft=_opt_dec(row["plot_length_ft"]), road_frontage_ft=_opt_dec(row["road_frontage_ft"]),
                road_access=row["road_access"], is_corner_plot=_opt_bool(row["is_corner_plot"]),
                locality_id=loc.id, general_address=row["general_address"],
                latitude=Decimal(row["latitude"]), longitude=Decimal(row["longitude"]),
                documents=docs, consent_to_store=True)
            seller = sellers[i % len(sellers)]
            prop = ps.create_property(db, seller, data, status=ListingStatus(row["listing_status"]),
                                      is_synthetic=True, data_source=row["data_source"],
                                      source_record_id=row["source_record_id"], coordinates_approximate=True)
            listed = datetime.combine(datetime.fromisoformat(row["listed_on"]).date(), time(10, 0),
                                      tzinfo=timezone.utc)
            prop.created_at = prop.updated_at = listed
            for item in filter(None, row["amenities"].split(";")):
                code, km = item.split(":")
                prop.amenity_links.append(PropertyAmenity(amenity=amenity_ids[code], approx_distance_km=Decimal(km),
                                                          distance_is_synthetic=True))
            if prop.listing_status == ListingStatus.rejected:
                prop.review_reason = "Demo rejection: listing information incomplete."
            elif prop.listing_status == ListingStatus.flagged:
                prop.review_reason = "Demo flag: price looks inconsistent with similar listings."
            elif prop.listing_status == ListingStatus.approved and i % 17 == 0:
                for d in prop.documents:  # a few documents show a review that has started
                    if d.availability == DocumentAvailability.provided:
                        d.verification_status = VerificationStatus.pending
                        break
            count += 1
    return count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--reset", action="store_true", help="delete previously seeded synthetic listings first")
    args = ap.parse_args()
    password = os.environ.get("SEED_DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)

    with SessionLocal() as db:
        localities = upsert_reference(db)
        users = upsert_users(db, password)
        if args.reset:
            ids = select(Property.id).where(Property.data_source == "synthetic_generator_v1")
            for model in (PropertyAmenity, PropertyDocument):
                db.execute(delete(model).where(model.property_id.in_(ids)))
            db.execute(delete(Property).where(Property.data_source == "synthetic_generator_v1"))
            db.flush()
        already = db.execute(select(Property.id).where(Property.data_source == "synthetic_generator_v1")
                             .limit(1)).first()
        if already:
            print("Synthetic listings already loaded; use --reset to reload.")
        else:
            sellers = [u for u in users.values() if u.role == UserRole.seller]
            n = load_listings(db, args.csv, localities, sellers)
            print(f"Loaded {n} SYNTHETIC demo listings from {args.csv.name}")
        db.commit()
    print("Demo accounts (password from SEED_DEMO_PASSWORD, default 'DemoPass123'):")
    for name, email, role in DEMO_USERS:
        print(f"  {role.value:<6} {email}")


if __name__ == "__main__":
    main()
