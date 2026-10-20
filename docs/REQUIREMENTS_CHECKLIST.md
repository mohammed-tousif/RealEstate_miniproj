# Requirements Checklist

Status: ✅ done and tested · 🟡 partial · ⬜ not started · ➖ future scope by design. Milestone in brackets.
Updated: 2026-10-18 (end of M6). Every item is done or explicitly deferred.

## Domain and data (spec §6, §7-A, §15, §16)
| Requirement | Status |
|---|---|
| Separate property type, land classification, conversion, layout approval, document status | ✅ M1 |
| Six document states incl. "verified only with a real process" | ✅ M1 (verified blocked by default) |
| Document applicability by property type (CC/OC only for buildings, etc.) | ✅ M1 |
| sq ft / sq m / gunta / acre with Decimal conversion, original value kept | ✅ M1 |
| Decimal-safe money and area storage | ✅ M1 |
| All listing fields in §7-A (basic, location, physical, legal, other) | ✅ M1 |
| Normalised relational schema, PK/FK/constraints/indexes, Alembic migrations | ✅ M1 |
| Multi-city ready (localities table with city/district/state) | ✅ M1 |
| ER diagram | ✅ Blueprint Part D |
| Synthetic dataset ~300 records, clearly labelled, reproducible | ✅ M1 (306 rows) |
| Data dictionary, source metadata | ✅ M1 |
| Cleaning pipeline, data quality, missing-value and duplicate reports | ✅ M3 (`ml/reports/data_quality.md`) |
| Official portal links verified (Bhoomi, Kaveri, RERA, HDMC) | ✅ M6 (checked through secondary sources; the government sites could not be opened from the build environment, so open them once by hand before a public demo) |
| Industrial property type | ➖ |

## Listing management and search (§7, §5)
| Requirement | Status |
|---|---|
| Create / read / update / archive listings | ✅ M1 |
| Seller ownership checks; edits send listing back to review | ✅ M1 |
| Admin approve / reject / flag (reason required), review queue, stats | ✅ M1 |
| Image upload: type from file bytes, size and count limits, random names | ✅ M1 |
| Filters: budget min/max, city, locality, category, land class, area min/max, road access, documents, approval, intended use, text | ✅ M1 |
| Sort by price, area, date; pagination; empty results | ✅ M1 |
| Sort by recommendation relevance | ✅ M4 (Advisor results are ranked by suitability; Explore keeps price, area and date sorts) |
| Favourites | ✅ M1 API · ✅ M2 UI |
| Saved preferences | ✅ M1 API · ✅ M4 UI (Advisor form: kept in the browser, and saved to the account when signed in) |
| Private document file upload | ➖ Deferred: declarations only. Render's free tier has no persistent disk for private files, and there is no verification process to use them |

## Security (§19)
| Requirement | Status |
|---|---|
| Auth (JWT, bcrypt), role checks in the API, role read from DB per request | ✅ M1 |
| Admins cannot self-register | ✅ M1 |
| Server-side validation, ORM-parameterised queries | ✅ M1 |
| Secrets via environment, none hardcoded; prod refuses missing JWT secret | ✅ M1 |
| CORS restricted to configured origins | ✅ M1 |
| Safe error messages in one consistent shape | ✅ M1 |
| Consent required to store a listing | ✅ M1 |
| Hidden listings return 404 (not revealed) | ✅ M1 |
| Rate limiting on AI endpoints | ✅ M5 (12 per minute per client) · ✅ M6 failed-login limit (10 per minute per client and email) |
| Security headers | ✅ M6 (API and frontend) |

## AI / ML (§8–§10)
| Requirement | Status |
|---|---|
| Content-based recommendation (hard filters + weighted, configurable, explainable) | ✅ M4 (`weighted-v1`, five factors, importance settings, data coverage, templated explanations) |
| KNN similar properties + comparison with weighted ranking | ✅ M4 |
| Recommendation evaluation without invented labels | ✅ M4 (`ml/reports/recommender_evaluation.md`: constraint checker, baselines, stability; no Precision@K) |
| Price model: baseline, Linear Regression, Random Forest (+GBR), leakage-safe splits | ✅ M3 (two baselines, group-aware split, locality hold-out) |
| MAE, RMSE, R², MAPE in INR; per-type/locality errors; interval coverage | ✅ M3 (`ml/reports/model_evaluation.md`) |
| Saved preprocessing + model; backend inference; synthetic warning | ✅ M3 |
| LLM assistant with validated read-only tools, grounding check, injection resistance | ✅ M5 (nine tools, cited-id grounding check, `<listing_data>` wrapping; adapter tested with mocked SDK responses, not live) |
| Labelled fallback when LLM unavailable | ✅ M5 (Basic search mode, also used on any provider failure) |
| Rule-based risk flags | ✅ M6 |

## Frontend (§12)
| Requirement | Status |
|---|---|
| Page 1 Landing (search, categories, featured, how it works) | ✅ M2 |
| Page 2 Listings (cards, search, filter sidebar, sort, pagination, list/map) | ✅ M2 |
| Page 3 Details (gallery, facts, land/legal, documents, map, amenities, comparables, compare/favourite) | ✅ M2 · ✅ KNN similar listings M4 · ✅ price estimate card M3 · ✅ risk flags and "Ask the assistant" links M5 |
| Page 4 AI Advisor | ✅ M4 |
| Page 5 Price estimate | ✅ M3 |
| Page 6 Chat | ✅ M5 |
| Page 7 Compare (2–3 listings, category-aware ₹/sq ft warning) | ✅ M2 · ✅ match score and rank M4 |
| Page 8 Seller dashboard (list, create, edit, photos, document declarations, archive) | ✅ M2 |
| Page 9 Admin dashboard (queue by status, approve/reject/flag, stats charts) | ✅ M2 |
| Page 10 Methodology (data, document model, disclaimers) | ✅ M2 · ✅ price model results M3 · ✅ ranking method M4 |
| Map (Leaflet + OSM attribution) | ✅ M2 |
| Responsive layout, loading/empty/error states | ✅ M2 (phone-width test passes) |

## Testing and documentation (§21, §23, §24)
| Requirement | Status |
|---|---|
| Backend tests: creation, filtering, invalid input, auth, authorisation, duplicates, pagination, admin workflow | ✅ M1 (now 132 tests incl. M3–M6, SQLite + PostgreSQL, Python 3.11) |
| Frontend: typecheck, lint, 11 unit tests, 17 Playwright browser tests (browse, filters, details, empty state, compare, seller→admin→public workflow, phone width, price estimate ×4, advisor ×3, chat ×3, the full 15-step demo) | ✅ M2–M6 |
| Price model tests (reproducibility, invalid input, unseen categories, extreme areas, loading, output) | ✅ M3 (21 tests) |
| Recommendation tests (constraints, scoring, explanations, stability, random preferences, API) | ✅ M4 (23 tests) |
| LLM tests | ✅ M5 (fake provider, grounding, injection, invalid ids, no matches, provider failure, unauthorised access, price question without a model) |
| README, setup, .env.example, dependency lists, migration instructions | ✅ M1 (updated each milestone) |
| OpenAPI docs | ✅ M1 (`/docs`) |
| Academic report material, viva Q&A, demo script | ✅ M6 (`docs/report/`) |
| API examples per endpoint | ✅ M6 (`docs/api.md`) |
| Deployment | ✅ M6 (`render.yaml`, `DEPLOY.md`; not yet deployed) |
