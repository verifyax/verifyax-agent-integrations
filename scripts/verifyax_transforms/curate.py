"""The curated, intent-aligned operation set for the no-code surfaces.

A GPT Actions / Gemini function-calling surface works best when it's small and
covers a coherent workflow — not a flat map of all 46 endpoints (ARCH-1). This
is the default set: enough to drive register → discover tags → generate → poll →
preview → simulate → poll → evaluate → fetch → track spend, and no more.

Deliberately excluded (SEC-3 / low value on a no-code surface): session-minting
(`createOneTimeLoginToken`), audit logs, per-call usage drill-down, job
retry/delete, scenario copy/artifact editing, and the JSON-validation schema
endpoints. The full 46-operation surface is still available as an explicit
opt-in (build with FULL=1).
"""

from __future__ import annotations

CURATED_OPERATION_IDS = frozenset(
    {
        # Tags
        "listSkillTags",
        # Agents — register (with connectivity probes), list, delete
        "testAgentCard",
        "testRestAgent",
        "createAgent",
        "listAgents",
        "deleteAgent",
        # Scenarios — generate, list, delete, poll the creation job
        "generateScenario",
        "listScenarios",
        "deleteScenario",
        "getScenarioJob",
        # Jobs — generic async poll
        "getJob",
        # Engine — cost preview, run, evaluate
        "previewWorkspaceCredits",
        "simulateScenario",
        "triggerEvaluation",
        # Simulations — list, poll a run, fetch the evaluation
        "listSimulations",
        "getSimulation",
        "getSimulationEvaluation",
        # Spend
        "listUsageEvents",
    }
)


def unknown_curated_ids(all_operation_ids: set[str]) -> set[str]:
    """Curated ids not present in the spec — a typo or an upstream rename. The
    build treats a non-empty result as fatal so curation can't silently no-op."""
    return set(CURATED_OPERATION_IDS) - set(all_operation_ids)
