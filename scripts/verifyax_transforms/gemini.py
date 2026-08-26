"""Derive Gemini function declarations from the gateway mirror.

Each API operation becomes a {name, description, parameters} declaration whose
`parameters` is a single OBJECT schema in Gemini's subset of OpenAPI:
  - `$ref`s are inlined (declarations must be self-contained)
  - path + query params are merged with the JSON request body
  - constructs Gemini rejects are simplified: allOf merged, oneOf/anyOf collapsed
    to the first non-null branch, types upper-cased to the proto enum
  - gateway-injected tenant fields are dropped

The type mapping happens exactly ONCE, at the leaf, on raw (lower-case) schemas
— combinators are resolved on raw sub-schemas first, so a merged/collapsed schema
is never re-mapped (which previously fell through to STRING and dropped its
properties; see BUILD-6).
"""

from __future__ import annotations

from typing import Any

from .curate import CURATED_OPERATION_IDS, unknown_curated_ids
from .normalize import TENANT_FIELDS

_METHODS = ("get", "post", "put", "patch", "delete")
_TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}
_SAFE_FORMATS = {
    "STRING": {"date-time", "date", "enum"},
    "INTEGER": {"int32", "int64"},
    "NUMBER": {"float", "double"},
}


def build_function_declarations(
    mirror: dict[str, Any], curate: bool = True
) -> tuple[list[dict], list[str]]:
    """Return (declarations, warnings). Warnings record lossy union collapses so a
    build can surface them rather than silently ship one arbitrary variant.

    When `curate` is true (default) only the intent-aligned operation set is
    emitted (see curate.py); pass false for the full-surface opt-in build."""
    warnings: list[str] = []
    deref = _make_deref(mirror)
    decls: list[dict] = []

    all_ids = {
        op["operationId"]
        for item in mirror.get("paths", {}).values()
        for method, op in item.items()
        if method in _METHODS and op.get("operationId")
    }
    if curate:
        missing = unknown_curated_ids(all_ids)
        if missing:
            raise ValueError(f"curated operationIds not found in the spec: {sorted(missing)}")

    for path, item in sorted(mirror.get("paths", {}).items()):
        for method, op in sorted(item.items()):
            if method not in _METHODS or not op.get("operationId"):
                continue
            name = op["operationId"]
            if curate and name not in CURATED_OPERATION_IDS:
                continue
            params: dict[str, Any] = {"type": "OBJECT", "properties": {}, "required": []}

            for raw in op.get("parameters", []):
                prm = deref(raw)
                pname = prm.get("name")
                if not pname or pname in TENANT_FIELDS or prm.get("in") not in ("path", "query"):
                    continue
                schema = _simplify(prm.get("schema") or {}, warnings, f"{name}.{pname}")
                if isinstance(prm.get("description"), str):
                    schema.setdefault("description", prm["description"][:1000])
                params["properties"][pname] = schema
                if prm.get("required"):
                    params["required"].append(pname)

            request_body = op.get("requestBody")
            if request_body:
                schema = (
                    deref(request_body).get("content", {}).get("application/json", {}).get("schema")
                )
                if schema:
                    body = _simplify(schema, warnings, f"{name}.body")
                    if body.get("type") == "OBJECT" and body.get("properties"):
                        params["properties"].update(body["properties"])
                        for req in body.get("required", []):
                            if req not in params["required"]:
                                params["required"].append(req)
                    else:
                        params["properties"]["body"] = body
                        if deref(request_body).get("required"):
                            params["required"].append("body")

            decl: dict[str, Any] = {
                "name": name,
                "description": (op.get("description") or op.get("summary") or name)[:1000],
            }
            if params["properties"]:
                if not params["required"]:
                    params.pop("required")
                decl["parameters"] = params
            decls.append(decl)

    names = [d["name"] for d in decls]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        raise ValueError(f"duplicate function names: {dups}")
    return decls, warnings


def _make_deref(root: dict[str, Any]):
    def resolve(ref: str) -> Any:
        node: Any = root
        for part in ref.lstrip("#/").split("/"):
            node = node[part]
        return node

    def deref(node: Any, seen: tuple[str, ...] = ()) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if ref in seen:  # cycle guard
                    return {}
                return deref(resolve(ref), seen + (ref,))
            return {k: deref(v, seen) for k, v in node.items()}
        if isinstance(node, list):
            return [deref(v, seen) for v in node]
        return node

    return deref


def _merge_all_of(schema: dict[str, Any]) -> dict[str, Any]:
    """Merge allOf members into the schema, staying in RAW (lower-case) form."""
    subs = schema.pop("allOf", None)
    if not isinstance(subs, list):
        return schema
    properties = dict(schema.get("properties") or {})
    required = list(schema.get("required") or [])
    type_value = schema.get("type")
    for sub in subs:
        if not isinstance(sub, dict):
            continue
        sub = _merge_all_of(dict(sub))
        type_value = type_value or sub.get("type")
        properties.update(sub.get("properties") or {})
        required.extend(sub.get("required") or [])
    if properties:
        schema["properties"] = properties
        type_value = type_value or "object"
    if required:
        schema["required"] = list(dict.fromkeys(required))
    if type_value:
        schema["type"] = type_value
    return schema


def _collapse_unions(
    schema: dict[str, Any], warnings: list[str], where: str
) -> tuple[dict[str, Any], bool]:
    """Collapse oneOf/anyOf to the first non-null branch (RAW). Returns (schema,
    nullable). Logs when a multi-branch union is collapsed lossily (BUILD-3)."""
    nullable = False
    for comb in ("oneOf", "anyOf"):
        branches = schema.pop(comb, None)
        if not isinstance(branches, list):
            continue
        real = [b for b in branches if not (isinstance(b, dict) and b.get("type") == "null")]
        if len(real) != len(branches):
            nullable = True
        if len(real) > 1:
            warnings.append(
                f"{where}: collapsed {comb} of {len(real)} branches to the first "
                f"({(real[0] or {}).get('type', '?')}) — Gemini can't express a union"
            )
        if real and isinstance(real[0], dict):
            for key, value in real[0].items():
                schema.setdefault(key, value)
    return schema, nullable


def _simplify(schema: Any, warnings: list[str], where: str) -> dict[str, Any]:
    """Map a raw OpenAPI schema to Gemini's subset. Type is mapped once, at the end."""
    if not isinstance(schema, dict):
        return {"type": "STRING"}
    schema = _merge_all_of(dict(schema))
    schema, nullable = _collapse_unions(schema, warnings, where)
    if schema.get("nullable") is True:
        nullable = True

    out: dict[str, Any] = {}
    type_value = schema.get("type")
    if isinstance(type_value, list):
        if "null" in type_value:
            nullable = True
        non_null = [t for t in type_value if t != "null"]
        type_value = non_null[0] if non_null else None

    if isinstance(type_value, str) and type_value in _TYPE_MAP:
        out["type"] = _TYPE_MAP[type_value]
    elif "properties" in schema:
        out["type"] = "OBJECT"
    elif "items" in schema:
        out["type"] = "ARRAY"
    else:
        out["type"] = "STRING"

    if isinstance(schema.get("description"), str):
        out["description"] = schema["description"][:1000]
    if isinstance(schema.get("enum"), list):
        out["enum"] = [str(v) for v in schema["enum"] if v is not None]
        out["type"] = "STRING"
    if nullable:
        out["nullable"] = True

    fmt = schema.get("format")
    if fmt in _SAFE_FORMATS.get(out["type"], set()):
        out["format"] = fmt

    if out["type"] == "ARRAY":
        out["items"] = _simplify(schema.get("items") or {}, warnings, f"{where}[]")
    if out["type"] == "OBJECT":
        props = schema.get("properties")
        if isinstance(props, dict) and props:
            out["properties"] = {
                k: _simplify(v, warnings, f"{where}.{k}")
                for k, v in props.items()
                if k not in TENANT_FIELDS
            }
            req = [r for r in (schema.get("required") or []) if r in out["properties"]]
            if req:
                out["required"] = req
    return out
