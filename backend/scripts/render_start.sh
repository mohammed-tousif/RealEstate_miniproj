#!/usr/bin/env bash
# Start command for the API on Render (and any similar host): migrate, seed the synthetic demo data and the
# real imported listings if they are not loaded yet, then serve. Safe to run on every start: both steps are idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."
alembic upgrade head
python scripts/seed_db.py
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
