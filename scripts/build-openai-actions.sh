#!/usr/bin/env bash
#
# build-openai-actions.sh — derive a GPT Actions-compatible OpenAPI spec from the
# faithful gateway mirror (openapi/verifyax.yaml → openai/verifyax-actions.yaml).
#
# This transforms a COPY of the mirror; it never edits the mirror. Re-run it
# after every `sync-openapi.sh` so the Actions spec tracks the gateway contract.
#
# Transforms applied (see PLAN.md "Normalize notes"):
#   - servers:        → single absolute entry https://console.verifyax.com/api/v1
#                       (and the matching "/v1" prefix is stripped from path keys,
#                        so the effective request URLs are unchanged)
#   - tenant params:  drop organization_uuid / workspace_uuid / user_uuid from every
#                     schema's `properties` + `required` — the gateway injects these
#                     from the API key, so a caller must never send them
#   - security:       keep the Bearer scheme the gateway already declares
#
# Validates operationId uniqueness and OpenAPI 3.x before writing.
#
# Usage:
#   scripts/build-openai-actions.sh
#   IN=openapi/verifyax.yaml OUT=openai/verifyax-actions.yaml scripts/build-openai-actions.sh
#
set -euo pipefail

IN="${IN:-openapi/verifyax.yaml}"
OUT="${OUT:-openai/verifyax-actions.yaml}"
SERVER_URL="${SERVER_URL:-https://console.verifyax.com/api/v1}"
# Path segment (no leading slash) to fold into the server URL and strip from path
# keys. Deliberately slash-less so Git Bash/MSYS doesn't rewrite it to a Windows
# path; the leading "/" is rebuilt in Python. Set empty to keep paths verbatim.
STRIP_PREFIX="${STRIP_PREFIX:-v1}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IN_PATH="$REPO_ROOT/$IN"
OUT_PATH="$REPO_ROOT/$OUT"

# Pass config via env, not argv: MSYS/Git Bash rewrites argv values that look
# like Unix paths (e.g. "/v1" → "C:/Program Files/Git/v1"), but leaves env alone.
IN_PATH="$IN_PATH" OUT_PATH="$OUT_PATH" SERVER_URL="$SERVER_URL" STRIP_PREFIX="$STRIP_PREFIX" \
python3 <<'PY'
import os, yaml

in_path     = os.environ["IN_PATH"]
out_path    = os.environ["OUT_PATH"]
server_url  = os.environ["SERVER_URL"]
# slash-less segment from the shell → leading "/" rebuilt here (see note above)
seg = os.environ.get("STRIP_PREFIX", "").strip().strip("/")
strip_prefix = ("/" + seg) if seg else ""
TENANT = {"organization_uuid", "workspace_uuid", "user_uuid"}

doc = yaml.safe_load(open(in_path, encoding="utf-8"))
assert str(doc.get("openapi", "")).startswith("3"), "input is not OpenAPI 3.x"

# 1. Single absolute server; strip the matching prefix from path keys.
doc["servers"] = [{"url": server_url, "description": "VerifyAX Gateway public API"}]
new_paths = {}
for p, item in doc.get("paths", {}).items():
    key = p
    if strip_prefix and p.startswith(strip_prefix):
        key = p[len(strip_prefix):] or "/"
    assert key not in new_paths, f"path collision after stripping prefix: {key}"
    new_paths[key] = item
doc["paths"] = new_paths

# 2. Drop gateway-injected tenant fields from every schema (properties + required)
#    and from any operation parameters (defensive — the mirror has none today).
def strip_tenant(node):
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for name in list(props):
                if name in TENANT:
                    del props[name]
        req = node.get("required")
        if isinstance(req, list):
            node["required"] = [r for r in req if r not in TENANT]
            if not node["required"]:
                del node["required"]
        for v in node.values():
            strip_tenant(v)
    elif isinstance(node, list):
        for v in node:
            strip_tenant(v)

strip_tenant(doc.get("components", {}).get("schemas", {}))
for item in doc["paths"].values():
    for m, op in list(item.items()):
        if m not in ("get", "post", "put", "patch", "delete"):
            continue
        params = op.get("parameters")
        if isinstance(params, list):
            op["parameters"] = [pr for pr in params if pr.get("name") not in TENANT]
        rb = op.get("requestBody")
        if rb:
            strip_tenant(rb)

# 3. Keep the Bearer security the gateway declares (assert it's intact).
schemes = doc.get("components", {}).get("securitySchemes", {})
assert schemes, "no securitySchemes to carry over"

# Validate operationId uniqueness.
ids = [op["operationId"]
       for item in doc["paths"].values()
       for m, op in item.items()
       if m in ("get", "post", "put", "patch", "delete") and op.get("operationId")]
dups = sorted({i for i in ids if ids.count(i) > 1})
assert not dups, f"duplicate operationIds: {dups}"

with open(out_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True, width=100)

print(f"OK: wrote {out_path} — server {server_url} — {len(doc['paths'])} paths — "
      f"{len(ids)} operations, all operationIds unique")
PY
