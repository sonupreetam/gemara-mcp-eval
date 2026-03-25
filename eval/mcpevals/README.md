# MCP Evals Evaluation

LLM-scored quality evaluation of gemara-mcp tool and resource responses.

## Setup

```bash
npm install
```

## Run

```bash
# From this directory
npx ts-node eval-suite.ts

# Or from repo root
make eval-mcpevals
```

## Server Connection

The eval suite connects to gemara-mcp via MCP stdio transport using
`@modelcontextprotocol/sdk`. It spawns a Docker container based on the
server config in `evals.config.ts` and communicates over stdin/stdout.

Configure via environment variables:

- `GEMARA_MCP_IMAGE` — Docker image (default: `ghcr.io/gemaraproj/gemara-mcp:v0.1.0`)
- `CONTAINER_RUNTIME` — Container runtime (default: `docker`)

## Dependencies

- **Docker**: Required for MCP server connection
- **Ollama** with `qwen2.5:7b`: Required for quality scoring

The MCP tool calls work independently of Ollama. If Ollama is unavailable,
real tool/resource outputs are retrieved but LLM scoring fails.

## What it tests

- Tool response quality (accuracy, completeness, relevance, clarity, reasoning)
- Each metric scored 1-5 by Ollama, threshold at 3.5
- Tests `validate_gemara_artifact` tool and `gemara://` resources against the live server
