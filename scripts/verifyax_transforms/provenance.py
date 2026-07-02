"""Provenance for the derived artifacts — which mirror content produced them.

Without this, you can't tell from an artifact alone whether it matches the
current contract (ARCH-3). The OpenAI spec carries it inline under
`info.x-verifyax-source`; the Gemini array (which must stay a bare list of
declarations) carries it in a sidecar `*.meta.json`.
"""

from __future__ import annotations

import hashlib
from typing import Any

SOURCE_URL = "https://console.verifyax.com/openapi.yaml"


def source_meta(mirror_bytes: bytes, mirror: dict[str, Any], curated: bool) -> dict[str, Any]:
    """Build the provenance block from the raw mirror bytes + parsed mirror."""
    return {
        "source": SOURCE_URL,
        "spec_version": str(mirror.get("info", {}).get("version", "unknown")),
        "spec_sha256": hashlib.sha256(mirror_bytes).hexdigest(),
        "surface": "curated" if curated else "full",
    }
