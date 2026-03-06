#!/usr/bin/env bash
set -euo pipefail

# Enables the Bibliotalk appservice in the Synapse homeserver config.
# Safe to run from anywhere (paths resolved from script location).

REPO_ROOT="$(CDPATH='' cd "$(dirname "$0")/../../.." && pwd)"
LOCAL_DIR="${REPO_ROOT}/deploy/local"
COMPOSE=(docker compose --project-directory "${LOCAL_DIR}" -f "${LOCAL_DIR}/docker-compose.yml")

APP_SERVICE_FILE="/data/appservices/bibliotalk-appservice.yaml"
HS_CONFIG="/data/homeserver.yaml"

HS_HOST_PATH="${LOCAL_DIR}/synapse/data/homeserver.yaml"
AS_HOST_PATH="${LOCAL_DIR}/synapse/data/appservices/bibliotalk-appservice.yaml"

if [[ ! -f "${HS_HOST_PATH}" ]]; then
  echo "Synapse homeserver config not found. Generating..."
  "${COMPOSE[@]}" run --rm synapse generate
fi

mkdir -p "${LOCAL_DIR}/synapse/data/appservices"

if [[ ! -f "${HS_HOST_PATH}" ]]; then
  echo "ERROR: Synapse homeserver config still missing after generate." >&2
  echo "Run manually and inspect errors:" >&2
  echo "  docker compose -f deploy/local/docker-compose.yml run --rm synapse generate" >&2
  exit 1
fi

configured_tls_cert="$(
  sed -nE 's/^tls_certificate_path:[[:space:]]*"?([^"]+)"?/\1/p' "${HS_HOST_PATH}" | head -n1
)"
configured_tls_key="$(
  sed -nE 's/^tls_private_key_path:[[:space:]]*"?([^"]+)"?/\1/p' "${HS_HOST_PATH}" | head -n1
)"
configured_server_name="$(
  sed -nE 's/^server_name:[[:space:]]*"?([^"]+)"?/\1/p' "${HS_HOST_PATH}" | head -n1
)"

to_host_path() {
  local container_path="$1"
  if [[ -z "${container_path}" ]]; then
    return 1
  fi
  if [[ "${container_path}" == /data/* ]]; then
    printf '%s/synapse/data/%s' "${LOCAL_DIR}" "${container_path#/data/}"
    return 0
  fi
  printf '%s' "${container_path}"
}

tls_cert_host_path="$(to_host_path "${configured_tls_cert:-}")"
tls_key_host_path="$(to_host_path "${configured_tls_key:-}")"

if [[ -n "${tls_cert_host_path:-}" && -n "${tls_key_host_path:-}" ]]; then
  if [[ ! -f "${tls_cert_host_path}" || ! -f "${tls_key_host_path}" ]]; then
    if ! command -v openssl >/dev/null 2>&1; then
      echo "ERROR: openssl is required to generate a self-signed cert for Synapse." >&2
      echo "Install openssl (or generate the files manually) and retry." >&2
      exit 1
    fi

    server_name="${configured_server_name:-${SYNAPSE_SERVER_NAME:-${MATRIX_SERVER_NAME:-localhost}}}"
    mkdir -p "$(dirname "${tls_cert_host_path}")" "$(dirname "${tls_key_host_path}")"
    echo "Generating self-signed TLS cert/key for Synapse startup (${server_name})..."
    openssl req -newkey rsa:2048 -nodes -x509 -days 3650 \
      -keyout "${tls_key_host_path}" \
      -out "${tls_cert_host_path}" \
      -subj "/CN=${server_name}" >/dev/null 2>&1
  fi
  if [[ ! -f "${tls_cert_host_path}" || ! -f "${tls_key_host_path}" ]]; then
    echo "ERROR: TLS cert/key still missing for Synapse startup." >&2
    echo "Expected files:" >&2
    echo "  ${tls_cert_host_path}" >&2
    echo "  ${tls_key_host_path}" >&2
    exit 1
  fi
fi

if [[ ! -f "${AS_HOST_PATH}" ]]; then
  echo "ERROR: Synapse appservice registration not found:" >&2
  echo "  ${AS_HOST_PATH}" >&2
  echo "Create it (tokens must match your .env) and retry." >&2
  exit 1
fi

if ! grep -q "^app_service_config_files:" "${HS_HOST_PATH}" >/dev/null 2>&1; then
  echo "" >> "${HS_HOST_PATH}"
  echo "app_service_config_files:" >> "${HS_HOST_PATH}"
fi

if ! grep -q "bibliotalk-appservice\\.yaml" "${HS_HOST_PATH}" >/dev/null 2>&1; then
  echo "  - ${APP_SERVICE_FILE}" >> "${HS_HOST_PATH}"
fi

echo "Synapse config patched. (Re)starting Synapse..."
synapse_container_id="$("${COMPOSE[@]}" ps -a -q synapse 2>/dev/null || true)"
if [[ -n "${synapse_container_id}" ]]; then
  "${COMPOSE[@]}" restart synapse
else
  "${COMPOSE[@]}" up -d synapse
fi
