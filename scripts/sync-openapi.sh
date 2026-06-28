#!/usr/bin/env bash
#
# sync-openapi.sh — pull the VerifyAX Gateway public OpenAPI spec into this repo.
#
# Source of truth: the static spec the gateway frontend serves at
#   https://console.verifyax.com/openapi.yaml
# (frontend/user-webapp/public/openapi.yaml — documents the public API under /api/v1).
#
# This makes a FAITHFUL mirror: it fetches and validates the spec, but does NOT
# transform it. Provider-specific massaging (GPT Actions single-server/operationId
# rules, Gemini function declarations) belongs in the openai/ and gemini/ build
# steps, so the mirror stays a clean 1:1 of the gateway contract and drift is easy
# to read in the sync PR.
#
# Usage:
#   scripts/sync-openapi.sh
#   SPEC_URL=https://.../openapi.yaml OUT=openapi/verifyax.yaml scripts/sync-openapi.sh
#
set -euo pipefail

SPEC_URL="${SPEC_URL:-https://console.verifyax.com/openapi.yaml}"
OUT="${OUT:-openapi/verifyax.yaml}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_PATH="$REPO_ROOT/$OUT"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

echo "Fetching $SPEC_URL"
curl -fsSL --retry 3 --retry-delay 2 --max-time 60 "$SPEC_URL" -o "$TMP"

# Validate: parses as YAML and looks like an OpenAPI 3.x document.
python3 - "$TMP" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
assert isinstance(doc, dict), "spec is not a YAML mapping"
ver = str(doc.get("openapi", ""))
assert ver.startswith("3"), f"unexpected/missing openapi version: {ver!r}"
assert doc.get("paths"), "spec has no paths"
info = doc.get("info", {})
print(f"OK: OpenAPI {ver} — {info.get('title','?')} v{info.get('version','?')} — {len(doc['paths'])} paths")
PY

mkdir -p "$(dirname "$OUT_PATH")"
cp "$TMP" "$OUT_PATH"
echo "Wrote $OUT"
