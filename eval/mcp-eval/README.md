# mcp-eval Evaluation

Language-agnostic MCP scenario testing for gemara-mcp.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
# Generate scenarios from corpus and execute against live server
python run_mcp_eval.py --corpus ../../corpus --output ../../results/mcp-eval.json

# Or from repo root
make eval-mcp-eval
```

## Server Connection

Scenarios are executed against a live gemara-mcp server via MCP stdio transport.
The harness spawns a Docker container (`docker run --rm -i <image> serve --mode artifact`)
and communicates over stdin/stdout. Configure via environment variables:

- `GEMARA_MCP_IMAGE` — Docker image (default: `ghcr.io/gemaraproj/gemara-mcp:v0.1.0`)
- `CONTAINER_RUNTIME` — Container runtime (default: `docker`)

## What it tests

- Replays corpus scenarios as structured MCP interactions against the live server
- **Tool scenarios** (tc-001 to tc-005): Calls `validate_gemara_artifact` and asserts on `$.valid`
- **Prompt scenarios** (tc-010+): Invokes `threat_assessment` / `control_catalog` prompts and checks for expected keywords
- Reports per-scenario pass/fail with step-level assertion results
