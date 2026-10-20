"""Approved definitions the assistant may quote (BLUEPRINT Part E, `explain_term`).

General guidance for the demo, not legal advice. Document entries reuse the text the listing pages
already show, so the assistant and the UI say the same thing.
"""
from __future__ import annotations

import re

from app.models.enums import DocumentType as D
from app.services.document_rules import DOCUMENT_GUIDANCE

# Official portals. Addresses checked on 2026-10-18 against published guides (the build environment
# could not open the government sites directly); confirm on the portal before relying on them.
OFFICIAL_PORTALS = {
    "bhoomi": ("Bhoomi land records (RTC / Pahani, mutation)", "https://landrecords.karnataka.gov.in"),
    "kaveri": ("Kaveri Online Services (registration, Encumbrance Certificate)", "https://kaveri.karnataka.gov.in"),
    "rera": ("Karnataka RERA (project and agent registration)", "https://rera.karnataka.gov.in"),
    "hdmc": ("Hubballi-Dharwad Municipal Corporation (khata, property tax, building permission)",
             "https://www.hdmc.mrc.gov.in"),
}

_DOC_TERMS: dict[str, D] = {
    "rtc": D.rtc_pahani, "pahani": D.rtc_pahani, "record of rights": D.rtc_pahani,
    "mutation": D.mutation_record,
    "encumbrance": D.encumbrance_certificate, "ec": D.encumbrance_certificate,
    "khata": D.khata, "e-khata": D.khata, "a khata": D.khata, "b khata": D.khata,
    "sale deed": D.sale_deed, "title deed": D.sale_deed,
    "dc conversion": D.dc_conversion_order, "conversion order": D.dc_conversion_order,
    "na conversion": D.dc_conversion_order, "land conversion": D.dc_conversion_order,
    "layout approval": D.layout_approval, "approved layout": D.layout_approval,
    "building plan": D.building_plan_approval,
    "commencement certificate": D.commencement_certificate, "cc": D.commencement_certificate,
    "completion certificate": D.completion_certificate,
    "occupancy certificate": D.occupancy_certificate, "oc": D.occupancy_certificate,
    "rera": D.rera_registration,
}

_TERMS: dict[str, tuple[str, str]] = {
    "gunta": ("Gunta", "A land-area unit used for farmland in Karnataka. 1 gunta = 1,089 sq ft, and 40 guntas = 1 acre."),
    "acre": ("Acre", "A land-area unit. 1 acre = 43,560 sq ft = 40 guntas (about 4,047 sq m)."),
    "sq ft": ("Square foot", "The unit PropWise stores every area in. 1 sq m = 10.7639 sq ft."),
    "sq m": ("Square metre", "Metric area unit. 1 sq m = 10.7639 sq ft."),
    "agricultural land": ("Agricultural land", "Land recorded for agricultural use. Building a house or business "
                          "on it normally needs a conversion order for non-agricultural use first."),
    "non-agricultural": ("Non-agricultural (NA) land", "Land whose permitted use has been changed from "
                         "agriculture (for example by a DC conversion order). PropWise records this as the "
                         "seller's claim, not as a verified fact."),
    "guidance value": ("Guidance value", "The minimum value per unit area fixed by the Karnataka government for "
                       "calculating stamp duty and registration fees. It is not a market price, and PropWise "
                       "does not use it."),
    "stamp duty": ("Stamp duty", "A state tax paid when a property transfer is registered, calculated on the higher "
                   "of the sale price and the guidance value. Check current rates with the registration "
                   "department."),
    "documentation completeness": ("Documentation completeness", "PropWise's share of applicable documents the "
                                   "seller declared as provided, with key documents counted twice. It measures "
                                   "what was declared, never whether the title is clear."),
    "suitability score": ("Suitability score", "The Advisor's 0-100 weighted score of how well a listing matches "
                          "your stated preferences (budget, location, purpose, connectivity, documentation). It is "
                          "not a probability of investment success."),
    "price estimate": ("Price estimate", "An indicative asking-price range from a regression model trained on "
                       "synthetic demo data. It is not a valuation."),
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\- ]", " ", s.lower())).strip()


def lookup(term: str) -> dict | None:
    """Exact or contained match against approved terms; None when we have no approved definition."""
    t = _norm(term)
    if not t:
        return None
    for keys, kind in ((_DOC_TERMS, "doc"), (_TERMS, "term")):
        for k in sorted(keys, key=len, reverse=True):
            if t == k or re.search(rf"\b{re.escape(k)}\b", t):
                return _entry(k, kind)
    return None


def _entry(key: str, kind: str) -> dict:
    if kind == "doc":
        from app.models.enums import LABELS
        d = _DOC_TERMS[key]
        return {"term": LABELS.get(("DocumentType", d.value), d.value), "document_type": d.value,
                "definition": DOCUMENT_GUIDANCE[d], "official_portals": _portals_for(d)}
    title, text = _TERMS[key]
    return {"term": title, "definition": text, "official_portals": []}


def _portals_for(d: D) -> list[dict]:
    key = {D.rtc_pahani: "bhoomi", D.mutation_record: "bhoomi", D.encumbrance_certificate: "kaveri",
           D.sale_deed: "kaveri", D.rera_registration: "rera", D.khata: "hdmc",
           D.building_plan_approval: "hdmc"}.get(d)
    return [{"name": OFFICIAL_PORTALS[key][0], "url": OFFICIAL_PORTALS[key][1]}] if key else []


def find_terms(text: str) -> list[dict]:
    """Every approved term mentioned in a free-text question (used by Basic search mode)."""
    t = f" {_norm(text)} "
    seen, out = set(), []
    for keys, kind in ((_DOC_TERMS, "doc"), (_TERMS, "term")):
        for k in sorted(keys, key=len, reverse=True):
            if re.search(rf"\b{re.escape(k)}\b", t):
                e = _entry(k, kind)
                if e["term"] not in seen:
                    seen.add(e["term"])
                    out.append(e)
    return out
