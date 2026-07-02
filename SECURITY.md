# Security Policy

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue or PR.

- Preferred: open a [GitHub private security advisory](https://github.com/verifyax/verifyax-agent-integrations/security/advisories/new).
- Or email **security@conscium.com** (subject: `verifyax-agent-integrations security`).

Include enough detail to reproduce (affected file/config, steps, impact). We'll acknowledge your report and keep you posted on remediation.

## Scope

This repo publishes **integration configs and docs**, not a runtime service:

- The OpenAPI mirror + derived GPT Actions / Gemini function declarations, generated from the gateway spec.
- Setup guides for pointing OpenAI / Gemini / MCP clients at VerifyAX.

The setup guides reference a user's **VerifyAX API key** (`sk-ver-api-...`), which is sent directly to the gateway by the user's own client — it never transits this repository or any service it operates.

## Handling API keys

- Never paste a key into a chat, issue, log, or committed config file. The guides recommend sourcing the key from the environment / a secret store.
- Rotate a key immediately if it may have been exposed (VerifyAX console → **Settings → API Keys**).

## Automation

The daily sync commits directly to `main` only after a validation gate (diff-magnitude guard + transform tests + Redocly lint) and opens a tracking issue on failure. See [`.github/workflows/sync-openapi.yml`](.github/workflows/sync-openapi.yml).
