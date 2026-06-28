# VerifyAX — Google Gemini

Two ways to use VerifyAX from Gemini, both backed by the same gateway:

- **[Gemini CLI](#gemini-cli-mcp) / any MCP client** — point it at the published
  `@verifyax/mcp-server`. No code; you get the curated VerifyAX tools directly.
- **[Gemini API / Vertex function calling](#gemini-api--vertex-function-calling)** — use the
  generated function declarations in [`verifyax-functions.json`](verifyax-functions.json) when you're
  writing your own Gemini app and calling the gateway yourself.

---

## Gemini CLI (MCP)

[Gemini CLI](https://github.com/google-gemini/gemini-cli) speaks MCP, so the shared
`@verifyax/mcp-server` (the same server used by Claude) works unchanged. Add it to your Gemini
settings (`~/.gemini/settings.json` for all projects, or `.gemini/settings.json` in a project).

### Local (stdio, via npx)

```json
{
  "mcpServers": {
    "verifyax": {
      "command": "npx",
      "args": ["-y", "@verifyax/mcp-server"],
      "env": {
        "VERIFYAX_API_KEY": "sk-ver-api-..."
      }
    }
  }
}
```

Requires Node.js ≥ 20. The server logs to stderr only; set `VERIFYAX_MCP_LOG_LEVEL`
(`debug` | `info` | `warn` | `error` | `silent`, default `info`) to adjust verbosity.

### Remote (Streamable HTTP)

If you host the HTTP transport (`verifyax-mcp-server-http`, e.g. on Cloud Run), point Gemini CLI at
it instead and pass the key as a header — the server reads `Authorization: Bearer` (or
`X-VerifyAX-API-Key`) per request:

```json
{
  "mcpServers": {
    "verifyax": {
      "httpUrl": "https://<your-deployment>/mcp",
      "headers": {
        "Authorization": "Bearer sk-ver-api-..."
      }
    }
  }
}
```

### Verify

```bash
gemini
> /mcp           # lists connected MCP servers and their tools — "verifyax" should appear
```

Then try: *"list my VerifyAX agents"* or *"preview the cost of a run"*.

---

## Gemini API / Vertex (function calling)

When you're building your own Gemini app rather than using an MCP client, use the generated
function declarations in [`verifyax-functions.json`](verifyax-functions.json). It's derived from the
gateway mirror ([`../openapi/verifyax.yaml`](../openapi/verifyax.yaml)) by
[`../scripts/build-gemini-functions.sh`](../scripts/build-gemini-functions.sh) — one declaration per
API operation, with `$ref`s inlined and parameters flattened into a single object schema.

```python
import json
from google import genai
from google.genai import types

decls = json.load(open("gemini/verifyax-functions.json"))
tools = [types.Tool(function_declarations=decls)]

client = genai.Client()
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="List my VerifyAX agents",
    config=types.GenerateContentConfig(tools=tools),
)
# When resp returns a functionCall, YOU make the matching HTTPS request to
# https://console.verifyax.com/api/v1/... with `Authorization: Bearer <api_key>`,
# then feed the result back as a functionResponse.
```

> **You own the HTTP call.** Unlike the MCP path, function calling only tells you *which* operation
> to invoke with *which* arguments — your code issues the actual authenticated request to the
> gateway and returns the result to the model.

### Caveats

- Generated from the same mirror as the OpenAI Actions spec; regenerate after every spec sync.
- Function declarations use a **subset** of OpenAPI schema. The build inlines `$ref`s and simplifies
  constructs Gemini doesn't accept (e.g. `oneOf`/`anyOf` are collapsed). Validate against your target
  (Gemini API vs. Vertex differ slightly) before relying on edge-case fields.
- All API operations are emitted. For a focused agent, pass only the declarations you need.
