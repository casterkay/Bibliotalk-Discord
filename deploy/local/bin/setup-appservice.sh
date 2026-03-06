#!/usr/bin/env bash
set -euo pipefail

# One-shot helper: generate Bibliotalk appservice registration + enable it in Synapse.
#
# Run from repo root:
#   deploy/local/bin/setup-appservice.sh

SCRIPT_DIR="$(CDPATH='' cd "$(dirname "$0")" && pwd)"

"${SCRIPT_DIR}/generate-appservice.sh"
"${SCRIPT_DIR}/enable-appservice.sh"

echo ""
echo "Appservice ready."
echo "Next:"
echo "  - Ensure agents_service is running on ${AGENTS_SERVICE_URL:-http://host.docker.internal:8009}"
