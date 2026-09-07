#!/usr/bin/env python3
"""Produce a review-oriented Markdown summary of two OpenAPI documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

METHODS = ("get", "post", "put", "patch", "delete")


def _load(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3"):
        raise ValueError(f"{path} is not an OpenAPI 3 document")
    return document


def _operations(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operations: dict[str, dict[str, Any]] = {}
    for path, item in document.get("paths", {}).items():
        if not isinstance(item, dict):
            continue
        for method in METHODS:
            operation = item.get(method)
            if not isinstance(operation, dict):
                continue
            key = operation.get("operationId") or f"{method.upper()} {path}"
            operations[str(key)] = {"method": method.upper(), "path": path, "value": operation}
    return operations


def _changes(old: dict[str, Any], new: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(
        key
        for key in old.keys() & new.keys()
        if json.dumps(old[key], sort_keys=True) != json.dumps(new[key], sort_keys=True)
    )
    return added, removed, changed


def summarize(previous: dict[str, Any], current: dict[str, Any]) -> str:
    old = _operations(previous)
    new = _operations(current)
    added, removed, changed = _changes(old, new)
    old_schemas = previous.get("components", {}).get("schemas", {})
    new_schemas = current.get("components", {}).get("schemas", {})
    schemas_added, schemas_removed, schemas_changed = _changes(old_schemas, new_schemas)
    security_changed = any(
        previous.get(key) != current.get(key) for key in ("security", "servers")
    ) or (
        previous.get("components", {}).get("securitySchemes")
        != current.get("components", {}).get("securitySchemes")
    )

    old_version = previous.get("info", {}).get("version", "unknown")
    new_version = current.get("info", {}).get("version", "unknown")
    lines = [
        "This PR proposes externally sourced API drift for maintainer review.",
        "",
        "## Semantic OpenAPI diff",
        "",
        f"- API version: `{old_version}` → `{new_version}`",
        f"- Operations: {len(old)} → {len(new)}",
        f"- Added: {len(added)}; removed: {len(removed)}; changed: {len(changed)}",
        (
            f"- Component schemas: +{len(schemas_added)}; -{len(schemas_removed)}; "
            f"changed: {len(schemas_changed)}"
        ),
        f"- Server or security configuration changed: {'yes' if security_changed else 'no'}",
    ]
    for heading, keys, source in (
        ("Added operations", added, new),
        ("Removed operations", removed, old),
        ("Changed operations", changed, new),
    ):
        if keys:
            lines.extend(["", f"### {heading}", ""])
            lines.extend(
                f"- `{source[key]['method']} {source[key]['path']}` (`{key}`)" for key in keys
            )
    for heading, keys in (
        ("Added component schemas", schemas_added),
        ("Removed component schemas", schemas_removed),
        ("Changed component schemas", schemas_changed),
    ):
        if keys:
            lines.extend(["", f"### {heading}", ""])
            lines.extend(f"- `{key}`" for key in keys)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    print(summarize(_load(args.previous), _load(args.current)), end="")


if __name__ == "__main__":
    main()
