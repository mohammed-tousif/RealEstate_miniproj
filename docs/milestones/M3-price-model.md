# M3 — Price prediction model: status summary

Date: 2026-10-14

## Completed functionality
- **Cleaning pipeline** (`backend/app/ml/data_prep.py`): schema and enum validation, unit conversion to sq ft,
  Karnataka coordinate check, exact-duplicate removal, near-duplicate grouping (same locality and type, area and
  price within 2%, coordinates within 100 m), consistency flags (dimensions vs area, agricultural land with
  conversion claimed, unknown road access) and price-outlier screening against similar listings. Nothing is dropped
  silently; every exclusion is listed in `ml/reports/data_quality.md`.
- **Detector check:** the generator's planted problems (6 near-duplicates, 3 price outliers, 3 dimension mismatches,
  5 removed road-access values) were all detected. The planted-label column is never used for cleaning or as a feature.
  The ×3 outlier is flagged but kept, because a 3× deviation can't be told from a genuine premium.
- **Shared feature builder** (`app/ml/features.py`) used by both training and the API: city, locality, type, land
  classification, conversion, layout approval, log area, road access (ordinal with an unknown indicator), frontage
  (with a missing indicator), corner plot, amenity count and straight-line distance to the city centre.
- **Training** (`app/ml/training.py`, `scripts/train_price_model.py`): 70/15/15 group-aware split (seed 42), two
  baselines, Linear Regression, Random Forest and Gradient Boosting on log price, small grid search for the tree
  models, selection by validation MAE, a single test evaluation, residual-quantile range with measured coverage,
  locality-held-out cross-validation, permutation importance and plots. The joblib pipeline and `metadata.json`
  are saved in `ml/artifacts/price_model/`, with a row in `model_metadata`.
- **API:** `POST /api/v1/predictions/price` (entered fields, or `property_id` for a listing) returns the estimate,
  the indicative range with its measured coverage, the quoted price against the estimate, comparables (approved
  listings of the same type and city), global top factors, warnings and a disclaimer.
  - Warnings cover synthetic training data, unseen localities, few examples of a type, area outside the training
    range, unknown road access, missing coordinates, and a listing that may have been in the training data.
  - It answers 503 when there is no model or the scikit-learn version differs.
- `GET /model-info` now serves the run's metrics, and `/health` reports whether the model is loaded.
- **Frontend:**
  - A `/estimate` page (form with Indian units and lakh/crore input), which is also in the navigation.
  - An estimate card on each listing page, with a range bar and the quoted price marked.
  - A live model-results section on the Methodology page.

## Results from the actual run (synthetic data; see `ml/reports/model_evaluation.md`)
288 clean rows out of 306. Train 200, validation 44, test 44.

| Test set (n = 44) | MAE | MAPE | Median APE | R² |
|---|---|---|---|---|
| Baseline: overall median | ₹33.56 lakh | 91.9% | 55.8% | −0.003 |
| Baseline: locality + type median ₹/sq ft × area | ₹19.59 lakh | 46.1% | 20.8% | 0.653 |
| **Linear Regression (selected on validation)** | ₹7.59 lakh | 15.2% | 11.3% | 0.963 |

- **Validation MAE:** Linear Regression ₹7.85 lakh, Gradient Boosting ₹10.32 lakh, Random Forest ₹12.88 lakh.
- **Why the linear model wins:** the generator multiplies factors, so log price is linear in the features. Genuine
  data might rank the models differently.
- **The 80% range** held 84.1% of the 44 test prices. With so few rows, that figure is itself uncertain.
- **Unseen localities** (5-fold, grouped by locality): the model's MAE was ₹36.82 lakh against ₹21.19 lakh for the
  baseline. It does **not** generalise to new localities, so estimates for one carry a warning.
- **Caveat:** these metrics show the pipeline recovers the generator's rules. They say nothing about the real market.

## Files created or changed
- **Created:**
  - backend/app/ml/: features.py, data_prep.py, baselines.py, training.py, reporting.py, pricing.py, registry.py
  - backend/app/schemas/prediction.py, backend/app/services/prediction_service.py,
    backend/app/api/v1/routes/predictions.py
  - backend/scripts/train_price_model.py, backend/tests/test_price_model.py
  - ml/artifacts/price_model/ (price_model.joblib, metadata.json)
  - ml/reports/ (data_quality.md, model_evaluation.md, plots/*.png)
  - data/processed/clean_properties_v1.csv, data/training/price_training_v1.csv
  - frontend/src/app/estimate/page.tsx
  - frontend/src/components/price/: EstimateResult.tsx, PriceCard.tsx, ModelReport.tsx
  - frontend/e2e/estimate.spec.ts
- **Changed:**
  - backend/app/core/config.py (`PRICE_MODEL_DIR`), backend/app/api/v1/router.py, backend/app/api/v1/routes/system.py
  - backend/requirements.txt (numpy, pandas, scikit-learn, joblib), backend/requirements-dev.txt (matplotlib)
  - frontend: types.ts, api.ts, Navbar, the property detail page, the about page
  - README, this checklist

## Tests performed (actually run)
| Check | Result |
|---|---|
| Backend pytest on SQLite, Python 3.13 | 70 passed (21 new) |
| Backend pytest on PostgreSQL 16 | 70 passed |
| Backend pytest on Python 3.11 (fresh venv from requirements-dev.txt) | 70 passed; saved artifact also loads and predicts |
| New tests cover | feature handling of missing/unknown values, bad areas, missing CSV columns, invalid rows and exact duplicates, planted-problem detection, training reproducibility (same seed → identical metrics), beating both baselines, unseen categories, version mismatch → unavailable, 503 without a model, field and `property_id` estimates, sq ft vs gunta consistency, invalid unit/area/type → 422, unknown locality, extreme area warning, comparables, hidden listing → 404, model-info and health |
| Frontend `tsc`, `next lint`, `vitest` | clean, clean, 8 passed |
| `next build` | succeeded, 14 routes |
| Playwright against live backend + production build | 10 passed (4 new: estimate form with quoted price, farmland in acres, detail-page estimate card, methodology results) |

Screenshots of the estimate page (desktop and phone width, no horizontal scroll), a listing's estimate card and the
methodology page were reviewed. One fix followed: the range-bar labels now sit under the range ends, with a legend.

## Outstanding issues
- `frontend/.env.local.example` could not be copied to the PC (the copy tool refuses `.env*` files). It is optional,
  because the frontend defaults to `http://localhost:8000`, and the README no longer depends on it.
- Seeded listings were part of the training data, so their estimates look closer than they would for a new listing.
  The card says so.
- Top factors are global (permutation importance), not per-property explanations.
- No genuine market data. The CSV schema is ready for it, but genuine data would need retraining and a new evaluation.

## Next milestone
**M4 — Recommendation engine and comparison:**
- hard constraints plus weighted, explainable factor scores with data coverage;
- KNN similar listings;
- evaluation scenarios against baselines;
- the Advisor page, and match scores on the compare page.
