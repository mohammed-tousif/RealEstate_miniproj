"""Recommendation engine, comparison and similar listings."""
import re
import uuid
from datetime import datetime, timezone

import pytest

from app.ml.recommendation import config as C
from app.ml.recommendation.engine import Candidate, rank, resolve_weights
from app.models import RecommendationHistory
from app.db.session import SessionLocal
from app.schemas.recommendation import Preferences
from tests.conftest import create_listing, locality_id

LOCS = {1: ("Saptapur", "Dharwad"), 2: ("Kelgeri", "Dharwad"), 3: ("Vidyanagar", "Hubballi")}
DOCS_FULL = {"rtc_pahani": "provided", "encumbrance_certificate": "provided", "sale_deed": "provided",
             "khata": "provided", "dc_conversion_order": "provided", "layout_approval": "provided"}


def cand(**kw) -> Candidate:
    base = dict(id=uuid.uuid4(), property_type="residential_plot", land_classification="non_agricultural_residential",
                conversion_status="converted_claimed", layout_approval_status="approved_layout_claimed",
                road_access="paved_internal", price=2_000_000, area_sqft=1200, locality_id=1,
                locality_name="Saptapur", city="Dharwad", doc_completeness=1.0, docs_provided=6, docs_applicable=6,
                doc_status=dict(DOCS_FULL), created_at=datetime.now(timezone.utc), latitude=15.46, longitude=75.0)
    base.update(kw)
    return Candidate(**base)


def by_id(result):
    return {s.candidate.id: s for s in result.scored}


# ------------------------------------------------------------------ hard constraints

def test_strict_budget_never_exceeded():
    cs = [cand(price=p) for p in (1_000_000, 2_400_000, 2_500_000, 2_600_000, 9_000_000)]
    r = rank(cs, Preferences(max_budget=2_500_000), LOCS)
    assert all(s.candidate.price <= 2_500_000 for s in r.scored)
    assert r.excluded["Over your maximum budget"] == 2


def test_non_strict_budget_allows_ten_percent_scored_down():
    within, over, far = cand(price=2_400_000), cand(price=2_700_000), cand(price=2_800_000)
    r = rank([within, over, far], Preferences(max_budget=2_500_000, budget_strict=False), LOCS)
    s = by_id(r)
    assert far.id not in s and r.excluded["More than 10% over your budget"] == 1
    assert s[within.id].score > s[over.id].score
    budget = next(f for f in s[over.id].factors if f.name == "budget")
    assert budget.score == pytest.approx(1 - 0.08 / 0.10)


def test_min_budget_strict():
    r = rank([cand(price=500_000), cand(price=1_500_000)], Preferences(min_budget=1_000_000), LOCS)
    assert [s.candidate.price for s in r.scored] == [1_500_000]


def test_type_constraint_strict_and_soft():
    plot, farm = cand(), cand(property_type="agricultural_land", land_classification="agricultural",
                              conversion_status="not_applicable", layout_approval_status="not_applicable")
    strict = rank([plot, farm], Preferences(property_types=["residential_plot"]), LOCS)
    assert [s.candidate.id for s in strict.scored] == [plot.id]
    soft = rank([plot, farm], Preferences(property_types=["residential_plot"], types_strict=False), LOCS)
    assert len(soft.scored) == 2 and soft.scored[0].candidate.id == plot.id


def test_location_matching_and_strictness():
    a = cand(locality_id=1)
    b = cand(locality_id=2, locality_name="Kelgeri")
    c = cand(locality_id=3, locality_name="Vidyanagar", city="Hubballi")
    r = rank([a, b, c], Preferences(locality_ids=[1]), LOCS)
    loc = {s.candidate.id: next(f.score for f in s.factors if f.name == "location") for s in r.scored}
    assert loc[a.id] == 1.0 and loc[b.id] == 0.7 and loc[c.id] == 0.3
    strict = rank([a, b, c], Preferences(locality_ids=[1], cities=["Hubballi"], location_strict=True), LOCS)
    assert {s.candidate.id for s in strict.scored} == {a.id, c.id}


def test_min_area_strict_and_soft():
    small, big = cand(area_sqft=600), cand(area_sqft=2400)
    assert [s.candidate.id for s in rank([small, big], Preferences(min_area_value=1000, area_strict=True), LOCS).scored] == [big.id]
    soft = by_id(rank([small, big], Preferences(min_area_value=1, min_area_unit="gunta"), LOCS))
    assert any("below your preferred minimum of 1,089 sq ft" in t for t in soft[small.id].tradeoffs)


# ------------------------------------------------------------------ scoring and missing data

def test_missing_road_scores_zero_and_is_reported():
    known, unknown = cand(), cand(road_access="unknown")
    s = by_id(rank([known, unknown], Preferences(), LOCS))
    road = next(f for f in s[unknown.id].factors if f.name == "connectivity")
    assert road.score == 0 and road.known == 0
    assert s[unknown.id].coverage < s[known.id].coverage == 1.0
    assert any("Road access is not stated" in m for m in s[unknown.id].missing_info)


def test_unknown_documents_count_as_not_provided():
    c = cand(doc_completeness=0.4, docs_provided=2, doc_status={**DOCS_FULL, "sale_deed": "unknown", "khata": "unknown"})
    s = rank([c], Preferences(), LOCS).scored[0]
    doc = next(f for f in s.factors if f.name == "documentation")
    assert doc.score == 0.4 and doc.known == pytest.approx(4 / 6)
    assert any("2 applicable document(s) is unknown" in m for m in s.missing_info)


def test_not_important_removes_factor_and_renormalises():
    w, ignored, _ = resolve_weights(Preferences(max_budget=2_000_000, objective="build_house",
                                                importance={"documentation": "not_important"}))
    assert "documentation" in ignored and "documentation" not in w
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["budget"] == pytest.approx(30 / 65)  # location also ignored: no location preference


def test_factors_without_preferences_are_ignored():
    w, ignored, notes = resolve_weights(Preferences())
    assert set(w) == {"connectivity", "documentation"} and set(ignored) == {"budget", "location", "purpose"}
    assert len(notes) == 3


def test_all_factors_unimportant_is_an_error():
    with pytest.raises(ValueError):
        resolve_weights(Preferences(importance={"connectivity": "not_important", "documentation": "not_important"}))


def test_purpose_prefers_converted_plot_for_house_and_farmland_for_farming():
    plot = cand()
    unconverted = cand(conversion_status="not_converted", layout_approval_status="unapproved_layout")
    farm = cand(property_type="agricultural_land", land_classification="agricultural",
                conversion_status="not_applicable", layout_approval_status="not_applicable")
    house = [s.candidate.id for s in rank([farm, unconverted, plot], Preferences(objective="build_house"), LOCS).scored]
    assert house[0] == plot.id and house[-1] == farm.id
    farming = rank([plot, farm], Preferences(objective="farming"), LOCS).scored
    assert farming[0].candidate.id == farm.id


def test_score_is_weighted_sum_of_factors():
    s = rank([cand(price=1_000_000, road_access="main_road")],
             Preferences(max_budget=2_500_000, objective="build_house", locality_ids=[2]), LOCS).scored[0]
    assert s.score == pytest.approx(100 * sum(f.weight * f.score for f in s.factors), abs=0.01)
    assert 0 <= s.score <= 100


# ------------------------------------------------------------------ explanations

def test_explanations_match_the_record():
    c = cand(price=2_000_000, road_access="main_road", docs_provided=5, docs_applicable=6, doc_completeness=0.8,
             doc_status={**DOCS_FULL, "khata": "not_provided"})
    s = rank([c], Preferences(max_budget=2_500_000, locality_ids=[1]), LOCS).scored[0]
    text = " ".join(s.reasons + s.tradeoffs)
    pct = re.search(r"asking price is (\d+)% of your maximum budget", text)
    if pct:
        assert int(pct.group(1)) == round(2_000_000 / 2_500_000 * 100)
    assert "Location: in Saptapur, one of your preferred localities." in s.reasons
    doc = next(f for f in s.factors if f.name == "documentation")
    assert "5 of 6 applicable documents" in doc.detail
    assert any("not verified" in v for v in s.verify)
    assert not any("verified." in r.lower() and "not" not in r.lower() for r in s.reasons)


def test_low_factor_becomes_tradeoff():
    s = rank([cand(road_access="unpaved")], Preferences(), LOCS).scored[0]
    assert any(t.startswith("Road access: an unpaved road") for t in s.tradeoffs)


# ------------------------------------------------------------------ stability

def test_identical_input_identical_ranking_and_tie_break():
    cs = [cand(price=2_000_000, doc_completeness=d) for d in (0.5, 0.9, 0.7)] + [cand(price=1_900_000, doc_completeness=0.9)]
    p = Preferences(objective="build_house")
    a = [s.candidate.id for s in rank(cs, p, LOCS).scored]
    b = [s.candidate.id for s in rank(list(reversed(cs)), p, LOCS).scored]
    assert a == b
    docs = [s.candidate.doc_completeness for s in rank(cs, Preferences(importance={"documentation": "not_important"}), LOCS).scored]
    assert docs == sorted(docs, reverse=True)  # equal scores break ties by documentation


def test_empty_result_counts_exclusions():
    r = rank([cand(price=5_000_000)], Preferences(max_budget=1_000_000), LOCS)
    assert r.scored == [] and r.excluded["Over your maximum budget"] == 1


# ------------------------------------------------------------------ API

def test_recommendations_api(client, seller_h, admin_h):
    cheap = create_listing(client, seller_h, approve_with=admin_h, asking_price_inr="1800000.00")
    create_listing(client, seller_h, approve_with=admin_h, asking_price_inr="4000000.00")
    create_listing(client, seller_h, asking_price_inr="1000000.00")  # pending: never recommended
    body = {"max_budget": "2500000", "property_types": ["residential_plot"], "locality_ids": [locality_id("Saptapur")],
            "objective": "build_house", "limit": 5}
    r = client.post("/api/v1/recommendations", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["candidates_considered"] == 2 and d["matched"] == 1
    assert d["results"][0]["property"]["id"] == cheap["id"]
    assert d["excluded"] == [{"reason": "Over your maximum budget", "count": 1}]
    assert d["engine_version"] == C.ENGINE_VERSION and "not a probability" in d["score_label"]
    res = d["results"][0]
    assert sum(f["weight"] for f in res["factors"]) == pytest.approx(1.0, abs=1e-3)
    with SessionLocal() as db:
        h = db.query(RecommendationHistory).one()
        assert h.result_property_ids == [cheap["id"]] and h.user_id is None


def test_recommendations_validation(client):
    assert client.post("/api/v1/recommendations", json={"locality_ids": [99999]}).status_code == 422
    assert client.post("/api/v1/recommendations", json={"min_budget": "500", "max_budget": "100"}).status_code == 422
    assert client.post("/api/v1/recommendations", json={"objective": "speculation"}).status_code == 422
    r = client.post("/api/v1/recommendations",
                    json={"importance": {"connectivity": "not_important", "documentation": "not_important"}})
    assert r.status_code == 422
    r = client.post("/api/v1/recommendations", json={"max_budget": "1000"})
    assert r.status_code == 200 and r.json()["results"] == [] and r.json()["notes"]


def test_compare_api(client, seller_h, admin_h):
    a = create_listing(client, seller_h, approve_with=admin_h)
    b = create_listing(client, seller_h, approve_with=admin_h, property_type="agricultural_land",
                       land_classification="agricultural", conversion_status="not_applicable",
                       layout_approval_status="not_applicable", intended_land_use="agricultural",
                       area_value="2", area_unit="acre", plot_width_ft=None, plot_length_ft=None,
                       asking_price_inr="3000000.00")
    r = client.post("/api/v1/properties/compare", json={"property_ids": [a["id"], b["id"]],
                                                        "preferences": {"objective": "build_house", "max_budget": "2500000"}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert any("different property types" in w for w in d["warnings"])
    items = {i["property"]["id"]: i for i in d["items"]}
    assert items[a["id"]]["match"]["rank"] == 1
    assert items[b["id"]]["excluded_reason"] == "Over your maximum budget"
    plain = client.post("/api/v1/properties/compare", json={"property_ids": [a["id"], b["id"]]}).json()
    assert all(i["match"] is None for i in plain["items"])
    assert client.post("/api/v1/properties/compare", json={"property_ids": [a["id"], a["id"]]}).status_code == 422
    assert client.post("/api/v1/properties/compare", json={"property_ids": [a["id"]]}).status_code == 422


def test_compare_hides_pending_listing(client, seller_h, admin_h):
    a = create_listing(client, seller_h, approve_with=admin_h)
    hidden = create_listing(client, seller_h)
    assert client.post("/api/v1/properties/compare", json={"property_ids": [a["id"], hidden["id"]]}).status_code == 404


def test_similar_api(client, seller_h, admin_h):
    a = create_listing(client, seller_h, approve_with=admin_h)
    twin = create_listing(client, seller_h, approve_with=admin_h, asking_price_inr="1900000.00")
    create_listing(client, seller_h, approve_with=admin_h, property_type="commercial_plot",
                   land_classification="non_agricultural_commercial", intended_land_use="commercial",
                   asking_price_inr="9000000.00", area_value="4000", plot_width_ft="50", plot_length_ft="80",
                   locality_id=locality_id("Vidyanagar"), latitude="15.37", longitude="75.12")
    r = client.get(f"/api/v1/properties/{a['id']}/similar")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items[0]["property"]["id"] == twin["id"]
    assert a["id"] not in [i["property"]["id"] for i in items]
    assert "Same type (residential plot)" in items[0]["similarities"]


def test_random_preferences_never_violate_strict_constraints():
    import random
    rng = random.Random(7)
    types = ["residential_plot", "independent_house", "agricultural_land", "commercial_plot", "commercial_building"]
    pool = [cand(property_type=rng.choice(types), price=rng.uniform(2e5, 2e7), area_sqft=rng.uniform(300, 2e5),
                 locality_id=rng.choice([1, 2, 3]), city=rng.choice(["Dharwad", "Hubballi"]),
                 road_access=rng.choice(list(C.ROAD_SCORE))) for _ in range(200)]
    for _ in range(200):
        p = Preferences(max_budget=round(rng.uniform(5e5, 1e7)), budget_strict=rng.random() < 0.5,
                        property_types=rng.sample(types, rng.randint(0, 2)), types_strict=rng.random() < 0.5,
                        locality_ids=rng.sample([1, 2, 3], rng.randint(0, 2)), location_strict=rng.random() < 0.5,
                        min_area_value=rng.choice([None, 1000, 20000]), area_strict=rng.random() < 0.5,
                        objective=rng.choice([None, *C.OBJECTIVES]))
        for s in rank(pool, p, LOCS).scored:
            c = s.candidate
            assert c.price <= float(p.max_budget) * (1 if p.budget_strict else 1.1) + 1e-6
            if p.types_strict and p.property_types:
                assert c.property_type in {t.value for t in p.property_types}
            if p.location_strict and p.locality_ids:
                assert c.locality_id in p.locality_ids
            if p.area_strict and p.min_area_value:
                assert c.area_sqft >= float(p.min_area_value)
            assert 0 <= s.score <= 100 and 0 <= s.coverage <= 1
