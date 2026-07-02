"""Tests for the transform module — the bug-prone paths plus golden-file locks.

Golden files are the committed derived artifacts (openai/verifyax-actions.yaml,
gemini/verifyax-functions.json). Rebuilding from the mirror must reproduce them
exactly; a diff means the transform changed and the artifacts need regenerating.
"""

import json
import pathlib

import yaml

from verifyax_transforms import build_actions_spec, build_function_declarations
from verifyax_transforms.curate import CURATED_OPERATION_IDS
from verifyax_transforms.gemini import _simplify

_ALL_OPERATIONS = 46
_SENSITIVE = {"createOneTimeLoginToken", "listAuditLogs", "getUsageEvent", "retryJob"}

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIRROR = yaml.safe_load((ROOT / "openapi" / "verifyax.yaml").read_text(encoding="utf-8"))
SERVER_URL = "https://console.verifyax.com/api/v1"


# --- Gemini simplify: the constructs that used to break (BUILD-6, BUILD-3) ---


def test_all_of_merges_properties_not_dropped_to_string():
    """Regression for BUILD-6: an allOf of object schemas must keep its merged
    properties as an OBJECT, not fall through to STRING with fields dropped."""
    warnings = []
    schema = {
        "allOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
            {"type": "object", "properties": {"b": {"type": "integer"}}},
        ]
    }
    out = _simplify(schema, warnings, "t")
    assert out["type"] == "OBJECT"
    assert set(out["properties"]) == {"a", "b"}
    assert out["properties"]["a"]["type"] == "STRING"
    assert out["properties"]["b"]["type"] == "INTEGER"
    assert out.get("required") == ["a"]


def test_nested_union_inside_object_property_keeps_object():
    """A property whose value is a oneOf must not collapse the parent to STRING."""
    warnings = []
    schema = {
        "type": "object",
        "properties": {"f": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}},
    }
    out = _simplify(schema, warnings, "t")
    assert out["type"] == "OBJECT"
    assert out["properties"]["f"]["type"] == "STRING"  # first non-null branch


def test_union_collapse_is_warned(recwarn=None):
    """BUILD-3: collapsing a multi-branch union is lossy and must be logged."""
    warnings = []
    _simplify({"oneOf": [{"type": "string"}, {"type": "integer"}]}, warnings, "field")
    assert any("collapsed oneOf" in w for w in warnings)


def test_null_branch_becomes_nullable():
    warnings = []
    out = _simplify({"oneOf": [{"type": "string"}, {"type": "null"}]}, warnings, "t")
    assert out["type"] == "STRING"
    assert out["nullable"] is True


def test_type_array_with_null_becomes_nullable():
    warnings = []
    out = _simplify({"type": ["integer", "null"]}, warnings, "t")
    assert out["type"] == "INTEGER"
    assert out["nullable"] is True


# --- OpenAI adapter: tenant scope (BUILD-7) + server rewrite ---


def test_openai_strips_tenant_from_requests_only():
    mirror = {
        "openapi": "3.0.3",
        "components": {
            "securitySchemes": {"BearerApiKeyAuth": {"type": "http", "scheme": "bearer"}},
            "schemas": {
                "AgentResponse": {
                    "type": "object",
                    "properties": {"uuid": {"type": "string"}, "user_uuid": {"type": "string"}},
                }
            },
        },
        "paths": {
            "/v1/agents": {
                "post": {
                    "operationId": "createAgent",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "organization_uuid": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/AgentResponse"}}
                            }
                        }
                    },
                }
            }
        },
    }
    spec = build_actions_spec(mirror, SERVER_URL, "v1", curate=False)
    # Request body: tenant field stripped.
    req_props = spec["paths"]["/agents"]["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["properties"]
    assert "organization_uuid" not in req_props
    assert "name" in req_props
    # Response/component schema: tenant field KEPT (BUILD-7).
    assert "user_uuid" in spec["components"]["schemas"]["AgentResponse"]["properties"]


def test_openai_sets_absolute_server_and_strips_prefix():
    mirror = {
        "openapi": "3.0.3",
        "components": {"securitySchemes": {"B": {"type": "http"}}},
        "paths": {"/v1/agents": {"get": {"operationId": "listAgents"}}},
    }
    spec = build_actions_spec(mirror, SERVER_URL, "v1", curate=False)
    assert spec["servers"] == [{"url": SERVER_URL, "description": "VerifyAX Gateway public API"}]
    assert list(spec["paths"]) == ["/agents"]


# --- Golden-file locks (CI-2): rebuild == committed artifacts ---


def test_openai_matches_committed_artifact():
    built = build_actions_spec(MIRROR, SERVER_URL, "v1")
    committed = yaml.safe_load((ROOT / "openai" / "verifyax-actions.yaml").read_text(encoding="utf-8"))
    assert built == committed, "openai/verifyax-actions.yaml is stale — re-run build-openai-actions.sh"


def test_gemini_matches_committed_artifact():
    built, _ = build_function_declarations(MIRROR)
    committed = json.loads((ROOT / "gemini" / "verifyax-functions.json").read_text(encoding="utf-8"))
    assert built == committed, "gemini/verifyax-functions.json is stale — re-run build-gemini-functions.sh"


# --- Curation (ARCH-1, SEC-3) ---


def test_default_is_curated_and_drops_sensitive_ops():
    decls, _ = build_function_declarations(MIRROR)  # curate=True default
    names = {d["name"] for d in decls}
    assert names == set(CURATED_OPERATION_IDS)
    assert not (names & _SENSITIVE)  # no sensitive/low-value ops on the default surface

    spec = build_actions_spec(MIRROR, SERVER_URL, "v1")
    op_ids = {
        op["operationId"]
        for item in spec["paths"].values()
        for method, op in item.items()
        if method in ("get", "post", "put", "patch", "delete")
    }
    assert op_ids == set(CURATED_OPERATION_IDS)


def test_full_surface_is_opt_in():
    decls, _ = build_function_declarations(MIRROR, curate=False)
    names = {d["name"] for d in decls}
    assert len(decls) == _ALL_OPERATIONS
    assert _SENSITIVE <= names  # the full surface still includes them

    spec = build_actions_spec(MIRROR, SERVER_URL, "v1", curate=False)
    op_count = sum(
        1
        for item in spec["paths"].values()
        for method in item
        if method in ("get", "post", "put", "patch", "delete")
    )
    assert op_count == _ALL_OPERATIONS


def test_every_curated_id_exists_in_the_spec():
    """Guard against a typo/rename silently dropping a curated operation."""
    from verifyax_transforms.curate import unknown_curated_ids

    all_ids = {
        op["operationId"]
        for item in MIRROR["paths"].values()
        for method, op in item.items()
        if method in ("get", "post", "put", "patch", "delete") and op.get("operationId")
    }
    assert unknown_curated_ids(all_ids) == set()
