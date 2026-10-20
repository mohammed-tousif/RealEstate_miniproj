# Milestone 2 — Frontend platform

**Date:** 2026-10-14 · **Status:** complete

## Completed functionality
- Next.js 14 (App Router) + TypeScript + Tailwind app that talks only to the real backend through one typed client (`src/lib/api.ts`).
- **Landing:** search (city, type, budget in lakh/crore), category tiles with live counts, latest listings, how-it-works, data disclaimer.
- **Listings:** filter sidebar for all backend filters (budget, city, locality, category, area in any unit, land classification, layout approval, road access, intended use, declared documents, text), sorting, pagination, list/map toggle, URL-shareable filters, empty and error states.
- **Details:** photo gallery (or a neutral illustration, never a fake photo), price and ₹/sq ft, key facts incl. acres+guntas for farmland, land and legal claims, six-state document checklist with guidance, "points to check" warnings, map, amenities (synthetic distances marked), comparable listings (same type/city, 60–160% area), compare and favourite actions, admin review panel.
- **Compare:** 2–3 listings side by side, best values highlighted, price-per-sq-ft highlight suppressed with a warning when categories differ.
- **Accounts:** register (buyer/seller), sign in, favourites.
- **Seller:** my listings with status, create/edit form with unit conversion preview and document declarations for applicable documents, photo upload (type/size checked client- and server-side), archive.
- **Admin:** stats cards and charts, review queue by status, approve / reject / flag with reason.
- **Methodology page:** data sources, document model, disclaimers (ML and ranking sections filled in M3/M4).
- Synthetic badge on every synthetic listing; page-level disclaimers.

## Files created
`frontend/` (package.json, configs, `src/app/**` 13 routes, `src/components/**`, `src/lib/**`, `e2e/**`).

## Tests performed (actually run)
| Check | Result |
|---|---|
| `tsc --noEmit` | no errors |
| `next lint` | no warnings or errors |
| `vitest` (formatting, lakh/crore parsing, units, query strings) | 8 passed |
| `next build` | succeeded, 13 routes |
| Playwright against live backend (SQLite, seeded) + production build | 6 passed: landing, filtered search → details, empty state, compare, seller submit → admin approve → visible to guest, phone-width layout |

Screenshots of landing, listings, details, admin and mobile were reviewed; two fixes followed (map placeholder when no
coordinates, filter unit selector width, chart label overlap).

## Outstanding issues
- Map tiles need internet (OpenStreetMap); offline the map shows markers on a grey background.
- Advisor, price estimate and chat pages are not in the navigation yet; they arrive with M3–M5.
- Comparable listings use a simple transparent rule; KNN similarity replaces it in M4.

## Next milestone
**M3 — Price prediction model:** cleaning pipeline and data-quality report, baselines vs Linear Regression vs Random Forest vs Gradient Boosting with leakage-safe splits, metrics in INR, calibrated range, saved pipeline, `/predictions/price` API and the estimate page.
