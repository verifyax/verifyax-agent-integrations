# VerifyAX — OpenAI Custom GPT (Actions)

> Using **Codex CLI** instead of a Custom GPT? It's an MCP client — see
> [`codex-cli.md`](codex-cli.md) to wire up `@verifyax/mcp-server` directly (no Actions spec needed).


`verifyax-actions.yaml` is a **GPT Actions–compatible OpenAPI spec**, derived from the faithful
gateway mirror in [`../openapi/verifyax.yaml`](../openapi/verifyax.yaml). It lets a Custom GPT call
the VerifyAX Gateway public API directly.

> Generated, not hand-edited. Re-run [`../scripts/build-openai-actions.sh`](../scripts/build-openai-actions.sh)
> after every spec sync. Edits belong in the build script (or upstream at the gateway), never here.

## What the build script changes vs. the mirror

GPT Actions can't consume the raw mirror, so the build applies the minimum needed:

| Transform | Why |
|---|---|
| `servers:` → single absolute `https://console.verifyax.com/api/v1` | Actions requires one absolute server URL; the mirror's is the relative `/api`. The `/v1` prefix is folded out of the path keys so request URLs are unchanged. |
| Drop `organization_uuid` / `workspace_uuid` / `user_uuid` from request schemas | The gateway injects these from the API key. A caller (the GPT) must never send them. |
| Keep the Bearer security scheme | Already declared upstream as `BearerApiKeyAuth` (HTTP Bearer). |

`operationId`s are already unique in the mirror (all 46), so none are rewritten. Tenant names that
remain in `description` prose are intentional documentation, not request fields.

## Wire up a Custom GPT

1. **Create a GPT** — ChatGPT → *Explore GPTs* → *Create* → *Configure* → *Create new action*.
2. **Import the schema** — paste the contents of `verifyax-actions.yaml` (or host it and use *Import
   from URL*).
3. **Authentication** — *API Key* → *Auth Type: Bearer*. Paste a VerifyAX API key. Sent as
   `Authorization: Bearer <key>`, matching the `BearerApiKeyAuth` scheme.
4. **Privacy policy** — required before publishing to the GPT Store; use VerifyAX's.
5. **Test** — try "list my agents" / "preview the cost of a run" to confirm calls reach the gateway.

## Validation

Lint with Redocly (config in [`../redocly.yaml`](../redocly.yaml)):

```bash
npx @redocly/cli lint openai/verifyax-actions.yaml
```

This spec validates with **0 errors**. Two issues in the raw gateway mirror are handled here:

- **3.1-in-3.0 nullability** — the gateway declares `openapi: 3.0.x` but uses `{type: "null"}`
  branches (e.g. `SkillTag.benchmark_family`). The build transform rewrites these to valid 3.0
  (`nullable`, dropping orphan `nullable` with no scalar `type`).
- **Missing `info.license`** — we mirror a third-party contract and don't invent a license; the
  Redocly config turns that documentation rule off rather than fabricate one.

Remaining output is `no-unused-components` **warnings** (shared components the gateway defines but
some operations don't reference) — harmless for GPT Actions import.

## Scope note — all 46 operations are exposed

This spec mirrors the **entire** public API surface. The `@verifyax/mcp-server` deliberately exposes
a curated **12-tool** subset for conversational use; some raw endpoints here (one-time-login token,
audit logs, usage drill-down, job retry/delete, validation-schema) are not ideal for a no-code GPT
and may bump GPT Actions' per-action operation limits. A curated Actions variant matching the MCP
tool catalogue is a likely follow-up — see [`../PLAN.md`](../PLAN.md).
