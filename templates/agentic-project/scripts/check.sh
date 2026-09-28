#!/usr/bin/env bash
# Offline gate for this project: backend tests, lint, types, fixture CLI probes, and the
# frontend build. With --docker it also builds the Compose stack, checks both services
# through their ports, and stops it again (the database volume is kept).
# Never makes a hosted model call and never reads .env values.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DOCKER=false
[[ "${1:-}" == "--docker" ]] && RUN_DOCKER=true

step() { printf '\n== %s\n' "$1"; }

# expect <needle> <command...>: run the command and fail unless its output contains the needle.
expect() {
  local needle="$1" output
  shift
  output="$("$@")"
  if [[ "$output" != *"$needle"* ]]; then
    echo "expected '$needle' from: $*" >&2
    exit 1
  fi
  echo "ok: $* -> $needle"
}

find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
  elif [[ -x "$ROOT/backend/.venv/bin/uv" ]]; then
    echo "$ROOT/backend/.venv/bin/uv"
  else
    # uv lives outside backend/.venv, which uv itself rebuilds for the pinned Python.
    if [[ ! -x "$ROOT/.tools/bin/uv" ]]; then
      python3 -m venv "$ROOT/.tools" >&2
      "$ROOT/.tools/bin/python" -m pip install --quiet uv >&2
    fi
    echo "$ROOT/.tools/bin/uv"
  fi
}

step "backend: install from the lock"
cd "$ROOT/backend"
UV="$(find_uv)"
"$UV" sync --locked

if [[ -f .format-pending ]]; then
  step "backend: format once after new_project.py changed name lengths"
  .venv/bin/ruff format app tests
  rm .format-pending
fi

step "backend: tests, lint, format, types"
.venv/bin/python -m pytest
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/mypy

step "backend: fixture probes (no hosted call)"
.venv/bin/python -m app.cli config-check
expect '"marker": "CONNECTION_OK"' .venv/bin/python -m app.cli smoke

step "frontend: install, audit, and build"
cd "$ROOT/frontend"
npm ci --no-audit --no-fund
npm audit --audit-level=moderate
npm run build

if $RUN_DOCKER; then
  step "docker: build and start"
  cd "$ROOT"
  compose() { docker compose -f docker/compose.yaml "$@"; }
  compose up --build -d
  trap 'compose down >/dev/null 2>&1 || true' EXIT
  for _ in $(seq 1 60); do
    [[ "$(compose ps ui --format '{{.Health}}')" == "healthy" ]] && break
    sleep 2
  done
  compose ps --format '{{.Service}} {{.Health}}'

  step "docker: API directly, and through nginx"
  expect '"db":"connected"' curl -fsS http://127.0.0.1:8000/health
  expect '"db":"connected"' curl -fsS http://127.0.0.1:3000/api/health
  expect '"marker":"CONNECTION_OK"' curl -fsS -X POST http://127.0.0.1:3000/api/diagnostics/connection
  expect '"marker": "CONNECTION_OK"' docker compose -f docker/compose.yaml exec -T api python -m app.cli smoke
fi

step "all offline checks passed"
