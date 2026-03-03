#!/usr/bin/env bash
set -euo pipefail

# Generates Synapse appservice registration YAML + writes tokens into repo-root .env.
# Run from repo root:
#   deploy/local/bin/generate-appservice.sh

REPO_ROOT="$(CDPATH='' cd "$(dirname "$0")/../../.." && pwd)"
OUT_DIR="${REPO_ROOT}/deploy/local/synapse/data/appservices"
OUT_FILE="${OUT_DIR}/bibliotalk-appservice.yaml"
ENV_FILE="${REPO_ROOT}/.env"

SERVER_NAME="${MATRIX_SERVER_NAME:-localhost}"
AS_URL="${AGENTS_SERVICE_URL:-http://host.docker.internal:8009}"

mkdir -p "${OUT_DIR}"

gen_token() {
  python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
}

AS_TOKEN="${MATRIX_AS_TOKEN:-$(gen_token)}"
HS_TOKEN="${MATRIX_HS_TOKEN:-$(gen_token)}"

cat > "${OUT_FILE}" <<YAML
id: bibliotalk
url: "${AS_URL}"
as_token: "${AS_TOKEN}"
hs_token: "${HS_TOKEN}"
sender_localpart: "bt_appservice"
rate_limited: false
namespaces:
  users:
    - exclusive: true
      regex: "@bt_.*:${SERVER_NAME}"
  aliases:
    - exclusive: true
      regex: "#bt_.*:${SERVER_NAME}"
  rooms: []
YAML

echo "Wrote ${OUT_FILE}"

touch "${ENV_FILE}"
python - "${ENV_FILE}" "${AS_TOKEN}" "${HS_TOKEN}" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
as_token = sys.argv[2]
hs_token = sys.argv[3]

lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
out = []
seen = set()
for line in lines:
    if line.startswith("MATRIX_AS_TOKEN="):
        out.append(f"MATRIX_AS_TOKEN={as_token}")
        seen.add("MATRIX_AS_TOKEN")
        continue
    if line.startswith("MATRIX_HS_TOKEN="):
        out.append(f"MATRIX_HS_TOKEN={hs_token}")
        seen.add("MATRIX_HS_TOKEN")
        continue
    out.append(line)

if "MATRIX_AS_TOKEN" not in seen:
    out.append(f"MATRIX_AS_TOKEN={as_token}")
if "MATRIX_HS_TOKEN" not in seen:
    out.append(f"MATRIX_HS_TOKEN={hs_token}")

env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

echo "Updated ${ENV_FILE} (MATRIX_AS_TOKEN, MATRIX_HS_TOKEN)"
echo ""
echo "Tokens (must match agents_service env):"
echo "  MATRIX_AS_TOKEN=${AS_TOKEN}"
echo "  MATRIX_HS_TOKEN=${HS_TOKEN}"
