"""Test setup. Uses a throwaway SQLite file by default; set TEST_DATABASE_URL to a
PostgreSQL URL to run the same suite against PostgreSQL."""
import os
import tempfile
from decimal import Decimal
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="propwise-test-"))
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{(_tmp / 'test.db').as_posix()}")
os.environ["APP_ENV"] = "test"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-use-0123456789"
os.environ["STORAGE_DIR"] = str(_tmp / "storage")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Amenity, Locality, User  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.services.reference_data import AMENITIES, LOCALITIES  # noqa: E402

PASSWORD = "Passw0rd123"


@pytest.fixture(autouse=True)
def fresh_db():
    from app.ai import rate_limit
    rate_limit.reset()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for name, city, lat, lng, rural in LOCALITIES:
            db.add(Locality(locality_name=name, city=city, district="Dharwad", state="Karnataka",
                            center_lat=Decimal(str(lat)), center_lng=Decimal(str(lng)), is_rural=rural))
        for code, label, cat in AMENITIES:
            db.add(Amenity(code=code, label=label, category=cat))
        for name, email, role in [("Admin", "admin@test.example", UserRole.admin),
                                  ("Seller A", "seller_a@test.example", UserRole.seller),
                                  ("Seller B", "seller_b@test.example", UserRole.seller),
                                  ("Buyer", "buyer@test.example", UserRole.buyer)]:
            db.add(User(name=name, email=email, role=role, password_hash=hash_password(PASSWORD)))
        db.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login(client, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_h(client):
    return login(client, "admin@test.example")


@pytest.fixture
def seller_h(client):
    return login(client, "seller_a@test.example")


@pytest.fixture
def seller_b_h(client):
    return login(client, "seller_b@test.example")


@pytest.fixture
def buyer_h(client):
    return login(client, "buyer@test.example")


def locality_id(name: str) -> int:
    with SessionLocal() as db:
        return db.query(Locality).filter_by(locality_name=name).one().id


def listing_payload(**overrides) -> dict:
    body = {
        "title": "Test 30x40 residential plot",
        "description": "Plot for automated tests.",
        "property_type": "residential_plot",
        "intended_land_use": "residential",
        "land_classification": "non_agricultural_residential",
        "conversion_status": "converted_claimed",
        "layout_approval_status": "approved_layout_claimed",
        "asking_price_inr": "1850000.00",
        "area_value": "1200",
        "area_unit": "sqft",
        "plot_width_ft": "30",
        "plot_length_ft": "40",
        "road_access": "paved_internal",
        "locality_id": locality_id("Saptapur"),
        "latitude": "15.460000",
        "longitude": "75.006000",
        "amenities": ["school", "bus_stop"],
        "documents": [{"document_type": "rtc_pahani", "availability": "provided"},
                      {"document_type": "encumbrance_certificate", "availability": "provided"}],
        "consent_to_store": True,
    }
    body.update(overrides)
    return body


def create_listing(client, headers, approve_with=None, **overrides) -> dict:
    r = client.post("/api/v1/properties", json=listing_payload(**overrides), headers=headers)
    assert r.status_code == 201, r.text
    prop = r.json()
    if approve_with:
        r = client.post(f"/api/v1/admin/properties/{prop['id']}/approve", headers=approve_with)
        assert r.status_code == 200, r.text
        prop = r.json()
    return prop
