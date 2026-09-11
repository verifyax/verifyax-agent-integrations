import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"


def test_actions_are_pinned_to_commit_shas():
    uses = []
    for workflow in WORKFLOWS.glob("*.yml"):
        uses.extend(re.findall(r"^\s*-\s+uses:\s+(\S+)", workflow.read_text(), re.MULTILINE))

    assert uses
    assert all(re.search(r"@[0-9a-f]{40}$", action) for action in uses), uses


def test_scheduled_sync_cannot_push_to_main():
    workflow = (WORKFLOWS / "sync-openapi.yml").read_text(encoding="utf-8")

    assert "pull-requests: write" in workflow
    assert "BRANCH: automation/openapi-sync" in workflow
    assert 'git push --force-with-lease origin "HEAD:refs/heads/$BRANCH"' in workflow
    assert "git push origin HEAD:main" not in workflow


def test_empty_gh_lists_are_not_treated_as_ids():
    workflow = (WORKFLOWS / "sync-openapi.yml").read_text(encoding="utf-8")

    assert "'.[0].number'" not in workflow
    assert ".[0].number // empty" in workflow
    assert 'gh workflow run CI --ref "$BRANCH"' in workflow


def test_ci_accepts_workflow_dispatch_for_bot_branch():
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in ci
