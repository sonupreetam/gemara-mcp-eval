# MCP Evals Evaluation

LLM-scored quality evaluation of gemara-mcp tool responses using MCP Evals.

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

## What it tests

- Tool response quality (accuracy, completeness, relevance, clarity, reasoning)
- Each metric scored 1-5, threshold at 3.5
- Tests `validate_gemara_artifact` tool and `gemara://` resources
