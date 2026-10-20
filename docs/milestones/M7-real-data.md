# M7 – Real listings (2026-10-20)

## What was added
- **22 real land and plot listings** in the Hubballi and Dharwad taluks, copied by hand from public listing pages on
  1acre.in (robots.txt allows them; one read per page). File: `data/raw/real_listings_1acre_v1.csv`, built by
  `backend/scripts/build_real_listings.py`, which holds the transcribed values and every mapping rule.
- **Provenance in the database.** Migration `0002` adds `properties.source_url` and `properties.source_retrieved_on`.
  Real rows have `is_synthetic=false`, `data_source=1acre_public_listing` and IDs `REAL-1ACRE-<id>`, and belong to a
  non-login import account rather than a demo seller.
- **Seed.** `scripts/seed_db.py` loads them after the synthetic rows (idempotent; `--no-real` skips them). It creates
  13 new localities from the listings' rounded coordinates.
- **Price model.** `scripts/train_price_model.py` now trains on synthetic + real by default. The metadata records the
  mix (`data_mix`) and the caveat says so.
- **UI.** "Real listing · unverified" badge, a source box with a link on the details page, a "Data origin" filter,
  and updated disclaimers on the home, listings, estimate, assistant, Advisor and Methodology pages. The assistant's
  tools return `source_url` and its prompt explains how to describe real listings.

## Results
| | Before (synthetic only) | After (+ real) |
|---|---|---|
| Clean training rows | 288 | 303 (288 synthetic + 15 real) |
| Test MAPE, Linear Regression | 15.2% | 19.4% |
| Test R² | 0.963 | 0.875 |
| 80% range coverage on test | 84.1% | 76.1% |

7 of the 22 real rows were excluded as extreme price outliers against the synthetic rows: real farmland is listed at
roughly ₹35 lakh–₹2 crore per acre, several times the generator's rates. The model is still dominated by synthetic
data and remains a demonstration, not a valuation.

## Not done / where it fell short
- Only 22 real rows: the source showed 27 for Dharwad district (3 out of scope, a second results page unreadable).
- No real houses or commercial listings. Major portals were not used because their terms forbid copying.
- Official guidance values (Kaveri / IGR Karnataka) could not be reached from the build environment.

## Tests
`backend/tests/test_real_listings.py` (CSV matches the builder, provenance and no personal data, road mapping, seed and
API labelling) and a Playwright check that the real-only filter and source link work.
