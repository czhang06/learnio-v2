#!/usr/bin/env bash
# Reproduce every benchmark. For each tagged version of the backend: export that
# tag into a clean temp folder, create + migrate + seed a fresh database, start the
# API, and run the k6 scenarios against it.
#
# Requirements on PATH: git, python (with backend requirements installed, e.g. an
# activated venv), psql, k6, curl. Works in Git Bash on Windows, Linux, and macOS.
#
# Usage (from anywhere inside the repo):
#   export PGUSER=learnio PGPASSWORD=learnio PGHOST=localhost
#   bash bench/run_all.sh
#
# Results: bench/results/<tag>__<scenario>.json, environment.txt, summary.md
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

PY=""
for c in python python3; do
  if "$c" -c "import sys" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "python not found"; exit 1; }
for tool in psql k6 curl git; do
  command -v "$tool" >/dev/null || { echo "Missing on PATH: $tool"; exit 1; }
done
"$PY" -c "import fastapi, uvicorn, alembic, psycopg" 2>/dev/null \
  || { echo "Activate the backend venv first (pip install -r backend/requirements.txt)."; exit 1; }
if curl -sf localhost:8000/api/health >/dev/null 2>&1; then
  echo "Something is already listening on port 8000. Stop it and retry."; exit 1
fi

DB_NAME="${DB_NAME:-learnio_bench}"
export PGHOST="${PGHOST:-localhost}" PGPORT="${PGPORT:-5432}" PGUSER="${PGUSER:-learnio}" PGPASSWORD="${PGPASSWORD:-learnio}"
export DATABASE_URL="postgresql+psycopg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${DB_NAME}"
SEED_ROWS="${SEED_ROWS:-500000}"
DURATION="${DURATION:-30s}"
VUS="${VUS:-20}"
TAGS="${TAGS:-baseline opt-1-indexes opt-2-eager-load opt-3-keyset opt-4-exam-sampling}"

RESULTS="bench/results"
mkdir -p "$RESULTS"
WORK="$(mktemp -d)"
API_PID=""

stop_api() {
  if [ -n "$API_PID" ]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
    API_PID=""
    for _ in $(seq 1 20); do curl -sf localhost:8000/api/health >/dev/null 2>&1 || return 0; sleep 0.5; done
    echo "Warning: API on port 8000 did not stop; kill it manually before continuing."
  fi
}
trap stop_api EXIT

{
  echo "date: $(date -u +%FT%TZ)"
  echo "os: $(uname -srm)"
  echo "cpu: ${PROCESSOR_IDENTIFIER:-$(lscpu 2>/dev/null | sed -n 's/^Model name: *//p')}"
  echo "cores: ${NUMBER_OF_PROCESSORS:-$(nproc 2>/dev/null || echo unknown)}"
  echo "postgres: $(psql -d postgres -Atc 'show server_version' 2>/dev/null || echo unknown)"
  echo "python: $("$PY" --version 2>&1)"
  echo "k6: $(k6 version 2>/dev/null | head -1)"
  echo "seed_rows: $SEED_ROWS  vus: $VUS  duration: $DURATION  api_workers: 1"
  echo "commit: $(git rev-parse --short HEAD)"
} > "$RESULTS/environment.txt"

for tag in $TAGS; do
  echo "=== $tag ==="
  git rev-parse --verify -q "$tag^{commit}" >/dev/null || { echo "Unknown tag: $tag"; exit 1; }
  mkdir -p "$WORK/$tag"
  git archive "$tag" backend | tar -x -C "$WORK/$tag"      # exactly this version, nothing extra

  psql -d postgres -q -c "DROP DATABASE IF EXISTS $DB_NAME"
  psql -d postgres -q -c "CREATE DATABASE $DB_NAME"
  (cd "$WORK/$tag/backend" && "$PY" -m alembic upgrade head)
  psql -d "$DB_NAME" -q -v n="$SEED_ROWS" -f bench/seed.sql >/dev/null
  psql -d "$DB_NAME" -q -c "VACUUM ANALYZE courses, topics, questions, question_topics"

  (cd "$WORK/$tag/backend" && exec "$PY" -m uvicorn app.main:app --port 8000 >"$WORK/$tag.log" 2>&1) &
  API_PID=$!
  up=0
  for _ in $(seq 1 40); do
    if curl -sf localhost:8000/api/health >/dev/null 2>&1; then up=1; break; fi
    sleep 1
  done
  [ "$up" = 1 ] || { echo "API failed to start for $tag:"; tail -20 "$WORK/$tag.log"; exit 1; }

  case "$tag" in opt-3-keyset|opt-4-exam-sampling) PAG=cursor ;; *) PAG=offset ;; esac
  run() { # <scenario> <script> <topic>
    k6 run --quiet -e PAGINATION="$PAG" -e TOPIC="$3" -e VUS="$VUS" -e DURATION="$DURATION" \
      --summary-export "$RESULTS/${tag}__$1.json" "bench/k6/$2" >/dev/null
  }
  run list list.js ""
  run list_topic list.js "topic-3"
  run exam exam.js ""
  run exam_topic exam.js "topic-3"

  stop_api
done

"$PY" bench/summarize.py "$RESULTS" > "$RESULTS/summary.md"
echo "Done. See $RESULTS/summary.md"
