# DeepEval Evaluation

MCP tool selection accuracy and N-run determinism measurement using DeepEval.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
# From this directory
python -m pytest test_tool_selection.py test_determinism.py -v

# Or from repo root
make eval-deepeval
```

## Server Connection

Tests connect to a live gemara-mcp server via MCP stdio transport using a
session-scoped pytest fixture (`mcp_client` in `conftest.py`). The fixture
spawns a Docker container and keeps the connection open for the test session.

Configure via environment variables:

- `GEMARA_MCP_IMAGE` — Docker image (default: `ghcr.io/gemaraproj/gemara-mcp:v0.1.0`)
- `CONTAINER_RUNTIME` — Container runtime (default: `docker`)

## Dependencies

- **Docker**: Required for MCP server connection
- **Ollama** with `qwen2.5:7b`: Required for GEval LLM-as-judge scoring

The MCP calls work independently of Ollama. If Ollama is unavailable, tool
calls succeed but GEval scoring (threat/control consistency tests) will fail.

## Test files

- `test_tool_selection.py` — Criterion 1: Are the right tools called for the right task?
- `test_determinism.py` — Criterion 3: Are results deterministic across runs?
- `conftest.py` — Shared fixtures: corpus loading and MCP client session
