"""Real imported listings: provenance is kept, nothing personal is stored, and the API labels them."""
import csv
import re
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Property

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
import build_real_listings as real  # noqa: E402
import seed_db  # noqa: E402

REAL_CSV = BACKEND.parent / "data" / "raw" / "real_listings_1acre_v1.csv"


def _rows():
    with REAL_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_committed_csv_matches_builder():
    rows = _rows()
    assert [r["source_record_id"] for r in rows] == [f"REAL-1ACRE-{x[0]}" for x in real.LISTINGS]
    assert rows == [{k: str(v) for k, v in real.row(x).items()} for x in real.LISTINGS]


def test_real_rows_have_provenance_and_no_personal_data():
    for r in _rows():
        assert r["is_synthetic"] == "False" and r["data_source"] == "1acre_public_listing"
        assert r["source_url"].startswith("https://1acre.in/lands-for-sale/") and r["source_retrieved_on"]
        assert r["city"] in ("Hubballi", "Dharwad")
        text = " ".join(r.values())
        assert not re.search(r"\b\d{10}\b|\+91|@", text), r["source_record_id"]  # no phones or e-mails
        # Facts the source does not state stay unknown instead of being invented.
        assert r["land_classification"] == "unknown" and r["amenities"] == ""
        assert r["plot_width_ft"] == r["road_frontage_ft"] == ""
        assert len(r["latitude"].split(".")[1]) == 3  # rounded to about 100 m


def test_road_access_mapping():
    assert real.road_access("60 ft highway road") == "highway"
    assert real.road_access("40 ft blacktop road") == "main_road"
    assert real.road_access("abutting 33 ft blacktop road") == "paved_internal"
    assert real.road_access("100 ft kacha road") == "unpaved"
    assert real.road_access("abutting 30 ft road, type not stated") == "unknown"
    assert real.road_access("") == "unknown"


def test_seed_loads_real_listings_labelled(client):
    with SessionLocal() as db:
        locs = seed_db.upsert_reference(db)
        owner = seed_db.upsert_import_account(db)
        n = seed_db.load_real_listings(db, REAL_CSV, locs, owner)
        db.commit()
        props = db.execute(select(Property).where(Property.data_source == "1acre_public_listing")).scalars().all()
        assert n == len(props) == len(real.LISTINGS)
        assert all(not p.is_synthetic and p.source_url and p.source_retrieved_on for p in props)
        assert all(p.coordinates_approximate for p in props)
        pid = str(props[0].id)
    listing = next(p for p in client.get("/api/v1/properties", params={"page_size": 50}).json()["items"]
                   if p["id"] == pid)
    assert listing["is_synthetic"] is False and listing["source_url"].startswith("https://1acre.in/")
    detail = client.get(f"/api/v1/properties/{pid}").json()
    assert detail["data_source"] == "1acre_public_listing" and detail["source_retrieved_on"] == "2026-10-20"
    assert "PropWise does not represent the seller" in detail["description"]
    # The import account cannot sign in with the demo password.
    r = client.post("/api/v1/auth/login", json={"email": seed_db.IMPORT_ACCOUNT[1], "password": "DemoPass123"})
    assert r.status_code == 401
