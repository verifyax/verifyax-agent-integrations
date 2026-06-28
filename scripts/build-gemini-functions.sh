#!/usr/bin/env bash
#
# build-gemini-functions.sh — derive Gemini function declarations from the gateway
# mirror (openapi/verifyax.yaml → gemini/verifyax-functions.json).
#
# Gemini function calling takes a list of {name, description, parameters} where
# `parameters` is a single OBJECT schema in a SUBSET of OpenAPI. So per operation
# this:
#   - name        = operationId
#   - description = operation description/summary
#   - parameters  = path + query params merged with the JSON request body into one
#                   OBJECT schema (required flags preserved)
#   - inlines every $ref (declarations must be self-contained)
#   - simplifies constructs Gemini rejects: allOf merged; oneOf/anyOf collapsed to
#     the first non-null branch (+ nullable); types upper-cased to the proto enum
#   - drops gateway-injected tenant fields (organization_uuid/workspace_uuid/user_uuid)
#
# Re-run after every `sync-openapi.sh`. Transforms a COPY; never edits the mirror.
#
# Usage:
#   scripts/build-gemini-functions.sh
#   IN=openapi/verifyax.yaml OUT=gemini/verifyax-functions.json scripts/build-gemini-functions.sh
#
set -euo pipefail

IN="${IN:-openapi/verifyax.yaml}"
OUT="${OUT:-gemini/verifyax-functions.json}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IN_PATH="$REPO_ROOT/$IN" OUT_PATH="$REPO_ROOT/$OUT" python3 <<'PY'
import os, json, yaml

in_path  = os.environ["IN_PATH"]
out_path = os.environ["OUT_PATH"]
TENANT = {"organization_uuid", "workspace_uuid", "user_uuid"}
TYPE_MAP = {"string": "STRING", "integer": "INTEGER", "number": "NUMBER",
            "boolean": "BOOLEAN", "array": "ARRAY", "object": "OBJECT"}
SAFE_FORMATS = {"STRING": {"date-time", "date", "enum"},
                "INTEGER": {"int32", "int64"}, "NUMBER": {"float", "double"}}

doc = yaml.safe_load(open(in_path, encoding="utf-8"))

def resolve_ref(ref):
    node = doc
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node

def deref(node, seen=()):
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if ref in seen:
                return {}  # cycle guard
            return deref(resolve_ref(ref), seen + (ref,))
        return {k: deref(v, seen) for k, v in node.items()}
    if isinstance(node, list):
        return [deref(x, seen) for x in node]
    return node

def simplify(s):
    """Map a (already de-ref'd) OpenAPI schema to Gemini's schema subset."""
    if not isinstance(s, dict):
        return {"type": "STRING"}
    s = dict(s)

    if "allOf" in s:
        merged = {}
        for sub in s["allOf"]:
            sub = simplify(sub)
            merged.setdefault("type", sub.get("type", "OBJECT"))
            merged.setdefault("properties", {}).update(sub.get("properties", {}))
            merged.setdefault("required", []).extend(sub.get("required", []))
        if "description" in s:
            merged["description"] = s["description"]
        merged = {k: v for k, v in merged.items() if v not in ([], {})}
        s = {**{k: v for k, v in s.items() if k != "allOf"}, **merged}

    for comb in ("oneOf", "anyOf"):
        if comb in s:
            branches = s.pop(comb)
            nullable = any(isinstance(b, dict) and b.get("type") == "null" for b in branches)
            real = [b for b in branches if not (isinstance(b, dict) and b.get("type") == "null")]
            chosen = simplify(real[0]) if real else {"type": "STRING"}
            if "description" in s:
                chosen.setdefault("description", s["description"])
            if nullable:
                chosen["nullable"] = True
            s = {**{k: v for k, v in s.items() if k not in ("oneOf", "anyOf")}, **chosen}

    out = {}
    t = s.get("type")
    if isinstance(t, list):  # OpenAPI 3.1 ['string','null']
        if "null" in t:
            out["nullable"] = True
        non_null = [x for x in t if x != "null"]
        t = non_null[0] if non_null else "string"
    if t:
        out["type"] = TYPE_MAP.get(t, "STRING")
    elif "properties" in s:
        out["type"] = "OBJECT"
    elif "items" in s:
        out["type"] = "ARRAY"
    else:
        out["type"] = "STRING"

    if isinstance(s.get("description"), str):
        out["description"] = s["description"][:1000]
    if isinstance(s.get("enum"), list):
        out["enum"] = [str(x) for x in s["enum"] if x is not None]
        out["type"] = "STRING"
    if s.get("nullable") is True:
        out["nullable"] = True

    fmt = s.get("format")
    if fmt in SAFE_FORMATS.get(out["type"], set()):
        out["format"] = fmt

    if out["type"] == "ARRAY":
        out["items"] = simplify(s.get("items") or {})
    if out["type"] == "OBJECT":
        props = s.get("properties")
        if isinstance(props, dict) and props:
            out["properties"] = {k: simplify(v) for k, v in props.items() if k not in TENANT}
            req = [r for r in s.get("required", []) if r in out["properties"]]
            if req:
                out["required"] = req
    return out

decls = []
for path, item in doc.get("paths", {}).items():
    for method, op in item.items():
        if method not in ("get", "post", "put", "patch", "delete"):
            continue
        name = op.get("operationId")
        if not name:
            continue
        params = {"type": "OBJECT", "properties": {}, "required": []}

        for prm in op.get("parameters", []):
            prm = deref(prm)
            pname = prm.get("name")
            if not pname or pname in TENANT or prm.get("in") not in ("path", "query"):
                continue
            ps = simplify(prm.get("schema") or {})
            if isinstance(prm.get("description"), str):
                ps.setdefault("description", prm["description"][:1000])
            params["properties"][pname] = ps
            if prm.get("required"):
                params["required"].append(pname)

        rb = op.get("requestBody")
        if rb:
            rb = deref(rb)
            js = rb.get("content", {}).get("application/json", {}).get("schema")
            if js:
                body = simplify(js)
                if body.get("type") == "OBJECT" and body.get("properties"):
                    params["properties"].update(body["properties"])
                    for r in body.get("required", []):
                        if r not in params["required"]:
                            params["required"].append(r)
                else:
                    params["properties"]["body"] = body
                    if rb.get("required"):
                        params["required"].append("body")

        decl = {"name": name,
                "description": (op.get("description") or op.get("summary") or name)[:1000]}
        if params["properties"]:
            if not params["required"]:
                params.pop("required")
            decl["parameters"] = params
        decls.append(decl)

# Validate: unique names, no leftover $ref.
names = [d["name"] for d in decls]
dups = sorted({n for n in names if names.count(n) > 1})
assert not dups, f"duplicate function names: {dups}"
blob = json.dumps(decls, indent=2, ensure_ascii=False)
assert "$ref" not in blob, "unresolved $ref remains in output"

with open(out_path, "w", encoding="utf-8") as f:
    f.write(blob + "\n")

print(f"OK: wrote {out_path} — {len(decls)} function declarations, all names unique, no $ref")
PY
