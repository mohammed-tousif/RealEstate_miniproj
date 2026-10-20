"""Generate the SYNTHETIC demonstration dataset for PropWise AI.

Every record produced here is fictional. Prices come from the documented formula
below using invented base rates; they are NOT market data for Hubballi–Dharwad.
Records are marked is_synthetic=true and data_source=synthetic_generator_v1.

    price = base_rate(locality, type) x area x type_mult x conversion_mult x layout_mult
            x road_mult x corner_mult x area_scale x lognormal_noise(sigma=0.15)

The generator also injects a few known imperfections (near-duplicates, price
outliers, mismatched dimensions, missing values) so the cleaning pipeline,
data-quality report and warnings have something real to detect.

Usage:  python scripts/generate_synthetic_data.py [--n 300] [--seed 42] [--out ../data/raw/synthetic_properties_v1.csv]
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.enums import DocumentType  # noqa: E402
from app.services.reference_data import LOCALITIES  # noqa: E402

GENERATOR_VERSION = "synthetic_generator_v1"
REFERENCE_DATE = date(2026, 10, 1)  # synthetic "listed_on" dates are spread over 180 days before this

# Invented demo base rates (INR per sq ft of non-agricultural residential land) per locality,
# and (INR per acre) for agricultural land. Chosen only to give a plausible-looking spread.
SYNTHETIC_NA_RATE = {
    "Vidyanagar": 3200, "Keshwapur": 3000, "Gokul Road": 2600, "Unkal": 2800, "Navanagar": 2400,
    "Bhairidevarkoppa": 2200, "Old Hubballi": 1900, "Gabbur": 1400, "Kusugal": 900, "Byahatti": 800,
    "Saptapur": 3100, "Kalyan Nagar": 2900, "Malmaddi": 2700, "Sattur": 2300, "Lakamanahalli": 1800,
    "Narayanpur": 2000, "Kelgeri": 1700, "Rayapur": 1600, "Garag": 800, "Mugad": 850, "Amminabhavi": 750,
}
SYNTHETIC_AGRI_RATE_PER_ACRE = {
    "Gabbur": 3_400_000, "Kusugal": 2_200_000, "Byahatti": 1_800_000, "Kelgeri": 3_000_000,
    "Rayapur": 3_200_000, "Garag": 1_500_000, "Mugad": 1_700_000, "Amminabhavi": 1_400_000,
    "Lakamanahalli": 3_600_000, "Navanagar": 4_500_000,
}

TYPE_MULT = {"residential_plot": 1.0, "commercial_plot": 1.7}
ROAD_MULT = {"highway": 1.25, "main_road": 1.15, "paved_internal": 1.0, "unpaved": 0.85,
             "no_direct_access": 0.7, "unknown": 0.95}
CONV_MULT = {"converted_claimed": 1.0, "conversion_in_progress": 0.8, "not_converted": 0.6, "unknown": 0.85,
             "not_applicable": 1.0}
LAYOUT_MULT = {"approved_layout_claimed": 1.0, "unapproved_layout": 0.8, "unknown": 0.9, "not_applicable": 1.0}

SQM_PER_SQFT = 1 / 10.7639104


def pick(rng: random.Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def choose_type(rng: random.Random, locality: str, rural: bool) -> str:
    if rural:
        w = {"agricultural_land": 0.7, "residential_plot": 0.25, "commercial_plot": 0.05}
    elif locality in SYNTHETIC_AGRI_RATE_PER_ACRE:  # urban fringe
        w = {"agricultural_land": 0.25, "residential_plot": 0.5, "independent_house": 0.1, "commercial_plot": 0.15}
    else:
        w = {"residential_plot": 0.45, "independent_house": 0.2, "commercial_plot": 0.18, "commercial_building": 0.17}
    return pick(rng, w)


def make_record(rng: random.Random, idx: int) -> dict:
    name, city, lat, lng, rural = rng.choice(LOCALITIES)
    ptype = choose_type(rng, name, rural)
    if ptype == "agricultural_land" and name not in SYNTHETIC_AGRI_RATE_PER_ACRE:
        ptype = "residential_plot"
    rec: dict = {"source_record_id": f"SYN-{idx:04d}", "is_synthetic": True, "data_source": GENERATOR_VERSION,
                 "locality": name, "city": city, "district": "Dharwad", "property_type": ptype,
                 "coordinates_approximate": True}

    # Location: jitter around the approximate locality point.
    spread = 0.012 if rural else 0.006
    rec["latitude"] = round(lat + rng.uniform(-spread, spread), 6)
    rec["longitude"] = round(lng + rng.uniform(-spread, spread), 6)

    width = length = frontage = None
    corner = None
    if ptype == "agricultural_land":
        acres = max(0.25, min(12.0, rng.lognormvariate(math.log(2.2), 0.6)))
        guntas_total = round(acres * 40)
        acres = guntas_total / 40
        if guntas_total % 40 == 0 or rng.random() < 0.3:
            rec["area_value"], rec["area_unit"] = (round(acres, 4), "acre")
        else:
            rec["area_value"], rec["area_unit"] = (guntas_total, "gunta")
        sqft = guntas_total * 1089
        rec["land_classification"] = "agricultural" if rng.random() < 0.95 else "unknown"
        rec["conversion_status"] = "not_applicable"
        rec["layout_approval_status"] = "not_applicable"
        rec["intended_land_use"] = "agricultural"
        road = pick(rng, {"highway": 0.08, "main_road": 0.15, "paved_internal": 0.15, "unpaved": 0.45,
                          "no_direct_access": 0.1, "unknown": 0.07})
        if rng.random() < 0.4:
            frontage = rng.choice([60, 80, 100, 150, 200, 300])
        base = SYNTHETIC_AGRI_RATE_PER_ACRE[name] * acres
        price = base * ROAD_MULT[road] * (acres / 2) ** -0.08
        if rng.random() < 0.3:
            price *= 1.08  # synthetic premium for an irrigation source
            rec["_irrigation"] = True
    else:
        dims = {"residential_plot": [(30, 40), (30, 50), (40, 60), (30, 45), (40, 50), (50, 80), (20, 30)],
                "independent_house": [(30, 40), (30, 50), (40, 60), (20, 30)],
                "commercial_plot": [(30, 60), (40, 60), (50, 80), (60, 100), (40, 80)],
                "commercial_building": [(20, 40), (30, 40), (40, 60), (30, 60)]}[ptype]
        width, length = rng.choice(dims)
        sqft = width * length
        unit = pick(rng, {"sqft": 0.8, "sqm": 0.15, "gunta": 0.05 if sqft >= 1089 else 0.0})
        if unit == "sqft":
            rec["area_value"] = sqft
        elif unit == "sqm":
            rec["area_value"] = round(sqft * SQM_PER_SQFT, 2)
            sqft = rec["area_value"] * 10.7639104
        else:
            rec["area_value"] = round(sqft / 1089, 2)
            sqft = rec["area_value"] * 1089
        rec["area_unit"] = unit
        commercial = ptype.startswith("commercial")
        rec["intended_land_use"] = "commercial" if commercial else "residential"
        r = rng.random()
        if commercial:
            rec["land_classification"] = "non_agricultural_commercial" if r < 0.85 else "unknown"
        else:
            rec["land_classification"] = ("non_agricultural_residential" if r < 0.8 else
                                          "agricultural" if r < 0.85 else "unknown")
        rec["conversion_status"] = pick(rng, {"converted_claimed": 0.7, "conversion_in_progress": 0.08,
                                              "not_converted": 0.07, "unknown": 0.15})
        if rec["land_classification"] == "agricultural":
            rec["conversion_status"] = rng.choice(["not_converted", "conversion_in_progress", "unknown"])
        is_plot = ptype in ("residential_plot", "commercial_plot")
        rec["layout_approval_status"] = pick(rng, {"approved_layout_claimed": 0.65, "unapproved_layout": 0.15,
                                                   "unknown": 0.2}) if is_plot else "not_applicable"
        road = pick(rng, {"highway": 0.05, "main_road": 0.25, "paved_internal": 0.55, "unpaved": 0.1,
                          "unknown": 0.05} if not rural else
                    {"main_road": 0.2, "paved_internal": 0.35, "unpaved": 0.35, "unknown": 0.1})
        if commercial and road == "paved_internal" and rng.random() < 0.5:
            road = "main_road"
        frontage = width if rng.random() < 0.7 else None
        corner = rng.random() < 0.15 if is_plot else None
        rate = SYNTHETIC_NA_RATE[name]
        if ptype == "independent_house":
            type_mult = rng.uniform(1.6, 1.9)  # synthetic premium for a built structure
        elif ptype == "commercial_building":
            type_mult = rng.uniform(2.4, 2.8)
        else:
            type_mult = TYPE_MULT[ptype]
        price = (rate * sqft * type_mult * CONV_MULT[rec["conversion_status"]]
                 * LAYOUT_MULT[rec["layout_approval_status"]] * ROAD_MULT[road]
                 * (1.08 if corner else 1.0) * (sqft / 1200) ** -0.06)

    rec["road_access"] = road
    rec["road_frontage_ft"] = frontage
    rec["plot_width_ft"] = width
    rec["plot_length_ft"] = length
    rec["is_corner_plot"] = corner
    price *= rng.lognormvariate(0, 0.15)
    step = 10_000 if price > 2_000_000 else 5_000
    rec["asking_price_inr"] = int(max(step, round(price / step) * step))
    rec["normalized_area_sqft_expected"] = round(sqft, 4)
    rec["listed_on"] = (REFERENCE_DATE - timedelta(days=rng.randint(0, 180))).isoformat()
    rec["listing_status"] = pick(rng, {"approved": 0.88, "pending": 0.07, "rejected": 0.03, "flagged": 0.02})
    rec["amenities"] = amenities_for(rng, ptype, rural, rec.pop("_irrigation", False))
    rec.update(documents_for(rng, rec))
    rec["title"], rec["description"] = text_for(rng, rec, width, length)
    rec["general_address"] = f"{name}, {city}, Dharwad district (approximate, demo)"
    return rec


def amenities_for(rng: random.Random, ptype: str, rural: bool, irrigation: bool) -> str:
    """'code:km;code:km' with synthetic straight-line distances."""
    pool = (["bus_stop", "electricity", "apmc_market", "school"] if rural else
            ["school", "college", "hospital", "bus_stop", "brts_stop", "municipal_water", "electricity",
             "underground_drainage", "market", "park", "railway_station"])
    chosen = rng.sample(pool, k=rng.randint(2, min(len(pool), 6)))
    if ptype == "agricultural_land":
        chosen = [c for c in chosen if c not in ("underground_drainage", "municipal_water")]
        if irrigation:
            chosen.append(rng.choice(["borewell", "canal_or_tank"]))
    far = 6.0 if rural else 2.5
    return ";".join(f"{c}:{round(rng.uniform(0.2, far), 1)}" for c in chosen)


def documents_for(rng: random.Random, rec: dict) -> dict:
    """doc_<type> columns with availability values. Verification is never 'verified'."""
    quality = rng.uniform(0.25, 1.0)
    ptype = rec["property_type"]
    built = ptype in ("independent_house", "commercial_building")
    plot = ptype in ("residential_plot", "commercial_plot")
    out = {}
    for t in DocumentType:
        name = t.value
        applicable = name in ("rtc_pahani", "mutation_record", "encumbrance_certificate", "sale_deed")
        applicable |= ptype != "agricultural_land" and name in ("khata", "dc_conversion_order")
        applicable |= plot and name == "layout_approval"
        applicable |= built and name in ("building_plan_approval", "commencement_certificate",
                                         "completion_certificate", "occupancy_certificate")
        if name == "rera_registration":
            out[f"doc_{name}"] = "unknown" if plot and rng.random() < 0.3 else "not_applicable"
            continue
        if not applicable:
            continue
        p = quality + (0.1 if name in ("rtc_pahani", "encumbrance_certificate", "sale_deed") else 0)
        if name == "dc_conversion_order" and rec["conversion_status"] != "converted_claimed":
            p = 0.05
        if name == "layout_approval" and rec["layout_approval_status"] != "approved_layout_claimed":
            p = 0.05
        r = rng.random()
        out[f"doc_{name}"] = "provided" if r < p else ("not_provided" if rng.random() < 0.7 else "unknown")
    return out


def _inr(v: int) -> str:
    return f"₹{v / 1e5:.1f} lakh" if v < 1e7 else f"₹{v / 1e7:.2f} crore"


def text_for(rng: random.Random, rec: dict, w, l) -> tuple[str, str]:
    loc, ptype = rec["locality"], rec["property_type"]
    facing = rng.choice(["East-facing", "North-facing", "West-facing", "South-facing"])
    if ptype == "agricultural_land":
        unit = "acres" if rec["area_unit"] == "acre" else "guntas"
        title = f"{rec['area_value']:g} {unit} of farmland near {loc}"
        body = (f"Agricultural land of {rec['area_value']:g} {unit} near {loc}, {rec['city']}. "
                f"Road access: {rec['road_access'].replace('_', ' ')}.")
    else:
        label = {"residential_plot": "residential plot", "independent_house": "independent house",
                 "commercial_plot": "commercial plot", "commercial_building": "commercial building"}[ptype]
        title = f"{facing} {w}×{l} ft {label} in {loc}"
        body = (f"{facing} {label} measuring about {w}×{l} ft in {loc}, {rec['city']}. "
                f"Conversion status as stated: {rec['conversion_status'].replace('_', ' ')}. "
                f"Layout approval as stated: {rec['layout_approval_status'].replace('_', ' ')}.")
    body += (" This is a synthetic demonstration listing generated for the PropWise AI college project. "
             "It is not a real property for sale and its price is not market data.")
    return title[:160], body


def inject_imperfections(rng: random.Random, records: list[dict]) -> None:
    # Near-duplicates: same property re-listed with tiny changes (tests duplicate grouping).
    for i, src in enumerate(rng.sample(records, 6)):
        dup = dict(src)
        dup["source_record_id"] = f"SYN-D{i:02d}"
        dup["asking_price_inr"] = int(round(src["asking_price_inr"] * rng.uniform(0.99, 1.01) / 1000) * 1000)
        dup["title"] = src["title"] + " (re-listed)"
        dup["_anomaly"] = f"near_duplicate_of:{src['source_record_id']}"
        records.append(dup)
    candidates = [r for r in records if "_anomaly" not in r]
    # Price outliers (typo-like x10 / x0.1 and a x3).
    for r, f in zip(rng.sample(candidates, 3), (10, 0.1, 3)):
        r["asking_price_inr"] = int(r["asking_price_inr"] * f)
        r["_anomaly"] = f"price_outlier_x{f}"
    candidates = [r for r in records if "_anomaly" not in r and r["plot_width_ft"]]
    # Dimensions that don't match the stated area.
    for r in rng.sample(candidates, 3):
        r["plot_length_ft"] = r["plot_length_ft"] + 25
        r["_anomaly"] = "dimension_mismatch"
    # Missing road access.
    for r in rng.sample([r for r in records if "_anomaly" not in r], 5):
        r["road_access"] = "unknown"
        r["_anomaly"] = "road_access_removed"


COLUMNS = ["source_record_id", "is_synthetic", "data_source", "title", "description", "property_type",
           "intended_land_use", "land_classification", "conversion_status", "layout_approval_status", "city",
           "district", "locality", "general_address", "latitude", "longitude", "coordinates_approximate",
           "area_value", "area_unit", "normalized_area_sqft_expected", "plot_width_ft", "plot_length_ft",
           "road_frontage_ft", "road_access", "is_corner_plot", "asking_price_inr", "amenities", "listed_on",
           "listing_status"] + [f"doc_{t.value}" for t in DocumentType] + ["injected_anomaly"]


def generate(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    records = [make_record(rng, i + 1) for i in range(n)]
    inject_imperfections(rng, records)
    for r in records:
        r["injected_anomaly"] = r.pop("_anomaly", "")
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parents[2] / "data" / "raw" / "synthetic_properties_v1.csv")
    args = ap.parse_args()
    records = generate(args.n, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({k: ("" if r.get(k) is None else r.get(k, "")) for k in COLUMNS})
    print(f"Wrote {len(records)} SYNTHETIC records to {args.out} (seed={args.seed})")


if __name__ == "__main__":
    main()
