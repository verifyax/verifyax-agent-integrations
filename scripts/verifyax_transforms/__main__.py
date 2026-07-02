"""CLI: python -m verifyax_transforms {openai|gemini}

Config comes from the environment (the shell wrappers set it) so Git Bash/MSYS
never rewrites a slash-prefixed value into a Windows path:
  openai: IN_PATH, OUT_PATH, SERVER_URL, STRIP_PREFIX (slash-less, e.g. "v1")
  gemini: IN_PATH, OUT_PATH
"""

from __future__ import annotations

import json
import os
import sys

import yaml

from . import build_actions_spec, build_function_declarations
from .provenance import source_meta


def _load_with_bytes(path: str) -> tuple[dict, bytes]:
    with open(path, "rb") as handle:
        raw = handle.read()
    return yaml.safe_load(raw), raw


def _curate() -> bool:
    # Default: the curated intent-aligned surface. FULL=1 opts into all 46 ops.
    return os.environ.get("FULL", "").strip().lower() not in ("1", "true", "yes")


def _openai() -> None:
    mirror, raw = _load_with_bytes(os.environ["IN_PATH"])
    curate = _curate()
    spec = build_actions_spec(
        mirror,
        server_url=os.environ["SERVER_URL"],
        strip_segment=os.environ.get("STRIP_PREFIX", "v1"),
        curate=curate,
        source_meta=source_meta(raw, mirror, curate),
    )
    with open(os.environ["OUT_PATH"], "w", encoding="utf-8") as handle:
        yaml.safe_dump(spec, handle, sort_keys=False, allow_unicode=True, width=100)
    ops = sum(
        1
        for item in spec["paths"].values()
        for method, op in item.items()
        if method in ("get", "post", "put", "patch", "delete") and op.get("operationId")
    )
    print(f"OK: wrote {os.environ['OUT_PATH']} — {len(spec['paths'])} paths — {ops} operations")


def _gemini() -> None:
    mirror, raw = _load_with_bytes(os.environ["IN_PATH"])
    curate = _curate()
    decls, warnings = build_function_declarations(mirror, curate=curate)
    blob = json.dumps(decls, indent=2, ensure_ascii=False)
    if "$ref" in blob:
        raise SystemExit("error: unresolved $ref remains in output")
    out_path = os.environ["OUT_PATH"]
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(blob + "\n")
    # A bare declarations array has no place for metadata — write a sidecar.
    meta = {**source_meta(raw, mirror, curate), "declaration_count": len(decls)}
    meta_path = out_path.rsplit(".", 1)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(meta, indent=2) + "\n")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"OK: wrote {out_path} (+ {meta_path}) — {len(decls)} declarations")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if target == "openai":
        _openai()
    elif target == "gemini":
        _gemini()
    else:
        raise SystemExit("usage: python -m verifyax_transforms {openai|gemini}")


if __name__ == "__main__":
    main()
