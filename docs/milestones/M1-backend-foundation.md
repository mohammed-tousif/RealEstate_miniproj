# Milestone 1 — Backend foundation, database and demo data

**Date:** 2026-10-14 · **Status:** complete

## Completed functionality
- FastAPI app with versioned API (`/api/v1`), OpenAPI docs at `/docs`, one consistent error format, restricted CORS.
- SQLAlchemy 2 models for all Part D entities; portable enum columns with CHECK constraints; Decimal money/area.
- Alembic migration `0001_initial_schema` (runs on SQLite and PostgreSQL 16).
- Indian area units (sq ft, sq m, gunta, acre) with Decimal conversion; original unit preserved.
- Document model with separate availability and verification; applicability rules per property type;
  weighted documentation-completeness score; "verified" blocked unless a real process is configured.
- Built-in JWT authentication (bcrypt), roles read from the DB on every request, admin creation via CLI only.
- Listings: create (pending), read, partial update (seller edits return to review), archive, document
  declarations, image upload (type sniffed from bytes, size/count limits), favourites, saved preferences.
- Search with 13 filters + text search, 6 sort options, stable pagination, explicit empty results.
- Admin: review queue, approve / reject / flag with reason, document verification states, statistics.
- Data-consistency warnings on the detail response (e.g. residential listing on agricultural land).
- Reproducible synthetic data generator (306 labelled rows incl. injected anomalies), seed script, data dictionary.

## Files created
`backend/app/**` (core, db, models, schemas, services, api), `backend/alembic/**`, `backend/scripts/{generate_synthetic_data,seed_db,create_admin}.py`,
`backend/tests/**`, `data/raw/synthetic_properties_v1.csv`, `docker-compose.yml`, `.env.example`, `README.md`,
`docs/{BLUEPRINT,REQUIREMENTS_CHECKLIST,data_dictionary}.md`.

## Tests performed (actually run)
| Run | Result |
|---|---|
| `pytest` on SQLite, Python 3.13 | 49 passed |
| `pytest` on PostgreSQL 16, Python 3.13 | 49 passed |
| `pytest` on SQLite, Python 3.11 | 49 passed |
| `alembic upgrade head` on SQLite and PostgreSQL | succeeded |
| `seed_db.py` on PostgreSQL, run twice (idempotency) | 306 loaded, then skipped |
| `uvicorn` smoke test: `/docs`, `/health`, filtered search | 200 OK |

Python 3.10 is **not** supported: SQLAlchemy 2.1 requires Python 3.11+.

## Outstanding issues / decisions to revisit
- Auth is built-in JWT instead of Supabase Auth (offline demo). Swap point: `app/core/security.py` + `app/api/deps.py`.
- Images are stored on local disk; document *files* are not uploaded yet (declarations only) — planned with private serving in M6.
- No rate limiting yet (planned for AI endpoints in M5).
- SQLite returns timestamps without a timezone; PostgreSQL returns them with one. Frontend will treat both as UTC.

## Next milestone
**M2 — Frontend platform:** Next.js + TypeScript + Tailwind app on the real API: landing, listings with filters,
map, property details, login/register, seller dashboard with listing form and photo upload, admin review queue.
