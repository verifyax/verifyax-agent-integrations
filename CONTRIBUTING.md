# Contributing

Thanks for your interest. This repo is **maintained internally by Conscium** (Apache-2.0). The API
contract it derives from is owned upstream, so the maintainers handle changes and **external pull
requests are not accepted** — please [open an issue](https://github.com/verifyax/verifyax-agent-integrations/issues)
instead. Report security issues privately per [`SECURITY.md`](SECURITY.md).

## How it fits together

- `openapi/verifyax.yaml` — a faithful mirror of the gateway's published spec (**do not hand-edit**; the sync overwrites it).
- `scripts/verifyax_transforms/` — the Python package that derives the provider artifacts (shared `normalize` core + `openai` / `gemini` adapters + `curate` allowlist). The `.sh` files are thin wrappers.
- `openai/`, `gemini/` — the **generated** artifacts (curated by default; provenance stamped) and setup guides.

## For maintainers

```bash
pip install -r requirements.txt
npm ci
python -m pytest tests/            # unit + golden-file locks
scripts/sync-openapi.sh            # refresh the mirror from the gateway
scripts/build-openai-actions.sh    # regenerate the GPT Actions spec  (FULL=1 for all operations)
scripts/build-gemini-functions.sh  # regenerate the Gemini declarations
npm test                           # pinned Redocly + Gemini SDK acceptance checks
```

- **Never hand-edit the generated artifacts** — change the transform (and its tests) and regenerate. CI enforces this with golden-file tests.
- The **curated operation set** lives in [`scripts/verifyax_transforms/curate.py`](scripts/verifyax_transforms/curate.py).
- The daily sync validates, opens or updates a bot PR with a semantic diff, and never writes
  externally sourced changes directly to `main`; a failure opens a tracking issue.
