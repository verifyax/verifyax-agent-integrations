# VerifyAX Integrations

Use [VerifyAX](https://verifyax.com) — the agent evaluation and verification platform from
[Conscium](https://conscium.com) — from **OpenAI** and **Google Gemini**, alongside the
[Claude Code marketplace](https://github.com/verifyax/verifyax-plugins).

Everything here is a thin client over the same VerifyAX Gateway public API (`/api/v1`). The
canonical contract is the [OpenAPI spec](#openapi-spec-source-of-truth); the MCP server
([`@verifyax/mcp-server`](https://www.npmjs.com/package/@verifyax/mcp-server)) is the shared
agent-tool layer.

## The portable layer: MCP

MCP is the common denominator — OpenAI (Codex CLI, Agents SDK) and Google (Gemini CLI) all speak
it, so the **same** `@verifyax/mcp-server` works everywhere. It's published on
[npm](https://www.npmjs.com/package/@verifyax/mcp-server) and listed in the
[official MCP registry](https://registry.modelcontextprotocol.io/v0/servers?search=verifyax) as
`io.github.verifyax/mcp-server`. For the no-code surfaces that can't run MCP (Custom GPTs, Gemini
function calling), we generate OpenAPI-derived artifacts from the mirror instead.

## Pick your platform

| Platform | How | Guide |
|---|---|---|
| **OpenAI Codex CLI** | MCP server (`@verifyax/mcp-server`) | [openai/codex-cli.md](openai/codex-cli.md) |
| **OpenAI Custom GPT** | GPT Actions (OpenAPI) | [openai/README.md](openai/README.md) |
| **Gemini CLI** | MCP server (`@verifyax/mcp-server`) | [gemini/README.md](gemini/README.md#gemini-cli-mcp) |
| **Gemini API / Vertex** | Function declarations | [gemini/README.md](gemini/README.md#gemini-api--vertex-function-calling) |
| **Claude Code** | Plugin marketplace | [verifyax/verifyax-plugins](https://github.com/verifyax/verifyax-plugins) |

## OpenAPI spec (source of truth)

`openapi/verifyax.yaml` is a **faithful mirror** of the spec the gateway serves at
<https://console.verifyax.com/openapi.yaml>. Do not edit it by hand — it's overwritten by the
sync. The provider artifacts are *derived* from it:

- `openai/verifyax-actions.yaml` ← `scripts/build-openai-actions.sh`
- `gemini/verifyax-functions.json` ← `scripts/build-gemini-functions.sh`

### Keeping everything in sync

```bash
scripts/sync-openapi.sh            # pull the latest spec → openapi/verifyax.yaml
scripts/build-openai-actions.sh    # regenerate the GPT Actions spec
scripts/build-gemini-functions.sh  # regenerate the Gemini function declarations
```

A scheduled GitHub Action (`.github/workflows/sync-openapi.yml`) runs all three daily and commits
the mirror **plus** the regenerated artifacts whenever the gateway spec changes — so the derived
files never lag the contract. Lint the OpenAPI specs with `npx @redocly/cli lint` (config in
[`redocly.yaml`](redocly.yaml)).

## Layout

```
openapi/   # Mirror of the gateway's public OpenAPI spec (synced — do not hand-edit)
openai/    # GPT Actions spec + Custom GPT guide; Codex CLI (MCP) setup
gemini/    # Gemini CLI (MCP) setup + API/Vertex function declarations
scripts/   # sync + build helpers (re-run after each sync)
.github/   # daily sync-and-rebuild workflow
```

## License

Apache-2.0.
