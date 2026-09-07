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
