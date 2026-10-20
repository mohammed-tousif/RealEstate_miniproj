import csv
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, select

from app.db.session import SessionLocal
from app.models import Property, User
from app.models.enums import UserRole

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
import generate_synthetic_data as gen  # noqa: E402
import seed_db  # noqa: E402


def test_generator_is_reproducible_and_labelled():
    a, b = gen.generate(40, seed=7), gen.generate(40, seed=7)
    assert a == b
    assert gen.generate(40, seed=8) != a
    assert all(r["is_synthetic"] is True and r["data_source"] == "synthetic_generator_v1" for r in a)
    assert all("synthetic demonstration listing" in r["description"] for r in a)
    anomalies = [r["injected_anomaly"] for r in a if r["injected_anomaly"]]
    assert any(x.startswith("near_duplicate_of") for x in anomalies)
    assert any(x.startswith("price_outlier") for x in anomalies)


def test_seed_loads_synthetic_listings(tmp_path):
    path = tmp_path / "s.csv"
    rows = gen.generate(30, seed=3)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=gen.COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k, "")) for k in gen.COLUMNS})
    with SessionLocal() as db:
        locs = seed_db.upsert_reference(db)
        users = seed_db.upsert_users(db, "DemoPass123")
        sellers = [u for u in users.values() if u.role == UserRole.seller]
        n = seed_db.load_listings(db, path, locs, sellers)
        db.commit()
        props = db.execute(select(Property)).scalars().all()
        assert n == len(rows) == len(props)
        assert all(p.is_synthetic for p in props)
        by_id = {r["source_record_id"]: r for r in rows}
        for p in props:  # normalised area matches the generator's own calculation
            assert abs(float(p.normalized_area_sqft) - by_id[p.source_record_id]["normalized_area_sqft_expected"]) < 0.5
        assert all(u.is_demo_account for u in db.execute(select(User).where(User.email.like("%demo.propwise%")))
                   .scalars())


def test_alembic_migration_matches_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'mig.db').as_posix()}"
    out = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND,
                         env={**__import__("os").environ, "DATABASE_URL": url}, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"users", "properties", "localities", "property_documents", "property_images", "amenities",
            "property_amenities", "favorites", "user_preferences", "recommendation_history",
            "model_metadata"} <= tables
