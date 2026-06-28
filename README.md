# VerifyAX Integrations

Use [VerifyAX](https://verifyax.com) — the agent evaluation and verification platform from
[Conscium](https://conscium.com) — from **OpenAI** and **Google Gemini**, alongside the
[Claude Code marketplace](https://github.com/verifyax/verifyax-plugins).

All of these are thin clients over the same VerifyAX Gateway public API (`/api/v1`). The
canonical contract is the OpenAPI spec; the MCP server (`@verifyax/mcp-server`) is the shared
agent-tool layer.

## Layout

```
openapi/        # Mirror of the gateway's public OpenAPI spec (synced — do not hand-edit)
openai/         # Custom GPT Actions spec (derived from the mirror) + setup guide
gemini/         # Gemini CLI MCP setup + API/Vertex function declarations (derived)
scripts/        # sync-openapi.sh and build helpers
.github/        # sync-openapi workflow
```

## OpenAPI spec (source of truth)

`openapi/verifyax.yaml` is a **faithful mirror** of the spec the gateway serves at
<https://console.verifyax.com/openapi.yaml>. Do not edit it by hand — it's overwritten by the
sync. Provider-specific transforms (GPT Actions, Gemini) read from this file.

### Syncing

Pull the latest spec locally:

```bash
scripts/sync-openapi.sh        # → openapi/verifyax.yaml
```

A scheduled GitHub Action (`.github/workflows/sync-openapi.yml`) does the same daily and commits
the mirror directly whenever the spec changes, so API updates land here automatically before
flowing into the GPT and Gemini configs.

## License

Apache-2.0.
