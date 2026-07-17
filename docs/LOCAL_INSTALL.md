# Local Installation

## Profiles

- Lightweight deterministic: `uv tool install autocite-mcp`
- Standard local ML: `uv tool install 'autocite-mcp[slm,retrieval]'`
- GPU enhanced: `uv tool install 'autocite-mcp[slm,slm-quantized,retrieval,retrieval-reranker]'`
- Offline: download the wheel, dependencies, and model directories on an authorized machine, transfer them, then install with network disabled.

`autocite install-plan --profile PROFILE` prints exact safe defaults. AutoCite never downloads a model during document review.

## Diagnostics

```bash
autocite health
autocite models list
autocite build-rule-index --output ~/.local/share/autocite/rules.json
autocite review "See 42 USC §1983."
```

The health report discloses privacy defaults, every network-capable component, installed models, and offline readiness.

## Model lifecycle

Installed models are stored under `~/.local/share/autocite/models` by default. Set `AUTOCITE_MODEL_DIR` to point at a different model root (for example, an offline transfer location or a shared cache path).

Install only from an already downloaded local directory:

```bash
autocite models install --model-id qwen-autocite --source /path/to/model
autocite models verify --model-id qwen-autocite
autocite models remove --model-id qwen-autocite --confirm
```

Installation creates a SHA-256 manifest. Removal is irreversible and requires explicit confirmation.

## Host connection

Stdio is default. Configure a compatible host to run `autocite-mcp`. Optional HTTP requires `AUTOCITE_TRANSPORT=streamable-http` and binds to `127.0.0.1`, `localhost`, or `::1` by default. Binding any other host requires both `AUTOCITE_ALLOW_REMOTE=1` and a configured `AUTOCITE_API_TOKEN`; see [`HOSTING.md`](HOSTING.md).

No telemetry or document logging is enabled. Review is in-memory. Exports are written only to a caller-selected location. CourtListener verification is the only ordinary review operation that can send citation data externally, and only after explicit enablement.
