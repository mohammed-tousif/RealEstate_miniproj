"""Price model: cleaning, features, training reproducibility, inference and the API."""
import json
import math
import shutil
from pathlib import Path

import pandas as pd
import pytest

from app.core.config import REPO_DIR, get_settings
from app.ml import pricing
from app.ml.data_prep import SchemaError, clean, detection_check, load_raw
from app.ml.features import FEATURES, build_features, feature_row
from app.ml.training import METADATA_FILE, train
from tests.conftest import create_listing, locality_id

RAW = REPO_DIR / "data" / "raw" / "synthetic_properties_v1.csv"


@pytest.fixture(scope="module")
def cleaned():
    return clean(RAW)


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory, cleaned):
    out = tmp_path_factory.mktemp("price_model")
    train(cleaned, out, seed=42, tune=False, dataset_file="test")
    return out


@pytest.fixture
def use_model(model_dir, monkeypatch):
    monkeypatch.setattr(get_settings(), "price_model_dir", model_dir)
    pricing.reset_cache()
    yield model_dir
    pricing.reset_cache()


def estimate_body(**kw):
    body = {"locality_id": locality_id("Saptapur"), "property_type": "residential_plot", "area_value": "1200",
            "area_unit": "sqft", "land_classification": "non_agricultural_residential",
            "conversion_status": "converted_claimed", "layout_approval_status": "approved_layout_claimed",
            "road_access": "paved_internal"}
    body.update(kw)
    return body


# ------------------------------------------------------------------ features and cleaning

def test_feature_row_handles_missing_and_unknown():
    row = feature_row({"city": "Dharwad", "locality": "Saptapur", "property_type": "residential_plot",
                       "normalized_area_sqft": 1200, "road_access": "unknown"})
    assert list(row) == FEATURES
    assert math.isclose(row["log_area_sqft"], math.log(1200))
    assert math.isnan(row["road_access_ord"]) and row["road_access_unknown"] == 1.0
    assert row["road_frontage_missing"] == 1.0 and math.isnan(row["road_frontage_ft"])
    assert math.isnan(row["distance_to_centre_km"])  # no coordinates
    assert row["land_classification"] == "unknown"


def test_feature_row_rejects_bad_area():
    for bad in (None, 0, -5, "abc"):
        with pytest.raises(ValueError):
            feature_row({"city": "Dharwad", "locality": "Saptapur", "property_type": "residential_plot",
                         "normalized_area_sqft": bad})


def test_missing_columns_rejected(tmp_path):
    df = pd.read_csv(RAW, dtype=str, keep_default_na=False).drop(columns=["asking_price_inr", "area_unit"])
    p = tmp_path / "broken.csv"
    df.to_csv(p, index=False)
    with pytest.raises(SchemaError, match="asking_price_inr"):
        load_raw(p)


def test_cleaning_excludes_invalid_rows_and_exact_duplicates(tmp_path):
    df = pd.read_csv(RAW, dtype=str, keep_default_na=False).head(40)
    bad_unit = df.iloc[[0]].assign(source_record_id="BAD-UNIT", area_unit="bigha")
    bad_price = df.iloc[[1]].assign(source_record_id="BAD-PRICE", asking_price_inr="-10")
    exact = df.iloc[[2]].assign(source_record_id="EXACT-COPY")
    p = tmp_path / "dirty.csv"
    pd.concat([df, bad_unit, bad_price, exact]).to_csv(p, index=False)
    c = clean(p)
    issues = c.flagged.set_index("source_record_id")["issue"].to_dict()
    assert "area_unit" in issues["BAD-UNIT"]
    assert "positive" in issues["BAD-PRICE"]
    assert "exact duplicate" in issues["EXACT-COPY"]
    assert not {"BAD-UNIT", "BAD-PRICE", "EXACT-COPY"} & set(c.clean["source_record_id"])


def test_cleaning_on_generated_data(cleaned):
    assert cleaned.raw_rows == 306
    ids = set(cleaned.clean["source_record_id"])
    # rejected listings and the extra copy of each near-duplicate are excluded
    assert not any(i.startswith("SYN-D") for i in ids)
    assert cleaned.clean["listing_status"].isin(["rejected", "archived"]).sum() == 0
    # every planted problem is found; the planted label is not used for the decision
    det = detection_check(load_raw(RAW), cleaned.flagged)
    assert (det["planted"] == det["detected"]).all(), det
    assert "injected_anomaly" not in FEATURES


# ------------------------------------------------------------------ training

def test_training_is_reproducible(tmp_path, cleaned):
    a = train(cleaned, tmp_path / "a", seed=42, tune=False)
    b = train(cleaned, tmp_path / "b", seed=42, tune=False)
    assert a["model_name"] == b["model_name"]
    assert a["test_metrics"] == b["test_metrics"]
    assert a["interval"] == b["interval"]
    assert a["split"] == b["split"]


def test_trained_model_beats_both_baselines(model_dir):
    m = json.loads((model_dir / METADATA_FILE).read_text())
    t = m["test_metrics"]
    best = t[m["model_name"]]["mae_inr"]
    assert best < t["baseline_median"]["mae_inr"]
    assert best < t["baseline_locality_type_ppsf"]["mae_inr"]
    assert m["trained_on_synthetic"] is True
    assert m["split"]["train"] + m["split"]["validation"] + m["split"]["test"] == m["dataset"]["clean_rows"]
    assert 0 < m["interval"]["measured_test_coverage"] <= 1


def test_model_handles_unseen_categories(model_dir):
    pricing.reset_cache()
    loaded = pricing.get_model(model_dir)
    X = build_features([{"city": "Dharwad", "locality": "Nowhere Nagar", "property_type": "residential_plot",
                         "normalized_area_sqft": 1500, "conversion_status": "something_new"}])
    v = float(loaded.model.predict(X)[0])
    assert math.isfinite(v) and v > 0
    w = pricing.input_warnings(loaded.metadata, {"locality": "Nowhere Nagar", "property_type": "residential_plot",
                                                 "normalized_area_sqft": 1500, "road_access": "unknown"})
    assert any("not in the training data" in x for x in w)


def test_version_mismatch_means_unavailable(tmp_path, model_dir):
    copy = tmp_path / "old"
    shutil.copytree(model_dir, copy)
    meta = json.loads((copy / METADATA_FILE).read_text())
    meta["library_versions"]["scikit-learn"] = "0.24.0"
    (copy / METADATA_FILE).write_text(json.dumps(meta))
    pricing.reset_cache()
    ok, reason = pricing.model_status(copy)
    assert not ok and "0.24.0" in reason


# ------------------------------------------------------------------ API

def test_no_model_returns_503(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "price_model_dir", tmp_path / "missing")
    pricing.reset_cache()
    r = client.post("/api/v1/predictions/price", json=estimate_body())
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "model_unavailable"
    assert client.get("/api/v1/model-info").json()["price_model"] is None
    assert client.get("/api/v1/health").json()["price_model_loaded"] is False
    pricing.reset_cache()


def test_estimate_from_fields(client, use_model):
    r = client.post("/api/v1/predictions/price", json=estimate_body(asking_price_inr="2500000"))
    assert r.status_code == 200, r.text
    d = r.json()
    low, mid, high = (float(d["indicative_range_inr"]["low"]), float(d["predicted_asking_price_inr"]),
                      float(d["indicative_range_inr"]["high"]))
    assert 0 < low < mid < high
    assert d["model"]["trained_on_synthetic"] is True
    assert any("synthetic" in w for w in d["warnings"])
    assert "not a valuation" in d["disclaimer"].lower()
    assert d["quoted_position"] in ("below_range", "within_range", "above_range")
    assert math.isclose(d["quoted_vs_estimate_pct"], (2_500_000 - mid) / mid * 100, abs_tol=0.2)
    assert any("coordinates" in w for w in d["warnings"])  # locality centre used
    assert d["top_factors"] and d["top_factors_note"]


def test_units_give_consistent_estimates(client, use_model):
    a = client.post("/api/v1/predictions/price", json=estimate_body(area_value="2178", area_unit="sqft")).json()
    b = client.post("/api/v1/predictions/price", json=estimate_body(area_value="2", area_unit="gunta")).json()
    assert a["normalized_area_sqft"] == b["normalized_area_sqft"] == "2178.0000"
    assert a["predicted_asking_price_inr"] == b["predicted_asking_price_inr"]


@pytest.mark.parametrize("override,field", [
    ({"area_unit": "bigha"}, "area_unit"),
    ({"area_value": "-10"}, "area_value"),
    ({"property_type": "castle"}, "property_type"),
    ({"area_value": None}, None),
])
def test_invalid_input_rejected(client, use_model, override, field):
    body = estimate_body(**override)
    body = {k: v for k, v in body.items() if v is not None}
    r = client.post("/api/v1/predictions/price", json=body)
    assert r.status_code == 422, r.text


def test_unknown_locality_rejected(client, use_model):
    r = client.post("/api/v1/predictions/price", json=estimate_body(locality_id=99999))
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "locality_id"


def test_extreme_area_warns_extrapolation(client, use_model):
    r = client.post("/api/v1/predictions/price", json=estimate_body(area_value="5000", area_unit="acre"))
    assert r.status_code == 200, r.text
    assert any("extrapolating" in w for w in r.json()["warnings"])


def test_estimate_for_listing_and_comparables(client, use_model, seller_h, admin_h):
    a = create_listing(client, seller_h, approve_with=admin_h, asking_price_inr="1900000.00")
    b = create_listing(client, seller_h, approve_with=admin_h, title="Neighbouring test plot",
                       area_value="1500", asking_price_inr="2400000.00")
    r = client.post("/api/v1/predictions/price", json={"property_id": a["id"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["quoted_price_inr"] == "1900000.00"
    ids = [c["id"] for c in d["comparables"]]
    assert b["id"] in ids and a["id"] not in ids
    assert all(c["property_type"] == "residential_plot" for c in d["comparables"])


def test_hidden_listing_not_estimated_for_guests(client, use_model, seller_h):
    pending = create_listing(client, seller_h)
    r = client.post("/api/v1/predictions/price", json={"property_id": pending["id"]})
    assert r.status_code == 404
    r = client.post("/api/v1/predictions/price", json={"property_id": pending["id"]}, headers=seller_h)
    assert r.status_code == 200


def test_model_info_and_health(client, use_model):
    info = client.get("/api/v1/model-info").json()["price_model"]
    assert info["trained_on_synthetic"] is True
    assert set(info["test_metrics"]) >= {"baseline_median", "baseline_locality_type_ppsf", info["model_name"]}
    assert "synthetic" in info["caveat"].lower()
    assert client.get("/api/v1/health").json()["price_model_loaded"] is True
