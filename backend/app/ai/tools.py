"""Read-only tools the assistant can call (BLUEPRINT Part E, "How the LLM accesses backend tools").

Every tool has a Pydantic input model. The JSON schema sent to the LLM is generated from it and the
LLM's arguments are re-validated with it before anything runs. Tools run with the caller's own
permissions (a guest never sees pending listings or seller details), cannot write, and return only
database facts and model outputs, each labelled as such.
"""
from __future__ import annotations

import json
import statistics
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import glossary
from app.ai.format import area_text, inr
from app.core.errors import AppError
from app.models import Locality, Property, User
from app.models.enums import LABELS, AreaUnit, DocumentType, ListingStatus, PropertyType, RoadAccess
from app.schemas.prediction import PriceEstimateIn
from app.schemas.property import PropertySummary
from app.schemas.recommendation import CompareRequest, Preferences, RecommendationRequest
from app.services import document_rules, prediction_service, recommendation_service
from app.services import property_service as ps
from app.services.risk_flags import risk_flags

City = Literal["Hubballi", "Dharwad"]
SYNTHETIC_NOTE = ("Listings with is_synthetic=true are synthetic demonstration data, not real properties or market "
                  "prices. Listings with is_synthetic=false and a source_url are real third-party listings copied "
                  "from a public site: unverified asking prices, not sale prices.")


@dataclass
class ToolContext:
    db: Session
    user: User | None
    # Every listing a tool returned in this conversation turn: the only listings the answer may cite.
    seen: dict[str, PropertySummary] = field(default_factory=dict)
    # Listings from the most recent tool that returned a list, in its order (cards for the UI).
    last_listed: list[str] = field(default_factory=list)
    used_model_estimate: bool = False
    # The buyer's Advisor preferences sent with the chat request, if any (used to explain rankings).
    preferences: Preferences | None = None


def _label(enum_name: str, value: str) -> str:
    return LABELS.get((enum_name, value), value.replace("_", " ").capitalize())


def _card(ctx: ToolContext, s: PropertySummary) -> dict:
    sid = str(s.id)
    ctx.seen[sid] = s
    return {
        "id": sid, "link": f"/properties/{sid}", "title": s.title,
        "property_type": _label("PropertyType", s.property_type.value),
        "asking_price": inr(s.asking_price_inr), "asking_price_inr": str(s.asking_price_inr),
        "area": area_text(s.normalized_area_sqft, s.area_value, s.area_unit.value),
        "price_per_sqft": inr(s.price_per_sqft_inr, exact=True),
        "locality": s.locality.locality_name, "city": s.locality.city,
        "road_access": _label("RoadAccess", s.road_access.value),
        "documents_declared": f"{s.documents_provided} of {s.documents_applicable} applicable",
        "documentation_completeness": round(s.documentation_completeness, 2),
        "is_synthetic": s.is_synthetic,
        **({"source_url": s.source_url} if s.source_url else {}),
    }


def _locality(ctx: ToolContext, name: str | None, city: str | None) -> Locality | None:
    if not name:
        return None
    q = select(Locality).where(Locality.locality_name.ilike(name.strip()))
    if city:
        q = q.where(Locality.city == city)
    loc = ctx.db.execute(q).scalars().first()
    if loc is None:
        names = sorted(f"{l.locality_name} ({l.city})" for l in ctx.db.execute(select(Locality)).scalars())
        raise AppError(422, "unknown_locality", f"Unknown locality '{name}'. Known localities: {', '.join(names)}")
    return loc


# ------------------------------------------------------------------ inputs

class SearchArgs(BaseModel):
    text: str | None = Field(default=None, max_length=100, description="free-text match on title, description, locality")
    city: City | None = None
    locality: str | None = Field(default=None, max_length=80, description="locality name, e.g. Saptapur")
    property_types: list[PropertyType] = Field(default_factory=list, max_length=5)
    min_price_inr: Decimal | None = Field(default=None, ge=0)
    max_price_inr: Decimal | None = Field(default=None, gt=0)
    min_area_sqft: Decimal | None = Field(default=None, ge=0)
    max_area_sqft: Decimal | None = Field(default=None, gt=0)
    road_access: list[RoadAccess] = Field(default_factory=list, max_length=6)
    has_documents: list[DocumentType] = Field(default_factory=list, max_length=12,
                                              description="only listings declaring these documents as provided")
    sort: Literal["price_asc", "price_desc", "area_asc", "area_desc", "newest"] = "price_asc"
    limit: int = Field(default=5, ge=1, le=10)


class PropertyIdArgs(BaseModel):
    property_id: uuid.UUID


class RecommendArgs(BaseModel):
    max_budget_inr: Decimal | None = Field(default=None, gt=0)
    min_budget_inr: Decimal | None = Field(default=None, gt=0)
    budget_strict: bool = Field(default=True, description="exclude listings above max_budget_inr")
    property_types: list[PropertyType] = Field(default_factory=list, max_length=5)
    cities: list[City] = Field(default_factory=list, max_length=2)
    localities: list[str] = Field(default_factory=list, max_length=10)
    min_area_value: Decimal | None = Field(default=None, gt=0)
    min_area_unit: AreaUnit = AreaUnit.sqft
    objective: Literal["build_house", "long_term_investment", "farming", "commercial_use"] | None = None
    limit: int = Field(default=5, ge=1, le=10)


class PriceArgs(BaseModel):
    property_id: uuid.UUID | None = Field(default=None, description="estimate an existing listing, or give the fields")
    locality: str | None = Field(default=None, max_length=80)
    city: City | None = None
    property_type: PropertyType | None = None
    area_value: Decimal | None = Field(default=None, gt=0)
    area_unit: AreaUnit | None = None
    road_access: RoadAccess = RoadAccess.unknown


class CompareArgs(BaseModel):
    property_ids: list[uuid.UUID] = Field(min_length=2, max_length=3)


class RankingArgs(BaseModel):
    property_ids: list[uuid.UUID] = Field(min_length=1, max_length=3)
    # Optional: the buyer's stated needs. When none are given, the Advisor preferences saved in the
    # buyer's browser (sent with the chat) are used.
    max_budget_inr: Decimal | None = Field(default=None, gt=0)
    property_types: list[PropertyType] = Field(default_factory=list, max_length=5)
    cities: list[City] = Field(default_factory=list, max_length=2)
    objective: Literal["build_house", "long_term_investment", "farming", "commercial_use"] | None = None


class DocumentArgs(BaseModel):
    document_type: DocumentType | None = Field(default=None, description="explain one document type")
    property_id: uuid.UUID | None = Field(default=None, description="document statuses declared for one listing")
    property_type: PropertyType | None = Field(default=None, description="which documents apply to this property type")


class LocationArgs(BaseModel):
    city: City | None = None
    locality: str | None = Field(default=None, max_length=80)
    property_type: PropertyType | None = None


class TermArgs(BaseModel):
    term: str = Field(min_length=1, max_length=80)


# ------------------------------------------------------------------ implementations

def search_properties(ctx: ToolContext, a: SearchArgs) -> dict:
    loc = _locality(ctx, a.locality, a.city)
    f = ps.PropertyFilters(q=a.text, city=a.city, locality_id=loc.id if loc else None,
                           property_type=a.property_types or None, min_price=a.min_price_inr,
                           max_price=a.max_price_inr, min_area_sqft=a.min_area_sqft, max_area_sqft=a.max_area_sqft,
                           road_access=a.road_access or None, has_document=a.has_documents or None, sort=a.sort,
                           page_size=a.limit)
    res = ps.list_properties(ctx.db, ctx.user, f)
    cards = [_card(ctx, s) for s in res.items]
    ctx.last_listed = [c["id"] for c in cards]
    return {"source": "listing database", "total_matches": res.total, "returned": len(cards), "listings": cards,
            "note": SYNTHETIC_NOTE}


def get_property_details(ctx: ToolContext, a: PropertyIdArgs) -> dict:
    p = ps.get_visible_property(ctx.db, a.property_id, ctx.user)
    d = ps.detail(p, ctx.user)
    card = _card(ctx, ps.summary(p))
    ctx.last_listed = [card["id"]]
    return {"source": "listing database", "listing": card,
            "seller_description": d.description,
            "land": {"land_classification": _label("LandClassification", d.land_classification.value),
                     "conversion_status": _label("ConversionStatus", d.conversion_status.value),
                     "layout_approval_status": _label("LayoutApprovalStatus", d.layout_approval_status.value),
                     "intended_land_use": _label("IntendedLandUse", d.intended_land_use.value),
                     "note": "Land and approval statuses are the seller's claims, not verified facts."},
            "documents": [{"document": doc.label, "status": doc.display_label} for doc in d.documents
                          if doc.applicable],
            "amenities": [a.label + (f" (~{a.approx_distance_km} km)" if a.approx_distance_km is not None else "")
                          for a in d.amenities],
            "data_warnings": d.data_warnings,
            "risk_flags": [f.message for f in d.risk_flags]}


def recommend_properties(ctx: ToolContext, a: RecommendArgs) -> dict:
    loc_ids = [_locality(ctx, n, None).id for n in a.localities]
    req = RecommendationRequest(max_budget=a.max_budget_inr, min_budget=a.min_budget_inr,
                                budget_strict=a.budget_strict, property_types=a.property_types, cities=a.cities,
                                locality_ids=loc_ids, min_area_value=a.min_area_value, min_area_unit=a.min_area_unit,
                                objective=a.objective, limit=a.limit)
    res = recommendation_service.recommend(ctx.db, req, ctx.user)
    out = []
    for r in res.results:
        c = _card(ctx, r.property)
        c.update({"rank": r.rank, "suitability_score": r.score, "why_it_matches": r.reasons,
                  "trade_offs": r.tradeoffs, "verify_independently": r.verify_independently,
                  "price_check": r.price_check.note if r.price_check else None})
        out.append(c)
    ctx.last_listed = [c["id"] for c in out]
    return {"source": f"recommendation engine {res.engine_version}", "score_meaning": res.score_label,
            "candidates_considered": res.candidates_considered, "matched_all_strict_requirements": res.matched,
            "excluded_counts": {e.reason: e.count for e in res.excluded}, "notes": res.notes,
            "recommendations": out, "note": SYNTHETIC_NOTE}


def predict_property_price(ctx: ToolContext, a: PriceArgs) -> dict:
    if a.property_id is not None:
        body = PriceEstimateIn(property_id=a.property_id)
    else:
        loc = _locality(ctx, a.locality, a.city)
        try:
            body = PriceEstimateIn(locality_id=loc.id if loc else None, property_type=a.property_type,
                                   area_value=a.area_value, area_unit=a.area_unit, road_access=a.road_access)
        except ValidationError:
            raise AppError(422, "missing_fields",
                           "Give property_id, or locality, property_type, area_value and area_unit")
    est = prediction_service.estimate_price(ctx.db, body, ctx.user)
    ctx.used_model_estimate = True
    if a.property_id is not None:
        p = ps.get_visible_property(ctx.db, a.property_id, ctx.user)
        _card(ctx, ps.summary(p))
    r = est.indicative_range_inr
    return {"source": f"price model {est.model.label} ({est.model.version})", "kind": "ML estimate",
            "estimated_asking_price": inr(est.predicted_asking_price_inr),
            "indicative_range": f"{inr(r.low)} to {inr(r.high)}",
            "range_coverage_on_test_data": r.measured_test_coverage,
            "quoted_price": inr(est.quoted_price_inr) if est.quoted_price_inr else None,
            "quoted_vs_estimate_pct": est.quoted_vs_estimate_pct, "quoted_position": est.quoted_position,
            "comparable_asking_prices": [f"{c.title}: {inr(c.asking_price_inr)} ({c.locality})"
                                         for c in est.comparables[:3]],
            "warnings": est.warnings, "disclaimer": est.disclaimer}


def _match_dict(m, reason) -> dict:
    return {"rank_among_these": m.rank, "suitability_score": m.score, "data_coverage": m.data_coverage,
            "factor_contributions": {f.label: {"score_0_to_1": f.score, "weight": f.weight,
                                               "points_out_of_100": f.contribution} for f in m.factors},
            "why_it_matches": m.reasons, "trade_offs": m.tradeoffs, "missing_information": m.missing_info,
            "verify_independently": m.verify_independently, "fails_strict_requirement": reason}


def compare_properties(ctx: ToolContext, a: CompareArgs) -> dict:
    res = recommendation_service.compare(ctx.db, CompareRequest(property_ids=a.property_ids,
                                                                preferences=ctx.preferences), ctx.user)
    cards = []
    for it in res.items:
        c = _card(ctx, it.property)
        p = ps.get_visible_property(ctx.db, it.property.id, ctx.user)
        c["risk_flags"] = [f.message for f in risk_flags(p, include_price=False)]
        if it.match:
            c["match_for_saved_preferences"] = _match_dict(it.match, it.excluded_reason)
        cards.append(c)
    ctx.last_listed = [c["id"] for c in cards]
    return {"source": "listing database", "listings": cards, "warnings": res.warnings,
            "score_meaning": res.score_label if ctx.preferences else None}


def explain_ranking(ctx: ToolContext, a: RankingArgs) -> dict:
    stated = a.max_budget_inr or a.property_types or a.cities or a.objective
    if stated:
        # Ranking named listings: stated needs score them but do not exclude them.
        prefs = Preferences(max_budget=a.max_budget_inr, budget_strict=False, property_types=a.property_types,
                            types_strict=False, cities=a.cities, objective=a.objective)
        basis = "preferences stated in this conversation"
    elif ctx.preferences is not None:
        prefs, basis = ctx.preferences, "the buyer's saved Advisor preferences"
    else:
        return {"error": "no_preferences",
                "message": "A ranking needs the buyer's preferences. Ask for budget, property type, city and "
                           "objective, or suggest setting them in the Advisor."}
    props = [ps.get_visible_property(ctx.db, pid, ctx.user) for pid in dict.fromkeys(a.property_ids)]
    out = []
    for p, (m, reason) in zip(props, recommendation_service.match_details(ctx.db, props, prefs)):
        c = _card(ctx, ps.summary(p))
        c.update(_match_dict(m, reason))
        out.append(c)
    out.sort(key=lambda c: c["rank_among_these"])
    ctx.last_listed = [c["id"] for c in out]
    return {"source": "recommendation engine weighted-v1", "preferences_used": basis,
            "score_meaning": "Weighted suitability score 0-100 for the stated preferences; not a probability of "
                             "investment success.", "listings": out}


def get_document_information(ctx: ToolContext, a: DocumentArgs) -> dict:
    if a.property_id is not None:
        p = ps.get_visible_property(ctx.db, a.property_id, ctx.user)
        docs, comp, n_prov, n_app = ps.document_view(p)
        _card(ctx, ps.summary(p, (docs, comp, n_prov, n_app)))
        return {"source": "listing database", "property_id": str(p.id),
                "listing_title": p.title,
                "documents": [{"document": d.label, "status": d.display_label, "status_code": d.display_status,
                               "guidance": d.guidance} for d in docs if d.applicable],
                "any_verified": any(d.display_status == "verified" for d in docs),
                "documentation_completeness": comp,
                "official_portals": [{"name": n, "url": u} for n, u in glossary.OFFICIAL_PORTALS.values()],
                "note": "Statuses are what the seller declared. PropWise has no document-verification process, "
                        "so 'provided' means unverified; verify with the issuing authority."}
    out: dict[str, Any] = {"source": "approved glossary"}
    if a.document_type is not None:
        e = glossary.lookup(_label("DocumentType", a.document_type.value)) or {}
        out["document"] = {"name": _label("DocumentType", a.document_type.value),
                           "what_it_is": document_rules.DOCUMENT_GUIDANCE[a.document_type],
                           "key_document": a.document_type in document_rules.KEY_DOCUMENTS,
                           "official_portals": e.get("official_portals", [])}
    if a.property_type is not None:
        from app.models.enums import ConversionStatus, LandClassification, LayoutApprovalStatus
        applicable = document_rules.applicable_documents(a.property_type, LandClassification.unknown,
                                                         ConversionStatus.unknown, LayoutApprovalStatus.unknown)
        out["documents_usually_relevant"] = {
            "property_type": _label("PropertyType", a.property_type.value),
            "documents": [_label("DocumentType", d.value) for d in applicable]}
    if len(out) == 1:
        out["documents"] = [{"name": _label("DocumentType", d.value), "what_it_is": g}
                            for d, g in document_rules.DOCUMENT_GUIDANCE.items()]
    out["official_portals"] = [{"name": n, "url": u} for n, u in glossary.OFFICIAL_PORTALS.values()]
    out["disclaimer"] = "General guidance, not legal advice. Verify documents with the issuing authority."
    return out


def get_location_summary(ctx: ToolContext, a: LocationArgs) -> dict:
    loc = _locality(ctx, a.locality, a.city)
    q = select(Property).join(Locality).where(Property.listing_status == ListingStatus.approved)
    if a.city:
        q = q.where(Locality.city == a.city)
    if loc:
        q = q.where(Property.locality_id == loc.id)
    if a.property_type:
        q = q.where(Property.property_type == a.property_type)
    rows = ctx.db.execute(q).scalars().all()
    scope = " · ".join(x for x in [loc.locality_name if loc else None, a.city,
                                   _label("PropertyType", a.property_type.value) if a.property_type else None] if x)
    if not rows:
        return {"source": "listing database", "scope": scope or "all", "approved_listings": 0}
    prices = [float(p.asking_price_inr) for p in rows]
    ppsf = [float(p.asking_price_inr) / float(p.normalized_area_sqft) for p in rows]
    by_type: dict[str, int] = {}
    for p in rows:
        k = _label("PropertyType", p.property_type.value)
        by_type[k] = by_type.get(k, 0) + 1
    return {"source": "listing database (asking prices of approved listings)", "scope": scope or "all",
            "approved_listings": len(rows), "by_property_type": by_type,
            "median_asking_price": inr(statistics.median(prices)),
            "asking_price_range": f"{inr(min(prices))} to {inr(max(prices))}",
            "median_price_per_sqft": inr(statistics.median(ppsf), exact=True),
            "note": SYNTHETIC_NOTE + " Asking prices are not sale prices."
                    + ("" if a.property_type else " Mixed property types: price per sq ft is not like-for-like.")}


def explain_term(ctx: ToolContext, a: TermArgs) -> dict:
    e = glossary.lookup(a.term)
    if e is None:
        return {"source": "approved glossary", "found": False,
                "message": "No approved definition for this term. Do not define it from general knowledge; "
                           "suggest checking with the relevant authority."}
    return {"source": "approved glossary", "found": True, **e}


# ------------------------------------------------------------------ registry

@dataclass
class Tool:
    name: str
    description: str
    args: type[BaseModel]
    fn: Callable[[ToolContext, Any], dict]

    def schema(self) -> dict:
        s = self.args.model_json_schema()
        s.pop("title", None)
        return s


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("search_properties", "Search approved listings with filters (city, locality, property types, price and "
         "area ranges in INR and sq ft, road access, declared documents). Use for 'show me…' questions.",
         SearchArgs, search_properties),
    Tool("get_property_details", "Full facts for one listing by id: land and approval status claims, document "
         "statuses, amenities, data warnings and risk flags.", PropertyIdArgs, get_property_details),
    Tool("recommend_properties", "Rank listings by suitability for the buyer's budget, property types, location, "
         "minimum area and objective, with reasons, trade-offs and what to verify.",
         RecommendArgs, recommend_properties),
    Tool("predict_property_price", "Indicative asking-price estimate and range from the demonstration price model, "
         "for a listing id or for locality + property type + area. Not a valuation.",
         PriceArgs, predict_property_price),
    Tool("compare_properties", "Compare 2 or 3 listings by id side by side (includes match scores when the buyer "
         "has saved Advisor preferences).", CompareArgs, compare_properties),
    Tool("explain_ranking", "Explain why one listing ranks higher than another, or why a listing was recommended: "
         "suitability score, rank and per-factor points for 1-3 listing ids against the buyer's preferences.",
         RankingArgs, explain_ranking),
    Tool("get_document_information", "What a property document is, which documents usually apply to a property "
         "type, or the document statuses declared for one listing; includes official portal links.",
         DocumentArgs, get_document_information),
    Tool("get_location_summary", "Counts and asking-price statistics of approved listings for a city, locality "
         "and/or property type (our own listings only).", LocationArgs, get_location_summary),
    Tool("explain_term", "Approved definition of a real-estate term (gunta, acre, RTC, khata, guidance value, "
         "suitability score…). Returns found=false when no approved definition exists.", TermArgs, explain_term),
]}


def _clean(s: str) -> str:
    # Listing text cannot close or open our data wrapper.
    import re
    return re.sub(r"</?\s*listing_data[^>]*>", "[removed tag]", s, flags=re.I)


def run_tool(ctx: ToolContext, name: str, arguments: dict) -> tuple[str, bool, dict]:
    """Validate and run one tool. Returns (content for the LLM, is_error, raw result)."""
    tool = TOOLS.get(name)
    if tool is None:
        result, err = {"error": "unknown_tool", "message": f"No tool named {name}"}, True
    else:
        try:
            args = tool.args.model_validate(arguments or {})
            result = tool.fn(ctx, args)
            err = "error" in result
        except ValidationError as e:
            result = {"error": "invalid_arguments",
                      "details": [{"field": ".".join(str(x) for x in er["loc"]), "issue": er["msg"]}
                                  for er in e.errors()]}
            err = True
        except AppError as e:
            code = "not_found_or_not_visible" if e.status_code == 404 else e.code
            result, err = {"error": code, "message": e.message}, True
    body = _clean(json.dumps(result, ensure_ascii=False, default=str))
    return f"<listing_data tool=\"{name}\">\n{body}\n</listing_data>", err, result
