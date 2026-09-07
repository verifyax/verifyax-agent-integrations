from summarize_openapi_diff import summarize


def _spec(version, operations, schemas=None):
    paths = {}
    for operation_id, method, path, summary in operations:
        paths.setdefault(path, {})[method] = {
            "operationId": operation_id,
            "summary": summary,
        }
    return {
        "openapi": "3.0.3",
        "info": {"version": version},
        "paths": paths,
        "components": {"schemas": schemas or {}},
    }


def test_summary_reports_semantic_operation_changes():
    previous = _spec(
        "1.0",
        [
            ("unchanged", "get", "/same", "same"),
            ("changed", "post", "/changed", "before"),
            ("removed", "delete", "/removed", "gone"),
        ],
        {"Changed": {"type": "string"}, "Removed": {"type": "boolean"}},
    )
    current = _spec(
        "1.1",
        [
            ("unchanged", "get", "/same", "same"),
            ("changed", "post", "/changed", "after"),
            ("added", "get", "/added", "new"),
        ],
        {"Changed": {"type": "integer"}, "Added": {"type": "object"}},
    )

    summary = summarize(previous, current)

    assert "API version: `1.0` → `1.1`" in summary
    assert "Added: 1; removed: 1; changed: 1" in summary
    assert "`GET /added` (`added`)" in summary
    assert "`DELETE /removed` (`removed`)" in summary
    assert "`POST /changed` (`changed`)" in summary
    assert "Component schemas: +1; -1; changed: 1" in summary
    assert "`Changed`" in summary


def test_summary_ignores_formatting_only_changes():
    previous = _spec("1.0", [("same", "get", "/same", "same")])
    current = _spec("1.0", [("same", "get", "/same", "same")])

    assert "Added: 0; removed: 0; changed: 0" in summarize(previous, current)
