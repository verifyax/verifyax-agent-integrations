"""Derive a GPT Actions-compatible OpenAPI spec from the gateway mirror.

Transforms (see PLAN.md "Normalize notes"):
  - servers → single absolute entry; the matching path prefix is folded out of
    the path keys so request URLs are unchanged.
  - drop gateway-injected tenant fields from request inputs only (BUILD-7):
    parameters and request bodies — never response/component schemas, which may
    legitimately carry them.
  - normalize 3.1-style nullability to valid 3.0.
"""

from __future__ import annotations

import copy
from typing import Any

from .curate import CURATED_OPERATION_IDS, unknown_curated_ids
from .normalize import TENANT_FIELDS, normalize_nullable_30, strip_tenant

_METHODS = ("get", "post", "put", "patch", "delete")


def build_actions_spec(
    mirror: dict[str, Any],
    server_url: str,
    strip_segment: str = "v1",
    curate: bool = True,
    source_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a new GPT Actions-compatible spec derived from `mirror` (unmutated).

    When `curate` is true (default) only the intent-aligned operation set is kept
    (see curate.py); pass false for the full-surface opt-in build. `source_meta`
    (see provenance.py) is stamped into `info.x-verifyax-source` when given."""
    doc = copy.deepcopy(mirror)
    if not str(doc.get("openapi", "")).startswith("3"):
        raise ValueError("input is not an OpenAPI 3.x document")

    if curate:
        _curate_paths(doc)

    if source_meta is not None:
        doc.setdefault("info", {})["x-verifyax-source"] = source_meta

    prefix = "/" + strip_segment.strip().strip("/") if strip_segment.strip() else ""

    # 1. Single absolute server; fold the prefix out of the path keys.
    doc["servers"] = [{"url": server_url, "description": "VerifyAX Gateway public API"}]
    new_paths: dict[str, Any] = {}
    for path, item in doc.get("paths", {}).items():
        key = path[len(prefix):] or "/" if prefix and path.startswith(prefix) else path
        if key in new_paths:
            raise ValueError(f"path collision after stripping prefix: {key}")
        new_paths[key] = item
    doc["paths"] = new_paths

    # 2. Strip tenant fields from request inputs only (BUILD-7): parameters +
    #    request bodies. Response/component schemas are left intact.
    for item in doc["paths"].values():
        for method, operation in list(item.items()):
            if method not in _METHODS or not isinstance(operation, dict):
                continue
            params = operation.get("parameters")
            if isinstance(params, list):
                operation["parameters"] = [
                    p for p in params if p.get("name") not in TENANT_FIELDS
                ]
            request_body = operation.get("requestBody")
            if request_body is not None:
                strip_tenant(request_body)

    # 3. Normalize 3.1 nullability to valid 3.0 across the whole doc.
    normalize_nullable_30(doc)

    if not doc.get("components", {}).get("securitySchemes"):
        raise ValueError("mirror has no securitySchemes to carry over")

    operation_ids = [
        operation["operationId"]
        for item in doc["paths"].values()
        for method, operation in item.items()
        if method in _METHODS and operation.get("operationId")
    ]
    duplicates = sorted({i for i in operation_ids if operation_ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate operationIds: {duplicates}")

    return doc


def _curate_paths(doc: dict[str, Any]) -> None:
    """Keep only curated operations; drop operations and now-empty path items."""
    all_ids = {
        op["operationId"]
        for item in doc.get("paths", {}).values()
        for method, op in item.items()
        if method in _METHODS and isinstance(op, dict) and op.get("operationId")
    }
    missing = unknown_curated_ids(all_ids)
    if missing:
        raise ValueError(f"curated operationIds not found in the spec: {sorted(missing)}")

    kept_paths: dict[str, Any] = {}
    for path, item in doc.get("paths", {}).items():
        for method in list(item):
            op = item[method]
            if method in _METHODS and isinstance(op, dict):
                if op.get("operationId") not in CURATED_OPERATION_IDS:
                    del item[method]
        # Keep the path only if it still has at least one operation.
        if any(m in _METHODS for m in item):
            kept_paths[path] = item
    doc["paths"] = kept_paths
