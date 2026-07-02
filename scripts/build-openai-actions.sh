#!/usr/bin/env bash
#
# build-openai-actions.sh — derive the GPT Actions spec from the gateway mirror.
# Thin wrapper over the verifyax_transforms package (openai adapter); the logic
# lives there so it can be linted, type-checked, and unit-tested.
#
# Usage:
#   scripts/build-openai-actions.sh
#   IN=openapi/verifyax.yaml OUT=openai/verifyax-actions.yaml scripts/build-openai-actions.sh
set -euo pipefail

IN="${IN:-openapi/verifyax.yaml}"
OUT="${OUT:-openai/verifyax-actions.yaml}"
SERVER_URL="${SERVER_URL:-https://console.verifyax.com/api/v1}"
# Slash-less segment (Git Bash/MSYS would rewrite a leading "/" into a Windows
# path); the package rebuilds the leading slash.
STRIP_PREFIX="${STRIP_PREFIX:-v1}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IN_PATH="$REPO_ROOT/$IN" OUT_PATH="$REPO_ROOT/$OUT" SERVER_URL="$SERVER_URL" \
  STRIP_PREFIX="$STRIP_PREFIX" PYTHONPATH="$REPO_ROOT/scripts" \
  python3 -m verifyax_transforms openai
