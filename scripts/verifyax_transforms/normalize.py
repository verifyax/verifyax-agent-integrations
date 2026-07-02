"""Shared normalization used by both provider adapters."""

from __future__ import annotations

from typing import Any

# Tenant fields the gateway injects from the API key; a caller must never send
# them. They may legitimately appear in *response* bodies, so stripping is scoped
# to request inputs by the callers (see the OpenAI adapter / BUILD-7).
TENANT_FIELDS = frozenset({"organization_uuid", "workspace_uuid", "user_uuid"})


def strip_tenant(node: Any) -> None:
    """Recursively remove tenant fields from a schema node's `properties` and
    `required`. Mutates in place. Only follows inline schemas — a `$ref` is a
    plain string, so referenced (shared) component schemas are left untouched."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for name in list(props):
                if name in TENANT_FIELDS:
                    del props[name]
        req = node.get("required")
        if isinstance(req, list):
            node["required"] = [r for r in req if r not in TENANT_FIELDS]
            if not node["required"]:
                del node["required"]
        for value in node.values():
            strip_tenant(value)
    elif isinstance(node, list):
        for value in node:
            strip_tenant(value)


def normalize_nullable_30(node: Any) -> None:
    """Rewrite 3.1-style nullability to valid OpenAPI 3.0.x, in place.

    The gateway declares `openapi: 3.0.x` but uses 3.1 constructs (`{type: "null"}`
    inside oneOf/anyOf, or `type: [..., "null"]`). In 3.0 `nullable: true` is only
    meaningful beside a scalar `type`, so: drop null members, set `nullable` only
    where a scalar `type` exists, and strip any orphan `nullable`."""
    if isinstance(node, dict):
        for comb in ("oneOf", "anyOf"):
            branches = node.get(comb)
            if isinstance(branches, list):
                kept = [b for b in branches if not _is_null_schema(b)]
                node[comb] = kept
                if len(kept) != len(branches) and isinstance(node.get("type"), str):
                    node["nullable"] = True
        type_value = node.get("type")
        if isinstance(type_value, list):
            if "null" in type_value:
                node["nullable"] = True
            non_null = [t for t in type_value if t != "null"]
            node["type"] = non_null[0] if non_null else "string"
        if node.get("nullable") is True and not isinstance(node.get("type"), str):
            del node["nullable"]
        for value in node.values():
            normalize_nullable_30(value)
    elif isinstance(node, list):
        for value in node:
            normalize_nullable_30(value)


def _is_null_schema(branch: Any) -> bool:
    return isinstance(branch, dict) and branch.get("type") == "null"
