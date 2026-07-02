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


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _curate() -> bool:
    # Default: the curated intent-aligned surface. FULL=1 opts into all 46 ops.
    return os.environ.get("FULL", "").strip().lower() not in ("1", "true", "yes")


def _openai() -> None:
    mirror = _load(os.environ["IN_PATH"])
    spec = build_actions_spec(
        mirror,
        server_url=os.environ["SERVER_URL"],
        strip_segment=os.environ.get("STRIP_PREFIX", "v1"),
        curate=_curate(),
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
    mirror = _load(os.environ["IN_PATH"])
    decls, warnings = build_function_declarations(mirror, curate=_curate())
    blob = json.dumps(decls, indent=2, ensure_ascii=False)
    if "$ref" in blob:
        raise SystemExit("error: unresolved $ref remains in output")
    with open(os.environ["OUT_PATH"], "w", encoding="utf-8") as handle:
        handle.write(blob + "\n")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"OK: wrote {os.environ['OUT_PATH']} — {len(decls)} declarations")


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
