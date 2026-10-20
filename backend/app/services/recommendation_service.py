"""Advisor, comparison and similar-listing endpoints on top of the recommendation engine."""
from __future__ import annotations

import math
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.ml import pricing
from app.ml.features import build_features
from app.ml.recommendation import config as C
from app.ml.recommendation import knn
from app.ml.recommendation.engine import Candidate, Scored, exclusion_reason, factor_scores, explain, rank, \
    resolve_weights
from app.models import Locality, Property, RecommendationHistory, User
from app.models.enums import ListingStatus
from app.schemas.recommendation import (CompareItem, CompareRequest, CompareResponse, ExcludedReason, FactorScore,
                                        Preferences, PriceCheck, Recommendation, RecommendationRequest,
                                        RecommendationResponse, SimilarItem, SimilarResponse)
from app.services import prediction_service
from app.services import property_service as ps


def to_candidate(p: Property) -> Candidate:
    docs = ps.document_view(p)
    out, comp, n_prov, n_app = docs
    lat = p.latitude if p.latitude is not None else p.locality.center_lat
    lng = p.longitude if p.longitude is not None else p.locality.center_lng
    return Candidate(
        id=p.id, property_type=p.property_type.value, land_classification=p.land_classification.value,
        conversion_status=p.conversion_status.value, layout_approval_status=p.layout_approval_status.value,
        road_access=p.road_access.value, price=float(p.asking_price_inr), area_sqft=float(p.normalized_area_sqft),
        locality_id=p.locality_id, locality_name=p.locality.locality_name, city=p.locality.city,
        doc_completeness=comp, docs_provided=n_prov, docs_applicable=n_app,
        doc_status={d.document_type.value: d.availability.value for d in out if d.applicable},
        created_at=p.created_at, latitude=float(lat) if lat is not None else None,
        longitude=float(lng) if lng is not None else None, ref=(p, docs))


def approved_candidates(db: Session) -> list[Candidate]:
    rows = db.execute(ps._with_children(select(Property).where(Property.listing_status == ListingStatus.approved))
                      ).scalars().unique().all()
    return [to_candidate(p) for p in rows]


def locality_map(db: Session) -> dict[int, tuple[str, str]]:
    return {l.id: (l.locality_name, l.city) for l in db.execute(select(Locality)).scalars()}


def _validate(db: Session, prefs: Preferences, localities: dict) -> None:
    unknown = [i for i in prefs.locality_ids if i not in localities]
    if unknown:
        raise AppError(422, "validation_error", "Unknown locality",
                       [{"field": "locality_ids", "issue": f"no such locality: {unknown}"}])
    try:
        resolve_weights(prefs)
    except ValueError as e:
        raise AppError(422, "validation_error", "Mark at least one factor as important",
                       [{"field": "importance", "issue": str(e)}])


def price_checks(scored: list[Scored]) -> dict[uuid.UUID, PriceCheck]:
    """Asking price vs the M3 model's indicative range, when a model is available."""
    try:
        loaded = pricing.get_model()
    except pricing.ModelUnavailable:
        return {}
    if not scored:
        return {}
    records = []
    for s in scored:
        r = prediction_service._record_from_property(s.candidate.ref[0])
        r.pop("_coords_from_locality")
        records.append(r)
    preds = loaded.model.predict(build_features(records))
    iv = loaded.metadata["interval"]
    out = {}
    for s, v in zip(scored, preds):
        lo, hi = v * math.exp(iv["log_residual_low"]), v * math.exp(iv["log_residual_high"])
        pos = "below_range" if s.candidate.price < lo else "above_range" if s.candidate.price > hi else "within_range"
        note = {"within_range": "Asking price is within the price model's indicative range.",
                "above_range": "Asking price is above the price model's indicative range; worth checking why.",
                "below_range": "Asking price is below the price model's indicative range; check documents and access."}[pos]
        out[s.candidate.id] = PriceCheck(position=pos, estimate_inr=Decimal(int(round(v / 1000) * 1000)),
                                         note=note + " (Demonstration model; not a valuation.)")
    return out


def to_recommendation(s: Scored, rank_no: int, checks: dict) -> Recommendation:
    p, docs = s.candidate.ref
    return Recommendation(
        rank=rank_no, property=ps.summary(p, docs), score=s.score, data_coverage=s.coverage,
        factors=[FactorScore(factor=f.name, label=C.FACTOR_LABELS[f.name], weight=round(f.weight, 4),
                             score=round(f.score, 4), contribution=round(100 * f.weight * f.score, 2),
                             data_known=round(f.known, 3)) for f in s.factors],
        reasons=s.reasons, tradeoffs=s.tradeoffs, missing_info=s.missing_info, verify_independently=s.verify,
        price_check=checks.get(s.candidate.id))


def recommend(db: Session, req: RecommendationRequest, user: User | None) -> RecommendationResponse:
    localities = locality_map(db)
    _validate(db, req, localities)
    candidates = approved_candidates(db)
    result = rank(candidates, req, localities)
    top = result.scored[:req.limit]
    checks = price_checks(top)
    notes = list(result.notes)
    if not result.scored:
        notes.append("No listing meets all of your strict requirements. Relax the ones with the most exclusions.")
    db.add(RecommendationHistory(user_id=user.id if user else None, engine_version=C.ENGINE_VERSION,
                                 input_criteria=req.model_dump(mode="json"),
                                 result_property_ids=[str(s.candidate.id) for s in top]))
    db.commit()
    return RecommendationResponse(
        results=[to_recommendation(s, i + 1, checks) for i, s in enumerate(top)],
        candidates_considered=len(candidates), matched=len(result.scored),
        excluded=[ExcludedReason(reason=r, count=n) for r, n in result.excluded.most_common()],
        weights_used={k: round(v, 4) for k, v in result.weights.items()}, factors_ignored=result.ignored,
        notes=notes, engine_version=C.ENGINE_VERSION, score_label=C.SCORE_LABEL,
        is_synthetic_data=any(c.ref[0].is_synthetic for c in candidates))


def match_details(db: Session, props: list[Property], prefs: Preferences) -> list[tuple[Recommendation, str | None]]:
    """Score each listing against the preferences and rank them among themselves (used by Compare and the
    assistant). Returns (match with rank, strict requirement it fails or None) in input order."""
    localities = locality_map(db)
    _validate(db, prefs, localities)
    weights, _, _ = resolve_weights(prefs)
    cands = [to_candidate(p) for p in props]
    out = []
    for c in cands:
        reason = exclusion_reason(c, prefs, localities)
        factors = factor_scores(c, prefs, weights, localities)
        r, t, m, v = explain(c, factors, prefs)
        s = Scored(c, round(100 * sum(f.weight * f.score for f in factors), 2),
                   round(sum(f.weight * f.known for f in factors), 3), factors, r, t, m, v)
        out.append((to_recommendation(s, 0, {}), reason))
    # Same tie-break as the ranking: more documents declared, then lower price.
    order = sorted(range(len(out)), key=lambda i: (-out[i][0].score, -cands[i].doc_completeness,
                                                    cands[i].price, str(cands[i].id)))
    for rank_no, i in enumerate(order, 1):
        out[i][0].rank = rank_no
    return out


def compare(db: Session, req: CompareRequest, user: User | None) -> CompareResponse:
    if len(set(req.property_ids)) != len(req.property_ids):
        raise AppError(422, "validation_error", "Choose different listings to compare",
                       [{"field": "property_ids", "issue": "duplicate id"}])
    props = [ps.get_visible_property(db, pid, user) for pid in req.property_ids]
    cands = [to_candidate(p) for p in props]
    warnings = []
    types = {c.property_type for c in cands}
    if len(types) > 1:
        warnings.append("These listings are different property types, so price per sq ft is not a like-for-like "
                        "comparison (farmland, plots and buildings are priced differently).")
    if len({c.city for c in cands}) > 1:
        warnings.append("The listings are in different cities.")
    if any(c.ref[0].is_synthetic for c in cands):
        warnings.append("Synthetic demonstration listings; prices are not market data.")
    if any(not c.ref[0].is_synthetic and c.ref[0].source_url for c in cands):
        warnings.append("Real listings copied from a public site: unverified asking prices, not sale prices.")
    matches = match_details(db, props, req.preferences) if req.preferences else [(None, None)] * len(props)
    items = [CompareItem(property=ps.summary(*c.ref), match=m, excluded_reason=reason)
             for c, (m, reason) in zip(cands, matches)]
    return CompareResponse(items=items, warnings=warnings, engine_version=C.ENGINE_VERSION,
                           score_label=C.SCORE_LABEL)


def similar_listings(db: Session, property_id: uuid.UUID, user: User | None, k: int = 5) -> SimilarResponse:
    target = to_candidate(ps.get_visible_property(db, property_id, user))
    pool = approved_candidates(db)
    items = [SimilarItem(property=ps.summary(*c.ref), distance=round(d, 3), similarities=knn.similarities(target, c))
             for c, d in knn.similar(target, pool, k)]
    return SimilarResponse(items=items, method=knn.METHOD)
