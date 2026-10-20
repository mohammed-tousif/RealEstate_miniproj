"""Content-based, explainable recommendation (BLUEPRINT Part E).

Stage 1 applies the hard constraints the user marked as strict and counts every
exclusion by reason. Stage 2 scores each remaining listing on five factors (0–1),
drops factors that are irrelevant or marked "not important", renormalises the
weights and returns score = 100 × Σ wᵢ·sᵢ / Σ wᵢ. Missing data scores 0 for its
factor (no inflation) and is listed under missing information.

The engine works on plain `Candidate` records so it can be tested and evaluated
without a database. All explanation text is generated from the same numbers that
produce the score, so every claim can be checked against the record.
"""
from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.ml.recommendation import config as C
from app.schemas.recommendation import Preferences
from app.services.area_units import to_sqft

TYPE_LABELS = {"residential_plot": "residential plot", "independent_house": "independent house",
               "agricultural_land": "agricultural land", "commercial_plot": "commercial plot",
               "commercial_building": "commercial building"}
ROAD_LABELS = {"highway": "highway frontage", "main_road": "main-road access", "paved_internal": "a paved internal road",
               "unpaved": "an unpaved road", "no_direct_access": "no direct road access", "unknown": "unknown road access"}
KEY_DOC_LABELS = {"rtc_pahani": "RTC / Pahani", "encumbrance_certificate": "Encumbrance Certificate",
                  "sale_deed": "sale deed", "dc_conversion_order": "DC conversion order",
                  "layout_approval": "layout approval"}


@dataclass
class Candidate:
    id: uuid.UUID
    property_type: str
    land_classification: str
    conversion_status: str
    layout_approval_status: str
    road_access: str
    price: float
    area_sqft: float
    locality_id: int
    locality_name: str
    city: str
    doc_completeness: float
    docs_provided: int
    docs_applicable: int
    doc_status: dict[str, str] = field(default_factory=dict)  # applicable document -> availability
    created_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    ref: Any = None  # the ORM object, for serialisation


@dataclass
class Factor:
    name: str
    weight: float
    score: float
    known: float
    detail: str  # truthful one-line description of the input to this factor


@dataclass
class Scored:
    candidate: Candidate
    score: float
    coverage: float
    factors: list[Factor]
    reasons: list[str]
    tradeoffs: list[str]
    missing_info: list[str]
    verify: list[str]


@dataclass
class RankResult:
    scored: list[Scored]
    excluded: Counter
    weights: dict[str, float]
    ignored: list[str]
    notes: list[str]


def min_area_sqft(p: Preferences) -> float | None:
    return float(to_sqft(p.min_area_value, p.min_area_unit)) if p.min_area_value is not None else None


def _preferred_cities(p: Preferences, localities: dict[int, tuple[str, str]]) -> set[str]:
    return set(p.cities) | {localities[i][1] for i in p.locality_ids if i in localities}


# ------------------------------------------------------------------ stage 1

def exclusion_reason(c: Candidate, p: Preferences, localities: dict[int, tuple[str, str]]) -> str | None:
    if p.max_budget is not None:
        cap = float(p.max_budget) * (1 if p.budget_strict else 1 + C.BUDGET_OVERRUN)
        if c.price > cap:
            return "Over your maximum budget" if p.budget_strict else "More than 10% over your budget"
    if p.budget_strict and p.min_budget is not None and c.price < float(p.min_budget):
        return "Below your minimum budget"
    if p.types_strict and p.property_types and c.property_type not in {t.value for t in p.property_types}:
        return "Different property type"
    if p.location_strict and (p.cities or p.locality_ids):
        if c.locality_id not in p.locality_ids and c.city not in set(p.cities):
            return "Outside your preferred locations"
    area = min_area_sqft(p)
    if p.area_strict and area is not None and c.area_sqft < area:
        return "Smaller than your minimum area"
    return None


# ------------------------------------------------------------------ stage 2: factor scores

def budget_score(c: Candidate, p: Preferences) -> tuple[float, str]:
    mx = float(p.max_budget)
    r = c.price / mx
    pct = round(r * 100)
    if r > 1:
        s = max(0.0, 1 - (r - 1) / C.BUDGET_OVERRUN)
        return s, f"asking price is {pct - 100}% over your maximum budget"
    if r >= C.BUDGET_SWEET_SPOT:
        return 1.0, f"asking price is {pct}% of your maximum budget"
    return r / C.BUDGET_SWEET_SPOT, f"asking price is only {pct}% of your maximum budget, well below what you planned to spend"


def location_score(c: Candidate, p: Preferences, localities: dict[int, tuple[str, str]]) -> tuple[float, str]:
    if c.locality_id in p.locality_ids:
        return C.LOCATION_SCORES["preferred_locality"], f"in {c.locality_name}, one of your preferred localities"
    if c.city in _preferred_cities(p, localities):
        if p.locality_ids:
            return C.LOCATION_SCORES["preferred_city"], f"in {c.locality_name}, {c.city}: your preferred city but not one of your localities"
        return C.LOCATION_SCORES["preferred_locality"], f"in {c.locality_name}, {c.city}, your preferred city"
    return C.LOCATION_SCORES["other_city"], f"in {c.locality_name}, {c.city}, outside your preferred locations"


def purpose_score(c: Candidate, objective: str | None, preferred_types: set[str] | None = None) -> tuple[float, float, str]:
    """Returns (score, share of the inputs that are known, description).
    `preferred_types` is a non-strict type preference: other types are scored down, not excluded."""
    parts = [TYPE_LABELS[c.property_type]]
    if preferred_types and c.property_type not in preferred_types:
        type_mult = C.NON_PREFERRED_TYPE_MULT
        parts.append("not one of your preferred types")
    else:
        type_mult = 1.0
    if objective is None:
        return type_mult, 1.0, ", ".join(parts)
    s = C.PURPOSE_BASE[objective][c.property_type] * type_mult
    checks, known = 0, 0
    strict = C.OBJECTIVE_STRICTNESS[objective]
    expected = C.EXPECTED_CLASSIFICATION[objective]
    if expected is not None:
        checks += 1
        if c.land_classification == "unknown":
            s *= C.CLASSIFICATION_UNKNOWN_MULT
            parts.append("land classification unknown")
        else:
            known += 1
            if c.land_classification not in expected:
                s *= C.CLASSIFICATION_MISMATCH_MULT
                parts.append(f"classified {c.land_classification.replace('_', ' ')}")
    if strict and c.property_type != "agricultural_land":
        for value, table, unknown_text, label in (
                (c.conversion_status, C.CONVERSION_MULT[strict], "conversion status unknown", "conversion"),
                (c.layout_approval_status, C.LAYOUT_MULT[strict], "layout approval unknown", "layout")):
            if value == "not_applicable":
                continue
            checks += 1
            if value == "unknown":
                parts.append(unknown_text)
            else:
                known += 1
                parts.append({"converted_claimed": "conversion claimed", "conversion_in_progress": "conversion in progress",
                              "not_converted": "not converted", "approved_layout_claimed": "approved layout claimed",
                              "unapproved_layout": "unapproved layout"}[value])
            s *= table[value]
    coverage = known / checks if checks else 1.0
    return round(min(1.0, s), 4), coverage, ", ".join(parts)


def factor_scores(c: Candidate, p: Preferences, weights: dict[str, float],
                  localities: dict[int, tuple[str, str]]) -> list[Factor]:
    out = []
    for name, w in weights.items():
        if name == "budget":
            s, d = budget_score(c, p)
            out.append(Factor(name, w, s, 1.0, d))
        elif name == "location":
            s, d = location_score(c, p, localities)
            out.append(Factor(name, w, s, 1.0, d))
        elif name == "purpose":
            soft_types = {t.value for t in p.property_types} if p.property_types and not p.types_strict else None
            s, k, d = purpose_score(c, p.objective, soft_types)
            out.append(Factor(name, w, s, k, d))
        elif name == "connectivity":
            out.append(Factor(name, w, C.ROAD_SCORE[c.road_access], 0.0 if c.road_access == "unknown" else 1.0,
                              ROAD_LABELS[c.road_access]))
        elif name == "documentation":
            n = len(c.doc_status)
            known = sum(1 for v in c.doc_status.values() if v != "unknown") / n if n else 1.0
            out.append(Factor(name, w, c.doc_completeness, known,
                              f"seller has declared {c.docs_provided} of {c.docs_applicable} applicable documents"))
    return out


def resolve_weights(p: Preferences, overrides: dict[str, float] | None = None) -> tuple[dict[str, float], list[str], list[str]]:
    """Base weights × importance, minus factors without a stated preference. Returns
    (normalised weights, ignored factor names, notes)."""
    base = dict(C.DEFAULT_WEIGHTS)
    if overrides:
        base.update(overrides)
    relevant = {"budget": p.max_budget is not None, "location": bool(p.cities or p.locality_ids),
                "purpose": p.objective is not None or (bool(p.property_types) and not p.types_strict), "connectivity": True, "documentation": True}
    raw, ignored, notes = {}, [], []
    for f in C.FACTORS:
        mult = C.IMPORTANCE[p.importance.get(f, "important")]
        if not relevant[f]:
            ignored.append(f)
            notes.append(f"{C.FACTOR_LABELS[f]} was not scored because no preference was given.")
        elif mult == 0:
            ignored.append(f)
            notes.append(f"{C.FACTOR_LABELS[f]} was not scored because you marked it as not important.")
        else:
            raw[f] = base[f] * mult
    total = sum(raw.values())
    if total == 0:
        raise ValueError("at least one factor must matter")
    return {f: w / total for f, w in raw.items()}, ignored, notes


# ------------------------------------------------------------------ explanations

def explain(c: Candidate, factors: list[Factor], p: Preferences) -> tuple[list[str], list[str], list[str], list[str]]:
    strong = sorted((f for f in factors if f.score >= 0.5 and f.known > 0), key=lambda f: -(f.weight * f.score))
    reasons = [f"{C.FACTOR_LABELS[f.name]}: {f.detail}." for f in strong[:2]]
    tradeoffs = [f"{C.FACTOR_LABELS[f.name]}: {f.detail}." for f in factors if f.score < 0.5 and f.known > 0]
    area = min_area_sqft(p)
    if area is not None and c.area_sqft < area:
        tradeoffs.append(f"Area: {c.area_sqft:,.0f} sq ft is below your preferred minimum of {area:,.0f} sq ft.")
    missing = []
    if c.road_access == "unknown":
        missing.append("Road access is not stated (scored as 0).")
    for f in factors:
        if f.name == "purpose" and f.known < 1:
            missing.append(f"Some legal-status fields are unknown ({f.detail}).")
    unknown_docs = [k for k, v in c.doc_status.items() if v == "unknown"]
    if unknown_docs:
        missing.append(f"Availability of {len(unknown_docs)} applicable document(s) is unknown (counted as not provided).")
    provided_key = [KEY_DOC_LABELS[k] for k, v in c.doc_status.items() if v == "provided" and k in KEY_DOC_LABELS]
    verify = []
    if provided_key:
        verify.append(f"Declared but not verified: {', '.join(provided_key)}. Check them with the issuing authority.")
    missing_key = [KEY_DOC_LABELS[k] for k, v in c.doc_status.items() if v != "provided" and k in KEY_DOC_LABELS]
    if missing_key:
        verify.append(f"Not declared: {', '.join(missing_key)}.")
    if c.property_type != "agricultural_land" and c.conversion_status != "converted_claimed":
        verify.append("Non-agricultural conversion is not established; confirm it before buying for construction.")
    return reasons, tradeoffs, missing, verify


# ------------------------------------------------------------------ ranking

def rank(candidates: list[Candidate], p: Preferences, localities: dict[int, tuple[str, str]],
         weight_overrides: dict[str, float] | None = None) -> RankResult:
    weights, ignored, notes = resolve_weights(p, weight_overrides)
    excluded: Counter = Counter()
    scored: list[Scored] = []
    for c in candidates:
        reason = exclusion_reason(c, p, localities)
        if reason:
            excluded[reason] += 1
            continue
        factors = factor_scores(c, p, weights, localities)
        score = 100 * sum(f.weight * f.score for f in factors)
        coverage = sum(f.weight * f.known for f in factors)
        reasons, tradeoffs, missing, verify = explain(c, factors, p)
        scored.append(Scored(c, round(score, 2), round(coverage, 3), factors, reasons, tradeoffs, missing, verify))
    # Ties: higher documentation completeness, then lower price, then id (stable and deterministic).
    scored.sort(key=lambda s: (-s.score, -s.candidate.doc_completeness, s.candidate.price, str(s.candidate.id)))
    return RankResult(scored, excluded, weights, ignored, notes)
