#!/usr/bin/env bash
set -euo pipefail

# Enables the Bibliotalk appservice in the Synapse homeserver config.
# Assumes docker compose is run from deploy/local/.

APP_SERVICE_FILE="/data/appservices/bibliotalk-appservice.yaml"
HS_CONFIG="/data/homeserver.yaml"

if [[ ! -f "synapse/data/homeserver.yaml" ]]; then
  echo "ERROR: synapse/data/homeserver.yaml not found. Start synapse once first:" >&2
  echo "  docker compose up -d synapse" >&2
  exit 1
fi

mkdir -p synapse/data/appservices

if [[ ! -f "synapse/data/appservices/bibliotalk-appservice.yaml" ]]; then
  echo "ERROR: synapse/data/appservices/bibliotalk-appservice.yaml not found." >&2
  echo "Create it (tokens must match your .env) and retry." >&2
  exit 1
fi

if ! grep -q "^app_service_config_files:" synapse/data/homeserver.yaml >/dev/null 2>&1; then
  echo "" >> synapse/data/homeserver.yaml
  echo "app_service_config_files:" >> synapse/data/homeserver.yaml
fi

if ! grep -q "bibliotalk-appservice\\.yaml" synapse/data/homeserver.yaml >/dev/null 2>&1; then
  echo "  - ${APP_SERVICE_FILE}" >> synapse/data/homeserver.yaml
fi

echo "Synapse config patched. Restart Synapse:"
echo "  docker compose restart synapse"
