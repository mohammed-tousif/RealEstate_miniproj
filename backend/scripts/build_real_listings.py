"""Write data/raw/real_listings_1acre_v1.csv: REAL land and plot listings in the Hubballi and
Dharwad taluks, transcribed by hand from public listing pages on 1acre.in.

    python scripts/build_real_listings.py

Collection rules (see docs/data_dictionary.md, "Real listings"):
- Source: https://1acre.in/lands-for-sale/... public pages. Its robots.txt allows these pages
  (it asks for a 10 s crawl delay); 26 pages were read once each on 2026-10-20, no bulk crawling.
- Only property facts were copied. Seller or agent names, phone numbers and e-mails were NOT
  collected. Survey numbers were not collected.
- Facts the page does not state are left empty / "unknown", never guessed: land classification,
  conversion, layout approval, documents, frontage, dimensions and amenities are all unknown.
- Published coordinates are rounded to 3 decimals (about 100 m) and marked approximate.
- Prices are the seller's asking price as displayed on the page (lakh/crore figures are rounded
  by the site). They are asking prices, not sale prices or valuations.
- Approach-road text is kept verbatim in the description. It is mapped to `road_access` as:
  "highway" -> highway; blacktop road of 40 ft or more -> main_road; narrower blacktop ->
  paved_internal; kacha (unpaved) -> unpaved; not stated or type not stated -> unknown.
- Three listings outside the Hubballi and Dharwad taluks (Kalghatgi, Navalgund, Kundgol) were
  read but left out, because PropWise covers Hubballi–Dharwad only.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.enums import (ConversionStatus, DocumentType, LandClassification,  # noqa: E402
                              LayoutApprovalStatus, PropertyType)
from app.services.area_units import to_sqft  # noqa: E402
from app.services.document_rules import applicable_documents  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "raw" / "real_listings_1acre_v1.csv"
RAW_SYNTHETIC = REPO / "data" / "raw" / "synthetic_properties_v1.csv"

DATA_SOURCE = "1acre_public_listing"
RETRIEVED_ON = "2026-10-20"
BASE_URL = "https://1acre.in/lands-for-sale/"

# (listing id, slug, kind, locality, city, area_value, area_unit, asking_price_inr, lat, lng,
#  posted_on, approach road as published or "")
# kind: "plot" (listed as a plot, use not stated) or "land" (listed as land; the page's own
# verification link is in its agricultural category).
LISTINGS = [
    (4040, "146.7-sqyd-plot-in-keshwapur-hubballi-urban-dharwad-karnataka-4040", "plot", "Keshwapur", "Hubballi",
     1320, "sqft", 5_016_000, 15.3598, 75.1728, "2026-09-11", ""),
    (3959, "231.1-sqyd-plot-in-timmasagara-m-hubballi-urban-dharwad-karnataka-3959", "plot", "Timmasagara",
     "Hubballi", 2080, "sqft", 41_600_000, 15.359979, 75.130279, "2026-08-29", ""),
    (3710, "157.2-sqyd-plot-in-kusugal-hubballi-dharwad-karnataka-3710", "plot", "Kusugal", "Hubballi",
     1414.98, "sqft", 2_830_000, 15.385353, 75.193741, "2026-07-27", "abutting 33 ft blacktop road"),
    (14253, "17.9-acre-land-in-karadikop-hubballi-dharwad-karnataka-14253", "land", "Karadikop", "Hubballi",
     717, "gunta", 66_300_000, 15.236084, 75.102817, "2026-04-27", "30 ft kacha road"),
    (2066, "132-sqyd-plot-in-hubballi-hubballi-dharwad-karnataka-2066", "plot", "Hubballi (village not named)",
     "Hubballi", 1188, "sqft", 1_467_000, 15.381781, 75.091631, "2025-10-09", ""),
    (2051, "616-sqyd-plot-in-karadikop-hubballi-dharwad-karnataka-2051", "plot", "Karadikop", "Hubballi",
     5544, "sqft", 1_800_000, 15.209120, 75.113701, "2025-10-08", "abutting 40 ft blacktop road"),
    (10315, "1-acre-land-in-tirumalkoppa-hubballi-dharwad-karnataka-10315", "land", "Tirumalkoppa", "Hubballi",
     1, "acre", 8_000_000, 15.174816, 75.128236, "2025-10-06", "40 ft blacktop road"),
    (9780, "23-acre-land-in-anchatgeri-hubballi-dharwad-karnataka-9780", "land", "Anchatgeri", "Hubballi",
     23, "acre", 460_000_000, 15.286872, 75.064603, "2025-09-19", "60 ft highway road"),
    (9728, "1.6-acre-land-in-halliyala-hubballi-dharwad-karnataka-9728", "land", "Halliyala", "Hubballi",
     63, "gunta", 12_600_000, 15.320359, 75.200749, "2025-09-18", "40 ft blacktop road"),
    (1838, "400-sqyd-plot-in-hubballi-hubballi-dharwad-karnataka-1838", "plot", "Hubballi (village not named)",
     "Hubballi", 3600, "sqft", 12_600_000, 15.382268, 75.146577, "2025-09-23", "abutting 30 ft road, type not stated"),
    (1396, "267-sqyd-plot-in-hubballi-hubballi-dharwad-karnataka-1396", "plot", "Hubballi (village not named)",
     "Hubballi", 2403, "sqft", 8_651_000, 15.365005, 75.175458, "2025-08-28", "abutting 30 ft blacktop road"),
    (8657, "0.6-acre-land-in-hubballi-hubballi-dharwad-karnataka-8657", "land", "Hubballi (village not named)",
     "Hubballi", 23, "gunta", 39_700_000, 15.336213, 75.149290, "2025-08-25", "80 ft blacktop road"),
    (1262, "605-sqyd-plot-in-hubballi-hubballi-dharwad-karnataka-1262", "plot", "Hubballi (village not named)",
     "Hubballi", 5445, "sqft", 20_000_000, 15.370392, 75.048421, "2025-08-14", ""),
    (17582, "4-acre-land-in-tegur-dharwad-dharwad-karnataka-17582", "land", "Tegur", "Dharwad",
     4, "acre", 67_200_000, 15.542504, 74.835252, "2026-10-13", "40 ft blacktop road"),
    (13602, "1.1-acre-land-in-mangalagatti-dharwad-dharwad-karnataka-13602", "land", "Mangalagatti", "Dharwad",
     44, "gunta", 7_700_000, 15.542646, 74.960024, "2026-03-04", "40 ft blacktop road"),
    (11201, "0.2-acre-land-in-mugad-dharwad-dharwad-karnataka-11201", "land", "Mugad", "Dharwad",
     10, "gunta", 3_800_000, 15.446510, 74.915031, "2025-10-28", ""),
    (2079, "605-sqyd-plot-in-manasura-sanna-somapura-dharwad-dharwad-karnataka-2079", "plot",
     "Manasur–Sanna Somapur", "Dharwad", 5445, "sqft", 4_000_000, 15.423058, 74.973447, "2025-10-09", ""),
    (10191, "10-acre-land-in-hebballi-dharwad-dharwad-karnataka-10191", "land", "Hebballi", "Dharwad",
     10, "acre", 100_000_000, 15.509460, 75.190052, "2025-09-29", "40 ft blacktop road"),
    (1890, "1039-sqyd-plot-in-navalur-dharwad-dharwad-karnataka-1890", "plot", "Navalur", "Dharwad",
     9351, "sqft", 42_100_000, 15.427779, 75.034063, "2025-09-26", "abutting 150 ft highway road"),
    (8974, "0.9-acre-land-in-kalakeri-dharwad-dharwad-karnataka-8974", "land", "Kalakeri", "Dharwad",
     38, "gunta", 10_100_000, 15.462173, 74.943792, "2025-09-03", "100 ft kacha road"),
    (8789, "2-acre-land-in-garag-dharwad-dharwad-karnataka-8789", "land", "Garag", "Dharwad",
     2, "acre", 25_000_000, 15.539770, 74.934497, "2025-08-29", "40 ft blacktop road"),
    (1324, "756-sqyd-plot-in-daravada-em-dharwad-dharwad-karnataka-1324", "plot", "Dharwad (village not named)",
     "Dharwad", 6804, "sqft", 40_800_000, 15.451177, 75.012299, "2025-08-21", "abutting 40 ft blacktop road"),
]



def road_access(text: str) -> str:
    t = text.lower()
    if "highway" in t:
        return "highway"
    if "kacha" in t:
        return "unpaved"
    if "blacktop" in t:
        width = int(t.split(" ft")[0].split()[-1])
        return "main_road" if width >= 40 else "paved_internal"
    return "unknown"


def unit_label(value, unit: str) -> str:
    if unit == "sqft":
        return f"{value:,} sq ft"
    if unit == "gunta":
        acres, guntas = divmod(int(value), 40)
        return " ".join(p for p in (f"{acres} acre{'s' if acres != 1 else ''}" if acres else "",
                                     f"{guntas} gunta{'s' if guntas != 1 else ''}" if guntas else "") if p)
    return f"{value:g} acre{'s' if value != 1 else ''}"


def row(rec) -> dict:
    (lid, slug, kind, locality, city, area, unit, price, lat, lng, posted, road) = rec
    ptype = PropertyType.residential_plot if kind == "plot" else PropertyType.agricultural_land
    docs = applicable_documents(ptype, LandClassification.unknown,
                                ConversionStatus.unknown if kind == "plot" else ConversionStatus.not_applicable,
                                LayoutApprovalStatus.unknown if kind == "plot" else LayoutApprovalStatus.not_applicable)
    size = unit_label(area, unit)
    what = "Plot" if kind == "plot" else "Land"
    road_txt = f"Approach road as published: {road}." if road else "Road access is not stated by the source."
    desc = (f"{what} of {size} in {locality}, {city} taluk, Dharwad district, as listed on 1acre.in "
            f"(listing {lid}, posted {posted}; copied {RETRIEVED_ON}). {road_txt} "
            + ("Listed as a plot; the source does not say whether it is residential, converted or in an approved "
               "layout, so those are shown as unknown. " if kind == "plot" else
               "Listed as land in the source's agricultural category; conversion and documents are not stated. ")
            + "This is a REAL third-party listing shown for reference: PropWise does not represent the seller and "
              "has not verified any detail. The price is the seller's asking price as displayed, not a sale price "
              "or valuation. See the original listing for current status.")
    out = {
        "source_record_id": f"REAL-1ACRE-{lid}", "is_synthetic": "False", "data_source": DATA_SOURCE,
        "title": f"{size} {'plot' if kind == 'plot' else 'of land'} in {locality} (real listing, 1acre.in)",
        "description": desc, "property_type": ptype.value,
        "intended_land_use": "unknown" if kind == "plot" else "agricultural",
        "land_classification": "unknown",
        "conversion_status": "unknown" if kind == "plot" else "not_applicable",
        "layout_approval_status": "unknown" if kind == "plot" else "not_applicable",
        "city": city, "district": "Dharwad", "locality": locality,
        "general_address": f"{locality}, {city} taluk, Dharwad district (as published on 1acre.in; approximate)",
        "latitude": f"{lat:.3f}", "longitude": f"{lng:.3f}", "coordinates_approximate": "True",
        "area_value": f"{area:g}", "area_unit": unit,
        "normalized_area_sqft_expected": f"{float(to_sqft(str(area), unit)):g}",
        "plot_width_ft": "", "plot_length_ft": "", "road_frontage_ft": "", "road_access": road_access(road),
        "is_corner_plot": "", "asking_price_inr": str(price), "amenities": "", "listed_on": posted,
        "listing_status": "approved", "injected_anomaly": "",
        "source_url": BASE_URL + slug, "source_retrieved_on": RETRIEVED_ON,
    }
    for t in DocumentType:
        out[f"doc_{t.value}"] = "unknown" if t in docs else ""
    return out


def main() -> None:
    with RAW_SYNTHETIC.open(encoding="utf-8") as fh:
        columns = next(csv.reader(fh)) + ["source_url", "source_retrieved_on"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        for rec in LISTINGS:
            w.writerow(row(rec))
    print(f"Wrote {len(LISTINGS)} REAL listings to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
