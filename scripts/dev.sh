#!/usr/bin/env bash
set -euo pipefail
trap 'kill 0' EXIT

echo "[dev] starting server on :5000"
(
  cd server
  source .venv/bin/activate
  OSRM_BASE_URL="${OSRM_BASE_URL:-https://router.project-osrm.org}" \
  MAX_LOCATIONS="${MAX_LOCATIONS:-10}" \
  TIMEOUT_CONNECT="${TIMEOUT_CONNECT:-2.5}" \
  TIMEOUT_READ="${TIMEOUT_READ:-4.0}" \
  RATE_LIMIT_RULE="${RATE_LIMIT_RULE:-60/minute}" \
  SOLVER_TIME_LIMIT_MS="${SOLVER_TIME_LIMIT_MS:-3000}" \
  python -m flask --app app.py run
) &

echo "[dev] starting frontend on :5173"
(
  cd frontend
  npm run dev
) &

wait
