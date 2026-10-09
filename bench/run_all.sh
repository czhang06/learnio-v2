#!/usr/bin/env bash
# Reproduce every benchmark: for each tagged version, rebuild the database,
# seed it, start the API, and run the k6 scenarios.
#
# Requirements: git, python3 + backend requirements, psql, k6, a running Postgres.
# Usage (from repo root, clean working tree):
#   PGHOST=localhost PGUSER=learnio PGPASSWORD=learnio bash bench/run_all.sh
#
# Results land in bench/results/<tag>__<scenario>.json plus environment.txt.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
[ -z "$(git status --porcelain)" ] || { echo "Commit or stash changes first."; exit 1; }

ORIG_REF="$(git rev-parse --abbrev-ref HEAD)"
BENCH_TMP="$(mktemp -d)"
cp -r bench "$BENCH_TMP/bench"          # keep the harness from the current checkout
RESULTS="$ROOT/bench/results"
mkdir -p "$RESULTS"

DB_NAME="${DB_NAME:-learnio_bench}"
PGHOST="${PGHOST:-localhost}"; PGPORT="${PGPORT:-5432}"; PGUSER="${PGUSER:-learnio}"; PGPASSWORD="${PGPASSWORD:-learnio}"
export PGHOST PGPORT PGUSER PGPASSWORD
export DATABASE_URL="postgresql+psycopg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${DB_NAME}"
SEED_ROWS="${SEED_ROWS:-500000}"
DURATION="${DURATION:-30s}"; VUS="${VUS:-20}"
TAGS="${TAGS:-baseline opt-1-indexes opt-2-eager-load opt-3-keyset opt-4-exam-sampling}"

{
  echo "date: $(date -u +%FT%TZ)"
  echo "os: $(uname -srm)"
  echo "cpu: $( (lscpu 2>/dev/null | grep 'Model name' | sed 's/.*: *//') || echo unknown)"
  echo "cores: $(nproc 2>/dev/null || echo unknown)"
  echo "postgres: $(psql -d postgres -Atc 'show server_version' 2>/dev/null || echo unknown)"
  echo "seed_rows: $SEED_ROWS  vus: $VUS  duration: $DURATION"
  echo "k6: $(k6 version 2>/dev/null | head -1)"
} > "$RESULTS/environment.txt"

cleanup() { git checkout -q "$ORIG_REF" -- backend 2>/dev/null || true; [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT

for tag in $TAGS; do
  echo "=== $tag ==="
  git checkout -q "$tag" -- backend
  psql -d postgres -qc "DROP DATABASE IF EXISTS $DB_NAME" -c "CREATE DATABASE $DB_NAME"
  (cd backend && alembic upgrade head)
  psql -d "$DB_NAME" -q -v n="$SEED_ROWS" -f "$BENCH_TMP/bench/seed.sql" >/dev/null

  (cd backend && uvicorn app.main:app --port 8000 --workers 2 >/dev/null 2>&1) &
  API_PID=$!
  for _ in $(seq 1 30); do curl -sf localhost:8000/api/health >/dev/null && break; sleep 1; done

  case "$tag" in opt-3-keyset|opt-4-exam-sampling) PAG=cursor ;; *) PAG=offset ;; esac
  run() { # scenario script topic
    k6 run --quiet -e PAGINATION=$PAG -e TOPIC="$3" -e VUS=$VUS -e DURATION=$DURATION \
      --summary-export "$RESULTS/${tag}__$1.json" "$BENCH_TMP/bench/k6/$2" >/dev/null
  }
  run list list.js ""
  run list_topic list.js "topic-3"
  run exam exam.js ""
  run exam_topic exam.js "topic-3"

  kill "$API_PID"; wait "$API_PID" 2>/dev/null || true; API_PID=""
done

python3 "$BENCH_TMP/bench/summarize.py" "$RESULTS" > "$RESULTS/summary.md"
echo "Wrote $RESULTS/summary.md"
