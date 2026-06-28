# PLAN — VerifyAX integrations for OpenAI & Gemini

Handoff plan for extending VerifyAX distribution beyond Claude Code to the OpenAI and Gemini
ecosystems. Written to seed a new, integrations-scoped Claude Code session.

## Status (2026-06-28)

Delivered in `v0.1.0`: repo bootstrap, OpenAPI sync + daily auto-rebuild workflow, OpenAI GPT
Actions spec + Codex CLI docs, Gemini CLI setup + function declarations. The MCP server is
published on npm and **listed in the official MCP registry** as `io.github.verifyax/mcp-server`
(work item 3 — done; source repo is `verifyax/verifyax-mcp`).

Remaining / optional: smithery.ai listing (web submission); mcp.so (auto-crawls the registry);
upstream gateway spec fixes (`info.license`, a 3.1-style `nullable` — currently normalized in the
build transform, better fixed at source); push-based spec sync via `repository_dispatch`.

## Context / what already exists

- **`verifyax/verifyax-plugins`** — published Claude Code plugin marketplace. Two plugins:
  - `verifyax-api` (skill, v0.2.0) — drives the REST API; SKILL.md is the curated, LLM-facing
    API reference.
  - `verifyax-mcp` (v0.1.0) — installs `@verifyax/mcp-server` (published on npm).
  - GitHub Release `verifyax-api-v0.2.0` published; `.skill` bundle built via
    `scripts/build-skill.sh`.
- **`@verifyax/mcp-server`** (npm) — the shared MCP server; works in any MCP client.
- **Gateway public OpenAPI spec** — static file at <https://console.verifyax.com/openapi.yaml>
  (served from `frontend/user-webapp/public/openapi.yaml`), documents the public API under
  `/api/v1`. No auth to fetch.

## Key decision: separate repo

Keep `verifyax-plugins` Claude-only (its identity = a Claude marketplace; already published &
crawled). Put cross-provider work in a **new `verifyax/verifyax-agent-integrations` repo** (this
scaffold). The OpenAPI spec's true source of truth is the gateway; this repo mirrors it.

## Guiding insight

MCP is the portable layer — OpenAI (Agents SDK, Codex CLI, Apps SDK) and Gemini (Gemini CLI,
Gemini API / Vertex) all speak it. So `@verifyax/mcp-server` already works across ecosystems; most
"new" work is **listing + documenting**, plus producing **one OpenAPI-derived artifact** for the
no-code surfaces (GPT Actions, Gemini function calling).

## Work items (suggested order)

1. **Bootstrap the repo** — create `verifyax/verifyax-agent-integrations`, push this scaffold
   (README, scripts/sync-openapi.sh, .github/workflows/sync-openapi.yml, openapi/, openai/,
   gemini/). Apache-2.0 LICENSE.
2. **OpenAPI sync (pull)** — verify `scripts/sync-openapi.sh` fetches & validates the gateway
   spec; run it once to commit the first `openapi/verifyax.yaml`; confirm the scheduled workflow
   opens a drift PR. (Push-based `repository_dispatch` from the API repo is a later add-on.)
3. **MCP registries (highest leverage, helps all ecosystems)** — submit `@verifyax/mcp-server`
   to the official MCP registry + smithery.ai + mcp.so. Needs the MCP server's source repo +
   a `server.json`.
4. **OpenAI — Custom GPT + GPT Store** — generate a GPT Actions-compatible spec from the mirror
   (single `servers` entry = `https://console.verifyax.com/api/v1`, unique `operationId`s, Bearer
   security scheme, drop gateway-injected tenant params), wire a Custom GPT, publish to GPT Store.
5. **OpenAI — Codex CLI docs** — short "add VerifyAX as an MCP server" guide (reuses npm pkg).
6. **Gemini — Gemini CLI** — extension / `settings.json` MCP setup docs (reuses npm pkg).
7. **Gemini — API/Vertex** — function declarations derived from the mirror (same transform as
   GPT Actions).

## Normalize notes (for the GPT/Gemini transform, NOT the sync)

The sync keeps `openapi/verifyax.yaml` a faithful 1:1 mirror. The OpenAI/Gemini build steps
transform a COPY:
- `servers:` → single entry `https://console.verifyax.com/api/v1`
- every operation needs a unique `operationId`
- declare Bearer `securityScheme`; remove any tenant params the gateway injects
  (`organization_uuid`/`workspace_uuid`/`user_uuid`) and internal engine/model/DAG fields
- validate/bundle with `@redocly/cli` or `spectral`

## Open questions / confirmations

- ~~MCP server **source repo** URL (needed for registry `server.json`).~~ Resolved:
  `https://github.com/verifyax/verifyax-mcp` (where `server.json` now lives).
- Whether to also do push-based spec sync (API repo fires `repository_dispatch`).
- GPT Store / Apps SDK / Gemini extension publishing policies move fast — verify current
  process before building (knowledge cutoff caveat).

## Access note

A Claude Code session must be **scoped to `verifyax/verifyax-agent-integrations`** (and ideally
`verifyax-plugins` too) to push this. Create the empty repo first, then open the scoped session.

## Scaffold delivered with this plan

```
verifyax-agent-integrations/
├── README.md
├── PLAN.md                         (this file)
├── scripts/sync-openapi.sh         (pull + validate the gateway spec → openapi/verifyax.yaml)
├── .github/workflows/sync-openapi.yml  (daily + manual; opens a drift PR)
├── openapi/                        (mirror lands here)
├── openai/                         (GPT Actions config — TODO)
└── gemini/                         (Gemini CLI docs — TODO)
```
