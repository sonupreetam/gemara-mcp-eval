# gemara-mcp-eval

Determinism evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — measuring NFR6 compliance (90% deterministic outcomes for artifact generation).

## Overview

This repo evaluates all gemara-mcp tools, prompts, and resources using six evaluation frameworks:

| Framework | Focus | Language | Requires Ollama | Connects to MCP |
|---|---|---|---|---|
| **detLLM** | Raw LLM determinism (Tier 0/1/2) | Python | Yes | No (by design) |
| **DeepEval** | MCP tool selection + output quality | Python | Yes (for scoring) | Yes |
| **MCP Evals** | LLM-scored tool response quality | Node.js | Yes (for scoring) | Yes |
| **mcp-eval** | Language-agnostic MCP scenario testing | Python | No | Yes |
| **DFAH** | Trajectory determinism + faithfulness (adapted from IBM) | Python | No (tool benchmarks) | Yes |
| **Promptfoo** | Assertion-based regression testing | Node.js | Yes | No |

All frameworks share a single test corpus (`corpus/`) to ensure consistent measurement.

## gemara-mcp Surface Under Test

- **Tool**: `validate_gemara_artifact` — validate YAML against Gemara CUE schemas
- **Resources**: `gemara://lexicon`, `gemara://schema/definitions`, `gemara://schema/definitions{?version}`
- **Prompts** (artifact mode): `threat_assessment`, `control_catalog`

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker (for running gemara-mcp server via stdio)
- [CUE CLI](https://cuelang.org/docs/install/) (for corpus validation)
- [Ollama](https://ollama.ai/) with `qwen2.5:7b` model (for LLM-based evals only)

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval

# Validate the test corpus
make corpus-validate

# Run all evaluations (each spawns its own gemara-mcp server instance)
make eval-all

# Generate NFR6 report
make report
```

Eval tools that connect to gemara-mcp (DFAH, mcp-eval, DeepEval, MCP Evals) manage their own server lifecycle — they spawn a `docker run --rm -i` process via MCP stdio transport. No separate `docker compose up` is needed.

## Running Individual Evaluations

```bash
make eval-detllm       # Raw LLM determinism (requires Ollama)
make eval-deepeval     # MCP tool selection + determinism (requires Ollama for scoring)
make eval-mcpevals     # LLM-scored quality (requires Ollama for scoring)
make eval-mcp-eval     # Scenario replay (self-contained, Docker only)
make eval-dfah         # Trajectory determinism (self-contained for tool benchmarks)
make eval-promptfoo    # Regression assertions (requires Ollama)
```

For offline testing without a live server, DFAH supports a `--simulate` flag:

```bash
cd eval/dfah && python3 harness.py --simulate
```

## Repo Structure

```
gemara-mcp-eval/
├── reference/          # Pinned submodules (gemara schemas, gemara-mcp server)
├── corpus/             # Shared test corpus (scenarios, inputs, golden outputs, prompts)
├── eval/               # Per-tool evaluation harnesses
│   ├── shared/         # Shared MCP client library (Python)
│   ├── detllm/
│   ├── deepeval/
│   ├── mcpevals/
│   ├── mcp-eval/
│   ├── dfah/
│   └── promptfoo/
├── analysis/           # Cross-tool comparison and NFR6 reporting
└── ci/                 # CI/CD (Dockerfile, GitHub Actions)
```

## Environment Variables

| Variable | Default | Used by |
|---|---|---|
| `GEMARA_MCP_IMAGE` | `ghcr.io/gemaraproj/gemara-mcp:v0.1.0` | All MCP-connected evals |
| `GEMARA_MCP_MODE` | `artifact` | All MCP-connected evals |
| `CONTAINER_RUNTIME` | `docker` | All MCP-connected evals, Makefile |
| `OLLAMA_MODEL` | `qwen2.5:7b` | detLLM, MCP Evals, Promptfoo |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | detLLM, MCP Evals |

## NFR6 Target

> The combination of the Context Tool and CUE Validation must ensure at least 90% deterministic outcomes for artifact generation.

The `make report` target aggregates results from all six tools and produces a pass/fail verdict against the 90% threshold.

## Related

- [gemara](https://github.com/gemaraproj/gemara) — GRC Engineering Model (CUE schemas)
- [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — MCP Server
- [Issue #14](https://github.com/gemaraproj/gemara-mcp/issues/14) — Explore solutions for MCP Evaluation
- [DFAH paper](https://arxiv.org/abs/2601.15322) — Determinism-Faithfulness Assurance Harness

## License

Apache-2.0
