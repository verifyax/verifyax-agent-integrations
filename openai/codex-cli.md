# VerifyAX in OpenAI Codex CLI (MCP)

[Codex CLI](https://github.com/openai/codex) is an MCP client, so the shared
`@verifyax/mcp-server` — the same server used by Claude and Gemini CLI — works unchanged. No code;
you get the curated VerifyAX tools natively.

## Setup

Add the server to `~/.codex/config.toml`:

```toml
[mcp_servers.verifyax]
command = "npx"
args = ["-y", "@verifyax/mcp-server"]
env = { VERIFYAX_API_KEY = "sk-ver-api-..." }
```

Requires Node.js ≥ 20. The server logs to stderr only; set `VERIFYAX_MCP_LOG_LEVEL`
(`debug` | `info` | `warn` | `error` | `silent`, default `info`) in `env` to adjust verbosity.

Equivalently, register it from the command line:

```bash
codex mcp add verifyax --env VERIFYAX_API_KEY=sk-ver-api-... -- npx -y @verifyax/mcp-server
```

## Verify

```bash
codex mcp list        # "verifyax" should be listed
```

Then, in a Codex session, ask something like *"list my VerifyAX agents"* or *"preview the cost of a
run"* to confirm the tools are reachable.

## Remote (Streamable HTTP)

To target a hosted HTTP deployment (`verifyax-mcp-server-http`) instead of the local stdio process,
use a streamable-HTTP server entry and pass the key as a header — the server reads
`Authorization: Bearer` (or `X-VerifyAX-API-Key`) per request:

```toml
[mcp_servers.verifyax]
url = "https://<your-deployment>/mcp"
http_headers = { Authorization = "Bearer sk-ver-api-..." }
```

> HTTP-transport support and the exact key names (`url` / `http_headers`) vary across Codex CLI
> versions — check `codex mcp --help` for your build. The stdio (`npx`) setup above is the most
> broadly supported.
