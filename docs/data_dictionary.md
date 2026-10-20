# Data Dictionary

## Dataset files

| Path | Stage | Contents |
|---|---|---|
| `data/raw/synthetic_properties_v1.csv` | Raw | Output of `generate_synthetic_data.py --n 300 --seed 42`: 306 rows (300 generated + 6 injected near-duplicates). **Synthetic.** |
| `data/raw/real_listings_1acre_v1.csv` | Raw | 22 **real** land/plot listings copied from public 1acre.in pages on 2026-10-20 by `backend/scripts/build_real_listings.py`. Same columns plus `source_url`, `source_retrieved_on` |
| `data/processed/` | Processed | Cleaned, normalised data (created by the Milestone 3 pipeline) |
| `data/training/` | Training | Model-ready snapshots, versioned by content hash (Milestone 3) |

**Source metadata.** `data_source = synthetic_generator_v1`; licence: created for this project, no third-party data.
No property portal was scraped. Locality names are real place names; coordinates are rough approximations.

## Raw CSV columns

| Column | Type | Description |
|---|---|---|
| source_record_id | string | `SYN-0001`… ; injected near-duplicates are `SYN-D00`… |
| is_synthetic | bool | Always `True` for generator output |
| data_source | string | `synthetic_generator_v1` |
| title, description | text | Template text; description states the listing is synthetic |
| property_type | enum | `residential_plot`, `independent_house`, `agricultural_land`, `commercial_plot`, `commercial_building` |
| intended_land_use | enum | `residential`, `agricultural`, `commercial`, `mixed`, `unknown` |
| land_classification | enum | `agricultural`, `non_agricultural_residential`, `non_agricultural_commercial`, `unknown` (as declared) |
| conversion_status | enum | `converted_claimed`, `conversion_in_progress`, `not_converted`, `not_applicable`, `unknown` |
| layout_approval_status | enum | `approved_layout_claimed`, `unapproved_layout`, `not_applicable`, `unknown` |
| city, district, locality | string | Hubballi or Dharwad; district Dharwad; one of 21 localities |
| general_address | string | Locality-level text, marked approximate |
| latitude, longitude | decimal(9,6) | Jittered around an approximate locality point; `coordinates_approximate=True` |
| area_value, area_unit | decimal, enum | Original value and unit (`sqft`, `sqm`, `gunta`, `acre`) |
| normalized_area_sqft_expected | decimal | Generator's own sq ft figure, used to test the backend conversion |
| plot_width_ft, plot_length_ft | decimal | Present for plots/buildings; empty for farmland |
| road_frontage_ft | decimal | Often missing (realistic) |
| road_access | enum | `highway`, `main_road`, `paved_internal`, `unpaved`, `no_direct_access`, `unknown` |
| is_corner_plot | bool | Plots only; empty otherwise |
| asking_price_inr | integer | **Synthetic** asking price (formula in the generator docstring) |
| amenities | string | `code:km;code:km`, straight-line distances that are synthetic |
| listed_on | date | Synthetic listing date within 180 days before 2026-10-01 |
| listing_status | enum | `approved` ≈88%, `pending`, `rejected`, `flagged` (for the admin demo) |
| doc_<document_type> | enum | Availability for each applicable document: `provided`, `not_provided`, `unknown`, `not_applicable`; empty = not applicable |
| injected_anomaly | string | Ground truth for data-quality checks: `near_duplicate_of:<id>`, `price_outlier_x<k>`, `dimension_mismatch`, `road_access_removed` |

## Units

Canonical: square feet. `1 acre = 43,560 sq ft`, `1 gunta = 1,089 sq ft` (40 guntas = 1 acre), `1 sq m = 10.7639104 sq ft`.
Money: INR, `NUMERIC(14,2)`. Areas: `NUMERIC(16,4)`. Both serialised as decimal strings in the API.

## Document status

Stored as two columns per document (`availability`, `verification_status`) and shown as one of six labels:
*Not provided*, *Provided – unverified*, *Verification pending*, *Verified*, *Not applicable*, *Unknown*.
`Verified` cannot be set unless `DOCUMENT_VERIFICATION_PROCESS_ENABLED=true` and an admin gives a reference.
Seed data never contains `verified`.

## Synthetic-data rules

1. Every synthetic row has `is_synthetic=true` and `data_source` set; the API returns `is_synthetic` on every listing.
2. Demo owners are demo accounts (`…@demo.propwise.example`), never real people.
3. Synthetic prices are produced by a stated formula with invented base rates; they say nothing about the real market.
4. Genuine data uses the same columns with `is_synthetic=false` and a real `data_source` (see below).

## Real listings

`data/raw/real_listings_1acre_v1.csv`, rows `REAL-1ACRE-<listing id>`, `data_source = 1acre_public_listing`.

- **Source and rules.** Public listing pages under `https://1acre.in/lands-for-sale/`, whose robots.txt allows them.
  Each page was read once on 2026-10-20. Only property facts were copied: no seller or agent names, phone numbers,
  e-mails or survey numbers. The builder script holds the transcribed values and the mapping rules.
- **Provenance per row.** `source_url` (the listing page), `source_retrieved_on` (2026-10-20), `listed_on` (the date
  the source says the listing was posted). Stored in the `properties` table as `source_url` and
  `source_retrieved_on` (migration `0002`).
- **Unknown stays unknown.** `land_classification`, `conversion_status` and `layout_approval_status` are `unknown`
  for plots (`not_applicable` conversion/layout for land); every applicable document is `unknown`; dimensions,
  frontage, corner and amenities are empty. "Plot" listings use `property_type=residential_plot` with
  `intended_land_use=unknown`; "land" listings use `agricultural_land` (the source files them as agricultural).
- **Road access** comes from the published approach-road text (kept in the description): highway → `highway`,
  blacktop ≥ 40 ft → `main_road`, narrower blacktop → `paved_internal`, kacha → `unpaved`, otherwise `unknown`.
- **Coordinates** are the source's published point rounded to 3 decimals (about 100 m), `coordinates_approximate=True`.
- **Price** is the asking price as displayed (the site rounds lakh/crore figures). Not a sale price or valuation.
- **Owner.** In PropWise these listings belong to a non-login account, "Public listings import (not the seller)".
- **Scope.** 25 Dharwad-district listings were read; 3 outside the Hubballi and Dharwad taluks were left out.
