#!/usr/bin/env bash
#
# build-gemini-functions.sh — derive Gemini function declarations from the mirror.
# Thin wrapper over the verifyax_transforms package (gemini adapter); the logic
# lives there so it can be linted, type-checked, and unit-tested.
#
# Usage:
#   scripts/build-gemini-functions.sh              # curated (default)
#   FULL=1 OUT=gemini/verifyax-functions.full.json scripts/build-gemini-functions.sh   # full 46 ops
set -euo pipefail

IN="${IN:-openapi/verifyax.yaml}"
OUT="${OUT:-gemini/verifyax-functions.json}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IN_PATH="$REPO_ROOT/$IN" OUT_PATH="$REPO_ROOT/$OUT" PYTHONPATH="$REPO_ROOT/scripts" \
  python3 -m verifyax_transforms gemini
