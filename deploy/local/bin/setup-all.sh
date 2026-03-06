#!/usr/bin/env bash
set -euo pipefail

# Idempotent-ish local E2E bootstrap for Bibliotalk.
# - Sets up .env (if missing)
# - Installs Python deps for agents_service + ingestion_service (via uv)
# - Starts local infra (Synapse + Element Web)
# - Generates + enables Synapse appservice
# - Creates Synapse admin user
# - Seeds Ghost agents into SQLite
# - Runs ingestion manifest to build EverMemOS segments + local segment cache
# - Imports segment cache into SQLite
# - Provisions Matrix rooms/permissions and runs smoke tests
#
# Usage (from repo root):
#   deploy/local/bin/setup-all.sh
#
# Safe to re-run; it will refresh infra and bootstrap steps where needed.

SCRIPT_DIR="$(CDPATH='' cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd "${SCRIPT_DIR}/../../.." && pwd)"

cd "${REPO_ROOT}"

info() { printf '\n[setup-all] %s\n' "$*" >&2; }
warn() { printf '\n[setup-all][WARN] %s\n' "$*" >&2; }
fail() { printf '\n[setup-all][ERROR] %s\n' "$*" >&2; exit 1; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command '$1' not found on PATH."
  fi
}

require_cmd python
require_cmd docker
require_cmd uv

COMPOSE_DIR="${REPO_ROOT}/deploy/local"
COMPOSE=(docker compose --project-directory "${COMPOSE_DIR}" -f "${COMPOSE_DIR}/docker-compose.yml")

AGENTS_DIR="${REPO_ROOT}/services/agents_service"
INGEST_DIR="${REPO_ROOT}/services/ingestion_service"
AGENTS_VENV="${AGENTS_DIR}/.venv"
INGEST_VENV="${INGEST_DIR}/.venv"
AGENTS_PY="${AGENTS_VENV}/bin/python"
INGEST_PY="${INGEST_VENV}/bin/python"

ENV_FILE="${REPO_ROOT}/.env"

###############################################################################
# 1) Ensure .env exists
###############################################################################

if [[ ! -f "${ENV_FILE}" ]]; then
  info "Creating .env from .env.example (edit it after this run if needed)..."
  if [[ -f "${REPO_ROOT}/.env.example" ]]; then
    cp "${REPO_ROOT}/.env.example" "${ENV_FILE}"
  else
    warn ".env.example missing; creating a minimal .env."
    cat > "${ENV_FILE}" <<'EOF'
EMOS_BASE_URL=https://api.evermind.ai
LOG_LEVEL=INFO
EOF
  fi
else
  info ".env already exists; leaving it unchanged."
fi

###############################################################################
# 2) Install Python deps (agents_service + ingestion_service)
###############################################################################

info "Syncing Python deps for agents_service..."
(
  cd "${AGENTS_DIR}"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync --extra dev
)

info "Syncing Python deps for ingestion_service..."
(
  cd "${INGEST_DIR}"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync --extra dev
)

if [[ ! -x "${AGENTS_PY}" ]]; then
  fail "agents_service venv missing at ${AGENTS_PY}"
fi

if [[ ! -x "${INGEST_PY}" ]]; then
  fail "ingestion_service venv missing at ${INGEST_PY}"
fi

###############################################################################
# 3) Start local infra (Synapse + Element Web)
###############################################################################

info "Starting local Docker infra (Synapse + Element Web)..."
"${COMPOSE[@]}" up -d

###############################################################################
# 4) Generate + enable Synapse appservice
###############################################################################

export AGENTS_SERVICE_URL="${AGENTS_SERVICE_URL:-http://host.docker.internal:8009}"

info "Generating + enabling Synapse appservice registration..."
"${SCRIPT_DIR}/setup-appservice.sh"

###############################################################################
# 5) Create Synapse admin user (safe to re-run)
###############################################################################

ADMIN_USER="${MATRIX_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${MATRIX_ADMIN_PASSWORD:-btadmin_pswd123}"

info "Ensuring Synapse admin user '${ADMIN_USER}' exists..."
set +e
"${COMPOSE[@]}" exec -T synapse register_new_matrix_user -c /data/homeserver.yaml http://localhost:8008 \
  -u "${ADMIN_USER}" -p "${ADMIN_PASSWORD}" -a >/dev/null 2>&1
rc=$?
set -e
if [[ ${rc} -ne 0 ]]; then
  warn "register_new_matrix_user exited with ${rc} (this is expected if the user already exists)."
else
  info "Synapse admin user '${ADMIN_USER}' created."
fi

###############################################################################
# 6) Prepare local SQLite + Ghost agents
###############################################################################

info "Ensuring agents_service local SQLite directory exists..."
mkdir -p "${REPO_ROOT}/.agents_service"

info "Seeding Ghost agents into SQLite..."
"${AGENTS_PY}" -m agents_service.bootstrap seed-ghosts

###############################################################################
# 7) Run ingestion manifest to build EverMemOS + segment cache
###############################################################################

MANIFEST_PATH="${REPO_ROOT}/deploy/local/ingest/manifest.yaml"

if [[ ! -f "${MANIFEST_PATH}" ]]; then
  warn "Ingestion manifest not found at ${MANIFEST_PATH}; skipping ingest step."
else
  if [[ -z "${EMOS_BASE_URL:-}" ]]; then
    warn "EMOS_BASE_URL is not set; ingestion may fail against EverMemOS."
  fi

  info "Running ingestion manifest against EverMemOS..."
  "${INGEST_PY}" -m ingestion_service ingest manifest --path "${MANIFEST_PATH}"
fi

###############################################################################
# 8) Import segment cache into SQLite
###############################################################################

SEGMENT_CACHE_DIR="${REPO_ROOT}/.ingestion_service/segment_cache"

if [[ -d "${SEGMENT_CACHE_DIR}" ]]; then
  info "Importing segment cache into agents_service SQLite..."
  "${AGENTS_PY}" -m agents_service.bootstrap import-segment-cache --cache-dir "${SEGMENT_CACHE_DIR}"
else
  warn "Segment cache directory ${SEGMENT_CACHE_DIR} not found; skipping import."
fi

###############################################################################
# 9) Provision Matrix space + rooms + smoke test
###############################################################################

info "Provisioning Matrix space + rooms..."
"${AGENTS_PY}" -m agents_service.bootstrap provision-matrix

info "Posting profile timelines..."
"${AGENTS_PY}" -m agents_service.bootstrap post-profile-timeline

info "Running smoke test..."
"${AGENTS_PY}" -m agents_service.bootstrap smoke-test

###############################################################################
# 10) Final hints
###############################################################################

info "All-in-one setup complete."
echo ""
echo "Next steps:"
echo "  1) Start agents_service in a separate terminal (from repo root):"
echo "       uvicorn agents_service.server:app --host 0.0.0.0 --port 8009"
echo "  2) Open Element Web at: http://localhost:8080"
echo "  3) Log in as: ${ADMIN_USER}"
echo "  4) Open a ghost DM (e.g. Confucius) and send a message."

