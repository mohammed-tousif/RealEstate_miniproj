"""Basic search mode: a rule-based intent parser over the same read-only tools.

Used when no LLM is configured or the LLM fails. Answers are templates filled from tool results,
so every listing and number in them comes from the database or the price model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select

from app.ai import glossary
from app.ai.tools import ToolContext, run_tool
from app.models import Locality

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_NUM = r"(\d+(?:[.,]\d+)*)"
_MONEY_RE = re.compile(_NUM + r"\s*(lakhs?|lacs?|lac|l|crores?|cr|k)\b", re.I)
_RUPEES_RE = re.compile(r"(?:₹|rs\.?|inr)\s*" + _NUM, re.I)
_AREA_RE = re.compile(_NUM + r"\s*(acres?|guntas?|guntha|sq\.?\s*ft|sqft|square\s+feet|sq\.?\s*m|sqm|square\s+met(?:er|re)s?)\b",
                      re.I)


@dataclass
class Parsed:
    min_budget: Decimal | None = None
    max_budget: Decimal | None = None
    property_types: list[str] = field(default_factory=list)
    cities: list[str] = field(default_factory=list)
    localities: list[str] = field(default_factory=list)
    min_area_value: Decimal | None = None
    min_area_unit: str = "sqft"
    objective: str | None = None
    ids: list[str] = field(default_factory=list)

    @property
    def has_criteria(self) -> bool:
        return bool(self.min_budget or self.max_budget or self.property_types or self.cities or self.localities
                    or self.min_area_value or self.objective)


def _num(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def _amounts(text: str) -> list[tuple[int, Decimal]]:
    out = []
    for m in _MONEY_RE.finditer(text):
        unit = m.group(2).lower()
        mult = 10_000_000 if unit.startswith("cr") else 1_000 if unit == "k" else 100_000
        out.append((m.start(), _num(m.group(1)) * mult))
    for m in _RUPEES_RE.finditer(text):
        if _MONEY_RE.match(text, m.start(1)):
            continue  # "₹25 lakh" is already counted above
        v = _num(m.group(1))
        if v >= 10_000:
            out.append((m.start(), v))
    return sorted(out)


def parse(text: str, locality_names: list[tuple[str, str]]) -> Parsed:
    t = text.lower()
    p = Parsed(ids=[m.group(0).lower() for m in UUID_RE.finditer(text)])
    clean = UUID_RE.sub(" ", text)

    amounts = _amounts(clean)
    if len(amounts) >= 2 and re.search(r"\bbetween\b|\bfrom\b|\bto\b|-", t):
        p.min_budget, p.max_budget = sorted([amounts[0][1], amounts[1][1]])
    elif amounts:
        pos, v = amounts[0]
        before = clean[max(0, pos - 25):pos].lower()
        if re.search(r"(above|over|more than|at least|minimum|min|from)\s*(₹|rs\.?|inr)?\s*$", before):
            p.min_budget = v
        else:
            p.max_budget = v

    m = _AREA_RE.search(clean)
    if m:
        unit = m.group(2).lower()
        p.min_area_unit = ("acre" if unit.startswith("acre") else "gunta" if unit.startswith("gunt")
                           else "sqft" if ("ft" in unit or "feet" in unit) else "sqm")
        p.min_area_value = _num(m.group(1))

    types = []
    t_types = re.sub(r"\bbuild(ing)? (a |my |our )?(house|home)\b", " ", t)  # an objective, not a property type
    if re.search(r"\bcommercial\s+plots?\b", t_types):
        types.append("commercial_plot")
    elif re.search(r"\b(plots?|sites?)\b", t_types):
        types.append("residential_plot")
    if re.search(r"\b(house|houses|home|homes|villa|independent)\b", t_types):
        types.append("independent_house")
    if re.search(r"\b(farm\s*land|farmland|farm|agricultural|agri|agriculture)\b", t_types):
        types.append("agricultural_land")
    if re.search(r"\b(shop|shops|office|showroom|commercial\s+buildings?|complex)\b", t_types):
        types.append("commercial_building")
    if re.search(r"\bcommercial\b", t_types) and not {"commercial_plot", "commercial_building"} & set(types):
        types += ["commercial_plot", "commercial_building"]
    p.property_types = list(dict.fromkeys(types))

    if re.search(r"\bhub(b)?al?li\b|\bhubli\b", t):
        p.cities.append("Hubballi")
    if re.search(r"\bdharwad\b|\bdharawad\b", t):
        p.cities.append("Dharwad")
    for name, _city in locality_names:
        if re.search(rf"\b{re.escape(name.lower())}\b", t) and name.lower() not in ("old hubballi",):
            p.localities.append(name)

    if re.search(r"\binvest|long[\s-]*term|appreciat|resale", t):
        p.objective = "long_term_investment"
    elif re.search(r"\bfarming|cultivat|grow crops|agricultur(e|al) use", t):
        p.objective = "farming"
    elif re.search(r"\bbuild(ing)? (a |my |our )?(house|home)|\bconstruct|live in|own home|my house", t):
        p.objective = "build_house"
    elif re.search(r"\bbusiness|commercial use|open a shop|for (a|my) shop|for (an|my) office", t):
        p.objective = "commercial_use"
    return p


# ------------------------------------------------------------------ answers

def _listing_line(c: dict) -> str:
    extra = f" · suitability {c['suitability_score']:.0f}/100" if "suitability_score" in c else ""
    return (f"- [{c['title']}]({c['link']}): {c['asking_price']}, {c['area']}, {c['property_type']} in "
            f"{c['locality']}, {c['city']} · documents {c['documents_declared']}{extra}")


def _criteria_text(p: Parsed) -> str:
    from app.ai.format import inr
    bits = []
    if p.property_types:
        bits.append(", ".join(t.replace("_", " ") for t in p.property_types))
    if p.localities or p.cities:
        bits.append("in " + ", ".join(p.localities + p.cities))
    if p.min_budget and p.max_budget:
        bits.append(f"between {inr(p.min_budget)} and {inr(p.max_budget)}")
    elif p.max_budget:
        bits.append(f"up to {inr(p.max_budget)}")
    elif p.min_budget:
        bits.append(f"from {inr(p.min_budget)}")
    if p.min_area_value:
        bits.append(f"at least {p.min_area_value} {p.min_area_unit}")
    return " ".join(bits) or "any listing"


HELP = ("I can search listings, recommend options for a budget, estimate an indicative price for a listing, "
        "compare listings, and explain documents and terms. Try: \"Plots in Dharwad under 25 lakh\", "
        "\"Farmland near Hubballi for long-term investment, 30 lakh\", or \"What is an RTC?\"")


def answer(ctx: ToolContext, message: str) -> tuple[str, list[str]]:
    """Returns (answer text, names of the tools that ran)."""
    names = [(l.locality_name, l.city) for l in ctx.db.execute(select(Locality)).scalars()]
    p = parse(message, names)
    t = message.lower()
    used: list[str] = []

    def call(name: str, args: dict) -> tuple[dict, bool]:
        used.append(name)
        _, err, res = run_tool(ctx, name, args)
        return res, err

    asks_rank = re.search(r"\bwhy\b.*\b(rank|higher|better|recommend|score|top|first)|\branks?\b|\branked\b|"
                          r"\branking\b|\bhigher\b|\bsuitab", t)
    if p.ids and asks_rank:
        args = {"property_ids": p.ids[:3], "property_types": p.property_types, "cities": p.cities,
                "objective": p.objective, "max_budget_inr": str(p.max_budget) if p.max_budget else None}
        res, err = call("explain_ranking", args)
        if err:
            if res.get("error") == "no_preferences":
                return ("To explain a ranking I need your preferences. Set them in the Advisor, or include them in "
                        "the question (for example: \"budget 25 lakh, residential plot, long-term investment\")."), used
            return f"I could not find one of those listings ({res.get('message', '')}).", used
        out = [f"Ranking using {res['preferences_used']} (suitability score out of 100, not a probability of "
               "investment success):"]
        for c in res["listings"]:
            pts = sorted(c["factor_contributions"].items(), key=lambda kv: -kv[1]["points_out_of_100"])
            pts_txt = ", ".join(f"{k} {v['points_out_of_100']:.1f}" for k, v in pts)
            line = f"- #{c['rank_among_these']} [{c['title']}]({c['link']}): {c['suitability_score']:.1f}/100 ({pts_txt})"
            if c["fails_strict_requirement"]:
                line += f"\n  Fails a strict requirement: {c['fails_strict_requirement']}"
            if c["why_it_matches"]:
                line += "\n  Why: " + "; ".join(r.rstrip(".") for r in c["why_it_matches"][:2])
            if c["trade_offs"]:
                line += "\n  Trade-off: " + "; ".join(r.rstrip(".") for r in c["trade_offs"][:2])
            out.append(line)
        if len(res["listings"]) >= 2:
            a, b = res["listings"][0], res["listings"][1]
            diffs = sorted(((k, v["points_out_of_100"] - b["factor_contributions"].get(k, {}).get(
                "points_out_of_100", 0)) for k, v in a["factor_contributions"].items()), key=lambda kv: -abs(kv[1]))
            top = [f"{k} ({d:+.1f} points)" for k, d in diffs if abs(d) >= 0.5][:3]
            gap = a["suitability_score"] - b["suitability_score"]
            out.append(f"\nThe first ranks higher by {gap:.1f} points. Biggest differences: "
                       + (", ".join(top) if top else "none; the order comes from the tie-break (more documents "
                          "declared, then lower price)") + ".")
        return "\n".join(out), used

    wants_price = re.search(r"\b(price|worth|estimate|valu|cost|fair|overpriced|cheap)", t)
    if "compar" in t and len(p.ids) >= 2:
        res, err = call("compare_properties", {"property_ids": p.ids[:3]})
        if err:
            return f"I could not compare those listings: {res.get('message', 'not found')}.", used
        lines = []
        for c in res["listings"]:
            line = _listing_line(c)
            m = c.get("match_for_saved_preferences")
            if m:
                line += f"\n  Match for your Advisor preferences: {m['suitability_score']:.1f}/100, #{m['rank_among_these']} of these"
            if c["risk_flags"]:
                line += f"\n  Risk flags: {'; '.join(c['risk_flags'])}"
            lines.append(line)
        return "Side by side (listing data):\n" + "\n".join(lines) + "\n\n" + " ".join(res["warnings"]), used

    if p.ids and wants_price:
        res, err = call("predict_property_price", {"property_id": p.ids[0]})
        if err:
            msg = res.get("message", "")
            if res.get("error") == "model_unavailable":
                return f"The price model is not available right now, so I cannot give an estimate. {msg}", used
            return f"I could not find that listing ({msg}).", used
        q = ""
        if res.get("quoted_price"):
            pos = {"within_range": "within", "above_range": "above", "below_range": "below"}[res["quoted_position"]]
            q = f" The asking price {res['quoted_price']} is {pos} that range."
        return (f"ML estimate: about {res['estimated_asking_price']} (indicative range {res['indicative_range']}).{q}\n"
                + "\n".join(f"- {w}" for w in res["warnings"]) + f"\n\n{res['disclaimer']}"), used

    if p.ids and re.search(r"\bdocument|papers|rtc|khata|\bec\b|deed|conversion|approval|verif|legal|title", t):
        res, err = call("get_document_information", {"property_id": p.ids[0]})
        if err:
            return f"I could not find that listing ({res.get('message', '')}).", used
        by = lambda *codes: [d["document"] for d in res["documents"] if d["status_code"] in codes]
        lines = [f"- {d['document']}: {d['status']}" for d in res["documents"]]
        verified = by("verified")
        head = (f"Stored document status for [{res['listing_title']}](/properties/{res['property_id']}) "
                f"(declared by the seller):")
        parts = [head + "\n" + "\n".join(lines)]
        parts.append(("Verified: " + ", ".join(verified) + ".") if verified else
                     "None of these documents is verified. PropWise has no document-verification process, so "
                     "\"provided\" only means the seller says they have it.")
        todo = by("provided_unverified", "verification_pending")
        if todo:
            parts.append("Still to verify independently: " + ", ".join(todo) + ". Check land records on Bhoomi "
                         "(landrecords.karnataka.gov.in), registration and EC on Kaveri (kaveri.karnataka.gov.in), "
                         "and khata with the municipal corporation.")
        missing = by("not_provided", "unknown")
        if missing:
            parts.append("Not provided or unknown: " + ", ".join(missing) + ". Ask the seller for these.")
        parts.append("General guidance, not legal advice. Consult a qualified lawyer before buying.")
        return "\n\n".join(parts), used

    if p.ids:
        res, err = call("get_property_details", {"property_id": p.ids[0]})
        if err:
            return f"I could not find that listing. It may not exist or may not be public ({res.get('message', '')}).", used
        c = res["listing"]
        flags = "\n".join(f"- {f}" for f in res["risk_flags"]) or "- none from our rules"
        return (f"{_listing_line(c)}\n\nLand: {res['land']['land_classification']}, "
                f"{res['land']['conversion_status']}, {res['land']['layout_approval_status']} (seller's claims).\n"
                f"Things to check:\n{flags}"), used

    terms = glossary.find_terms(message)
    asks_definition = re.search(r"\bwhat\s+(is|are|does)\b|\bwhat's\b|\bmeaning\b|\bexplain\b|\bdefine\b|"
                                r"\bwhy\b.*\bneed|\bwhich documents?\b", t)
    if re.search(r"\bwhich documents?\b|\bdocuments? (do i|should i|are) need", t) and p.property_types:
        res, _ = call("get_document_information", {"property_type": p.property_types[0]})
        docs = res["documents_usually_relevant"]
        portals = "\n".join(f"- {x['name']}: {x['url']}" for x in res["official_portals"])
        return (f"Documents usually relevant for {docs['property_type'].lower()}: {', '.join(docs['documents'])}.\n\n"
                f"Official portals:\n{portals}\n\n{res['disclaimer']}"), used
    if terms and (asks_definition or not p.has_criteria):
        used.append("explain_term")
        parts = []
        for e in terms[:3]:
            portals = "".join(f"\n  Official portal: {x['name']}: {x['url']}" for x in e["official_portals"])
            parts.append(f"**{e['term']}**: {e['definition']}{portals}")
        return "\n\n".join(parts) + "\n\nGeneral guidance, not legal advice.", used

    if re.search(r"\baverage|median|typical|price range|how much (do|does|are|is)|rates?\b", t) and \
            (p.cities or p.localities):
        args = {"city": p.cities[0] if p.cities else None, "locality": p.localities[0] if p.localities else None,
                "property_type": p.property_types[0] if p.property_types else None}
        res, err = call("get_location_summary", args)
        if err or not res.get("approved_listings"):
            return f"There are no approved listings for {res.get('scope', 'that area')} yet.", used
        return (f"Approved listings for {res['scope']}: {res['approved_listings']}. Median asking price "
                f"{res['median_asking_price']}, range {res['asking_price_range']}, median "
                f"{res['median_price_per_sqft']} per sq ft.\n\n{res['note']}"), used

    if not p.has_criteria:
        return HELP, used

    if p.objective or re.search(r"\brecommend|suggest|best|suitable|good for|should i", t):
        args = {"max_budget_inr": str(p.max_budget) if p.max_budget else None,
                "min_budget_inr": str(p.min_budget) if p.min_budget else None,
                "property_types": p.property_types, "cities": p.cities, "localities": p.localities,
                "min_area_value": str(p.min_area_value) if p.min_area_value else None,
                "min_area_unit": p.min_area_unit, "objective": p.objective, "limit": 5}
        res, err = call("recommend_properties", args)
        if err:
            return f"I could not run the recommendation: {res.get('message', '')}", used
        if not res["recommendations"]:
            excl = "; ".join(f"{k} ({v})" for k, v in res["excluded_counts"].items())
            return f"No listing meets all of those requirements for {_criteria_text(p)}. Most exclusions: {excl}.", used
        lines = []
        for c in res["recommendations"]:
            why = "; ".join(r.rstrip(".") for r in c["why_it_matches"][:2])
            lines.append(_listing_line(c) + (f"\n  Why: {why}" if why else ""))
        return (f"Top matches for {_criteria_text(p)} (ranked by the Advisor's suitability score, not a probability "
                f"of investment success):\n" + "\n".join(lines) + f"\n\n{res['note']}"), used

    sort = "price_desc" if re.search(r"\bexpensive|premium|luxury", t) else "price_asc"
    args = {"city": p.cities[0] if len(p.cities) == 1 else None,
            "locality": p.localities[0] if p.localities else None, "property_types": p.property_types,
            "min_price_inr": str(p.min_budget) if p.min_budget else None,
            "max_price_inr": str(p.max_budget) if p.max_budget else None, "sort": sort, "limit": 5}
    if p.min_area_value:
        from app.services.area_units import to_sqft
        args["min_area_sqft"] = str(to_sqft(p.min_area_value, p.min_area_unit))
    res, err = call("search_properties", args)
    if err:
        return f"I could not search: {res.get('message', '')}", used
    if not res["listings"]:
        return f"No approved listings match {_criteria_text(p)}. Try a higher budget or another locality.", used
    return (f"{res['total_matches']} listing(s) match {_criteria_text(p)}; showing {res['returned']} "
            f"({'highest' if sort == 'price_desc' else 'lowest'} price first):\n"
            + "\n".join(_listing_line(c) for c in res["listings"]) + f"\n\n{res['note']}"), used
