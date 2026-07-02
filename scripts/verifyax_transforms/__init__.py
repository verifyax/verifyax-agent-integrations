"""Transforms that derive provider-specific artifacts from the gateway OpenAPI mirror.

A shared core (`normalize`) plus two provider adapters (`openai`, `gemini`). The
mirror is never mutated — every function operates on a caller-owned copy.
"""

from .gemini import build_function_declarations
from .openai import build_actions_spec

__all__ = ["build_actions_spec", "build_function_declarations"]
