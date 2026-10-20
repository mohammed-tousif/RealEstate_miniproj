"""Evaluate the recommendation engine on scripted scenarios (BLUEPRINT Part E).

There are no genuine relevance labels (no real buyers rated these listings), so this
script does NOT report Precision@K as if there were. Instead it measures:

1. Constraint satisfaction: every result must respect every strict requirement.
   Checked by an independent checker written here, not by the engine's own filter.
2. Agreement with rule-derived expectations: for each scenario a listing is "ideal"
   by rules written before running the engine (right type and legal status for the
   purpose, inside budget and preferred area, known road access, most documents
   declared). We report how often an ideal listing is ranked above a non-ideal one.
   These labels are rule-derived, not human judgements.
3. Baselines on the same filtered set: cheapest-first and newest-first.
4. Stability: random ±20% changes to the weights, measured with Kendall's tau.
5. KNN retrieval towards a "preference vector" vs the weighted ranking.

It builds a throwaway SQLite database from the synthetic CSV, so it never touches
your own database. Output: ml/reports/recommender_evaluation.md (+ .json).

    python scripts/evaluate_recommender.py
"""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="propwise-eval-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'eval.db').as_posix()}"
os.environ.setdefault("BCRYPT_ROUNDS", "4")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scipy.stats import kendalltau  # noqa: E402  (installed with scikit-learn)

from app.core.config import REPO_DIR  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.ml.recommendation import config as C  # noqa: E402
from app.ml.recommendation import knn  # noqa: E402
from app.ml.recommendation.engine import Candidate, min_area_sqft, purpose_score, rank  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.schemas.recommendation import Preferences  # noqa: E402
from app.services import recommendation_service as rs  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_db  # noqa: E402

K = 5
SEED = 42

# Scenario definitions use locality *names*; they are resolved to ids after seeding.
SCENARIOS = [
    ("Demo: ₹25 lakh residential plot, Hubballi or Dharwad, long-term",
     dict(max_budget=2_500_000, property_types=["residential_plot"], cities=["Hubballi", "Dharwad"],
          objective="long_term_investment")),
    ("₹20 lakh plot to build a house in Dharwad",
     dict(max_budget=2_000_000, property_types=["residential_plot"], cities=["Dharwad"], location_strict=True,
          objective="build_house")),
    ("₹35 lakh house plot, Saptapur or Kalyan Nagar preferred",
     dict(max_budget=3_500_000, localities=["Saptapur", "Kalyan Nagar"], objective="build_house")),
    ("₹60 lakh farmland for farming, at least 2 acres",
     dict(max_budget=6_000_000, property_types=["agricultural_land"], min_area_value=2, min_area_unit="acre",
          area_strict=True, objective="farming")),
    ("₹40 lakh farmland as long-term investment, flexible budget",
     dict(max_budget=4_000_000, budget_strict=False, property_types=["agricultural_land"],
          objective="long_term_investment")),
    ("₹1 crore commercial plot in Hubballi",
     dict(max_budget=10_000_000, property_types=["commercial_plot"], cities=["Hubballi"], location_strict=True,
          objective="commercial_use")),
    ("₹1.5 crore commercial use, any commercial type",
     dict(max_budget=15_000_000, property_types=["commercial_plot", "commercial_building"],
          objective="commercial_use")),
    ("₹80 lakh independent house in Hubballi",
     dict(max_budget=8_000_000, property_types=["independent_house"], cities=["Hubballi"], objective="build_house")),
    ("₹15 lakh, anything to build on, documents very important",
     dict(max_budget=1_500_000, objective="build_house", importance={"documentation": "very_important"})),
    ("₹30 lakh plot, road access very important",
     dict(max_budget=3_000_000, property_types=["residential_plot"], objective="build_house",
          importance={"connectivity": "very_important"})),
    ("₹25 lakh plot, location does not matter",
     dict(max_budget=2_500_000, property_types=["residential_plot"], cities=["Dharwad"], objective="build_house",
          importance={"location": "not_important"})),
    ("₹50 lakh, preferred type plot but flexible",
     dict(max_budget=5_000_000, property_types=["residential_plot"], types_strict=False,
          objective="long_term_investment")),
    ("Vidyanagar only, house plot, at least 1,200 sq ft",
     dict(localities=["Vidyanagar"], location_strict=True, min_area_value=1200, area_strict=True,
          objective="build_house")),
    ("₹2 lakh plot (expected: no results)",
     dict(max_budget=200_000, property_types=["residential_plot"], objective="build_house")),
    ("₹10–20 lakh, strict range, long-term",
     dict(min_budget=1_000_000, max_budget=2_000_000, objective="long_term_investment")),
]


def independent_violations(c: Candidate, p: Preferences) -> list[str]:
    """Re-implements the strict rules from the specification, independently of the engine."""
    v = []
    if p.max_budget is not None:
        limit = float(p.max_budget) * (1.0 if p.budget_strict else 1.10)
        if c.price > limit + 1e-6:
            v.append("budget")
    if p.budget_strict and p.min_budget is not None and c.price < float(p.min_budget):
        v.append("min_budget")
    if p.types_strict and p.property_types and c.property_type not in [t.value for t in p.property_types]:
        v.append("type")
    if p.location_strict and (p.cities or p.locality_ids):
        if not (c.locality_id in p.locality_ids or c.city in p.cities):
            v.append("location")
    if p.area_strict and p.min_area_value is not None and c.area_sqft < min_area_sqft(p) - 1e-6:
        v.append("area")
    return v


IDEAL_STATUS = {
    "build_house": lambda c: c.property_type == "residential_plot" and c.conversion_status == "converted_claimed"
    and c.layout_approval_status == "approved_layout_claimed" and c.land_classification == "non_agricultural_residential",
    "long_term_investment": lambda c: c.property_type in ("residential_plot", "commercial_plot", "agricultural_land")
    and c.conversion_status in ("converted_claimed", "not_applicable")
    and c.layout_approval_status in ("approved_layout_claimed", "not_applicable"),
    "farming": lambda c: c.property_type == "agricultural_land" and c.land_classification == "agricultural",
    "commercial_use": lambda c: c.property_type in ("commercial_plot", "commercial_building")
    and c.land_classification == "non_agricultural_commercial" and c.conversion_status == "converted_claimed",
}


def is_ideal(c: Candidate, p: Preferences) -> bool:
    """Rule-derived 'clearly good match', written from the specification before running the engine."""
    if independent_violations(c, p):
        return False
    if p.objective and not IDEAL_STATUS[p.objective](c):
        return False
    if p.property_types and c.property_type not in [t.value for t in p.property_types]:
        return False
    if p.max_budget is not None and not (0.6 * float(p.max_budget) <= c.price <= float(p.max_budget)):
        return False
    if (p.cities or p.locality_ids) and p.importance.get("location") != "not_important":
        if not (c.locality_id in p.locality_ids or (not p.locality_ids and c.city in p.cities)):
            return False
    if c.road_access in ("unknown", "no_direct_access", "unpaved"):
        return False
    return c.doc_completeness >= 0.7


def pairwise_agreement(order: list[Candidate], p: Preferences) -> tuple[float | None, int, int]:
    ideal = [is_ideal(c, p) for c in order]
    agree = total = 0
    for i, a in enumerate(ideal):
        for j in range(i + 1, len(ideal)):
            if a != ideal[j]:
                total += 1
                agree += a  # ideal ranked above non-ideal
    return (agree / total if total else None), sum(ideal), total


def top_stats(cands: list[Candidate], p: Preferences) -> dict:
    top = cands[:K]
    if not top:
        return {"n": 0}
    n_ideal = sum(is_ideal(c, p) for c in cands)
    return {
        "n": len(top),
        "ideal_recall": sum(is_ideal(c, p) for c in top) / min(K, n_ideal) if n_ideal else None,
        "ideal_share": sum(is_ideal(c, p) for c in top) / len(top),
        "avg_doc_completeness": statistics.mean(c.doc_completeness for c in top),
        "road_known_share": sum(c.road_access != "unknown" for c in top) / len(top),
        "avg_purpose_score": statistics.mean(purpose_score(c, p.objective)[0] for c in top) if p.objective else None,
    }


def stability(cands: list[Candidate], p: Preferences, localities, base_ids: list) -> dict:
    rng = random.Random(SEED)
    taus, overlaps = [], []
    base_rank = {cid: i for i, cid in enumerate(base_ids)}
    for _ in range(20):
        w = {f: C.DEFAULT_WEIGHTS[f] * rng.uniform(0.8, 1.2) for f in C.FACTORS}
        ids = [s.candidate.id for s in rank(cands, p, localities, weight_overrides=w).scored]
        if len(ids) >= 2:
            taus.append(kendalltau([base_rank[i] for i in ids], list(range(len(ids)))).statistic)
        overlaps.append(len(set(ids[:K]) & set(base_ids[:K])) / max(1, min(K, len(base_ids))))
    return {"kendall_tau_mean": statistics.mean(taus) if taus else None,
            "kendall_tau_min": min(taus) if taus else None,
            "top5_overlap_mean": statistics.mean(overlaps)}


def preference_vector(p: Preferences, pool: list[Candidate], localities, centroids) -> Candidate:
    """A pseudo-listing describing what the buyer asked for, used as the KNN query."""
    ptype = p.property_types[0].value if p.property_types else "residential_plot"
    if p.locality_ids:
        lat, lng = centroids[p.locality_ids[0]]
        city = localities[p.locality_ids[0]][1]
    else:
        city = p.cities[0] if p.cities else "Dharwad"
        lat, lng = {"Hubballi": (15.3647, 75.1240), "Dharwad": (15.4589, 75.0078)}[city]
    same = [c.area_sqft for c in pool if c.property_type == ptype] or [1200.0]
    area = min_area_sqft(p) or statistics.median(same)
    price = 0.8 * float(p.max_budget) if p.max_budget else statistics.median(c.price for c in pool)
    return Candidate(id=None, property_type=ptype, land_classification="unknown", conversion_status="unknown",
                     layout_approval_status="unknown", road_access="paved_internal", price=price, area_sqft=area,
                     locality_id=-1, locality_name="query", city=city, doc_completeness=1.0, docs_provided=0,
                     docs_applicable=0, latitude=lat, longitude=lng)


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        locs = seed_db.upsert_reference(db)
        users = seed_db.upsert_users(db, "eval-only-password-1")
        sellers = [u for u in users.values() if u.role == UserRole.seller]
        seed_db.load_listings(db, seed_db.DEFAULT_CSV, locs, sellers)
        db.commit()
        pool = rs.approved_candidates(db)
        localities = rs.locality_map(db)
        by_name = {name: i for i, (name, _) in localities.items()}
        centroids = {l.id: (float(l.center_lat), float(l.center_lng)) for l in locs.values()}

    rows = []
    for name, spec in SCENARIOS:
        spec = dict(spec)
        if "localities" in spec:
            spec["locality_ids"] = [by_name[n] for n in spec.pop("localities")]
        p = Preferences(**spec)
        result = rank(pool, p, localities)
        ordered = [s.candidate for s in result.scored]
        violations = sum(bool(independent_violations(c, p)) for c in ordered)
        eligible = [c for c in pool if not independent_violations(c, p)]
        agreement, n_ideal, pairs = pairwise_agreement(ordered, p)
        cheapest = sorted(eligible, key=lambda c: (c.price, str(c.id)))
        newest = sorted(eligible, key=lambda c: (c.created_at.replace(tzinfo=None), str(c.id)), reverse=True)
        knn_top = [c for c, _ in knn.similar(preference_vector(p, pool, localities, centroids), pool, K)] if ordered else []
        rows.append({
            "scenario": name,
            "matched": len(ordered),
            "eligible_independent": len(eligible),
            "constraint_violations": violations,
            "excluded": dict(result.excluded),
            "ideal_listings": n_ideal,
            "pairwise_agreement": agreement,
            "pairs": pairs,
            "weighted_top5": top_stats(ordered, p),
            "cheapest_top5": top_stats(cheapest, p),
            "newest_top5": top_stats(newest, p),
            "stability": stability(pool, p, localities, [c.id for c in ordered]) if len(ordered) > 1 else None,
            "knn_top5_violations": sum(bool(independent_violations(c, p)) for c in knn_top),
            "knn_top5_overlap_with_weighted": (len({c.id for c in knn_top} & {c.id for c in ordered[:K]}) / K
                                               if ordered else None),
            "top_coverage_mean": statistics.mean(s.coverage for s in result.scored[:K]) if ordered else None,
        })

    out = REPO_DIR / "ml" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "recommender_evaluation.json").write_text(json.dumps({"engine_version": C.ENGINE_VERSION, "k": K,
                                                                 "candidates": len(pool), "scenarios": rows},
                                                                indent=2, default=str), encoding="utf-8")
    (out / "recommender_evaluation.md").write_text(report(rows, len(pool)), encoding="utf-8")
    total_viol = sum(r["constraint_violations"] for r in rows)
    print(f"{len(rows)} scenarios over {len(pool)} approved synthetic listings; constraint violations: {total_viol}")
    print(f"Report written to {out / 'recommender_evaluation.md'}")


def _pct(v):
    return "–" if v is None else f"{v * 100:.0f}%"


def _num(v, d=2):
    return "–" if v is None else f"{v:.{d}f}"


def report(rows: list[dict], n_pool: int) -> str:
    def mean_of(key, sub):
        vals = [r[key][sub] for r in rows if r[key].get("n") and r[key].get(sub) is not None]
        return statistics.mean(vals) if vals else None

    agreements = [r["pairwise_agreement"] for r in rows if r["pairwise_agreement"] is not None]
    taus = [r["stability"]["kendall_tau_mean"] for r in rows if r["stability"] and r["stability"]["kendall_tau_mean"] is not None]
    lines = [
        "# Recommendation engine evaluation",
        "",
        f"Engine `{C.ENGINE_VERSION}`, {len(rows)} scripted scenarios, {n_pool} approved **synthetic** listings, "
        f"top-{K}. Generated by `scripts/evaluate_recommender.py`; every number below comes from that run.",
        "",
        "> There are no genuine relevance labels, so no Precision@K is reported. \"Ideal\" listings are defined "
        "by rules written from the specification (right type and legal status for the purpose, inside budget and "
        "preferred area, known and usable road access, at least 70% documentation declared). Agreement with those "
        "rules shows the engine does what it was designed to do, not that buyers would agree with it.",
        "",
        "## Summary",
        "",
        f"- Constraint violations (independent checker, all scenarios): **{sum(r['constraint_violations'] for r in rows)}**",
        f"- Mean pairwise agreement with rule-derived expectations (partly by construction, since both follow the "
        f"same specification): **{_pct(statistics.mean(agreements)) if agreements else '–'}** "
        f"over {sum(r['pairs'] for r in rows)} ideal/non-ideal pairs",
        f"- Mean Kendall's tau under ±20% random weight changes: **{_num(statistics.mean(taus)) if taus else '–'}** "
        "(1.0 = order unchanged)",
        "",
        "| Top-5, mean over scenarios | Weighted engine | Cheapest first | Newest first |",
        "|---|---|---|---|",
        f"| Available ideal listings that reached the top 5 | {_pct(mean_of('weighted_top5', 'ideal_recall'))} | "
        f"{_pct(mean_of('cheapest_top5', 'ideal_recall'))} | {_pct(mean_of('newest_top5', 'ideal_recall'))} |",
        f"| Share of top 5 that is rule-derived ideal (capped by how many exist) | {_pct(mean_of('weighted_top5', 'ideal_share'))} | "
        f"{_pct(mean_of('cheapest_top5', 'ideal_share'))} | {_pct(mean_of('newest_top5', 'ideal_share'))} |",
        f"| Documentation completeness | {_pct(mean_of('weighted_top5', 'avg_doc_completeness'))} | "
        f"{_pct(mean_of('cheapest_top5', 'avg_doc_completeness'))} | {_pct(mean_of('newest_top5', 'avg_doc_completeness'))} |",
        f"| Road access known | {_pct(mean_of('weighted_top5', 'road_known_share'))} | "
        f"{_pct(mean_of('cheapest_top5', 'road_known_share'))} | {_pct(mean_of('newest_top5', 'road_known_share'))} |",
        f"| Purpose suitability (engine's own table, so partly circular) | {_num(mean_of('weighted_top5', 'avg_purpose_score'))} | "
        f"{_num(mean_of('cheapest_top5', 'avg_purpose_score'))} | {_num(mean_of('newest_top5', 'avg_purpose_score'))} |",
        "",
        "The baselines rank the same listings that pass the strict filters, so they never violate constraints either; "
        "the comparison is about what rises to the top.",
        "",
        "## Per scenario",
        "",
        "| Scenario | Matched | Violations | Ideal | Pairwise agreement | Ideal in top 5 (engine / cheapest / newest) | Tau | KNN violations in top 5 | KNN overlap with engine |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        w, c, n = r["weighted_top5"], r["cheapest_top5"], r["newest_top5"]
        lines.append(
            f"| {r['scenario']} | {r['matched']} | {r['constraint_violations']} | {r['ideal_listings']} | "
            f"{_pct(r['pairwise_agreement'])} | {_pct(w.get('ideal_share'))} / {_pct(c.get('ideal_share'))} / "
            f"{_pct(n.get('ideal_share'))} | {_num(r['stability']['kendall_tau_mean']) if r['stability'] else '–'} | "
            f"{r['knn_top5_violations'] if r['matched'] else '–'} | {_pct(r['knn_top5_overlap_with_weighted'])} |")
    empty = [r for r in rows if r["matched"] == 0]
    lines += [
        "",
        "## Notes",
        "",
        "- **KNN towards a preference vector** (a pseudo-listing at 80% of the budget, the preferred type, area and "
        "location) has no notion of strict requirements, so it can return listings that break them. That is why "
        "KNN is used only for \"similar listings\" on a property page, and the weighted engine for the Advisor.",
        "- **Stability:** weights are design assumptions; the tau figures show how much the order depends on them.",
    ]
    for r in empty:
        lines.append(f"- *{r['scenario']}*: no results; exclusions were {r['excluded']}. The Advisor reports these "
                     "counts so the user knows which requirement to relax.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
