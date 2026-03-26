# gemara-mcp-eval

Determinism evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — measuring NFR6 compliance (90% deterministic outcomes for artifact generation).

## Overview

This repo evaluates all gemara-mcp tools, prompts, and resources using six evaluation frameworks:

| Framework | Focus | Language | Needs LLM | Connects to MCP |
|---|---|---|---|---|
| **mcp-eval** | Language-agnostic MCP scenario testing | Python | **No** | Yes |
| **DFAH** | Trajectory determinism + faithfulness (adapted from IBM) | Python | **No** | Yes |
| **detLLM** | Raw LLM determinism (Tier 0/1/2) | Python | Yes (system under test) | No (by design) |
| **DeepEval** | MCP tool selection + output quality | Python | Yes (LLM-as-judge) | Yes |
| **MCP Evals** | LLM-scored tool response quality | Node.js | Yes (LLM-as-judge) | Yes |
| **Promptfoo** | Assertion-based regression testing | Node.js | Yes (system under test) | No |

All frameworks share a single test corpus (`corpus/`) to ensure consistent measurement.

> **Note**: mcp-eval and DFAH do not require any LLM — they connect directly to gemara-mcp via MCP stdio and compute determinism with pure math. You can get partial NFR6 results from these two alone.

## gemara-mcp Surface Under Test

- **Tool**: `validate_gemara_artifact` — validate YAML against Gemara CUE schemas
- **Resources**: `gemara://lexicon`, `gemara://schema/definitions`, `gemara://schema/definitions{?version}`
- **Prompts** (artifact mode): `threat_assessment`, `control_catalog`

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker or Podman (for running gemara-mcp server via stdio)
- [CUE CLI](https://cuelang.org/docs/install/) (for corpus validation)
- **At least one** LLM backend (for harnesses that need an LLM):
  - [Ollama](https://ollama.ai/) with a model like `qwen2.5:7b` (local, default)
  - Google Cloud Vertex AI (set `VERTEX_PROJECT` + `VERTEX_LOCATION`)
  - OpenAI API (set `OPENAI_API_KEY`)

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval
cp .env.example .env   # Edit with your provider settings

# Validate the test corpus
make corpus-validate

# Run all evaluations (each spawns its own gemara-mcp server instance)
make eval-all

# Generate NFR6 report
make report
```

Eval tools that connect to gemara-mcp (DFAH, mcp-eval, DeepEval, MCP Evals) manage their own server lifecycle — they spawn a `docker run --rm -i` process via MCP stdio transport. No separate `docker compose up` is needed.

## NFR6 Evaluation Workflow

Run evaluations in phases based on what infrastructure you have available:

### Phase 1 — No LLM needed (just gemara-mcp container)

```bash
make eval-mcp-eval     # Functional correctness (right output for right input)
make eval-dfah         # Trajectory + output determinism via MCP
```

### Phase 2 — LLM needed (Ollama OR Vertex AI OR OpenAI)

```bash
make eval-detllm       # Raw LLM determinism isolation
make eval-deepeval     # Full-stack determinism + tool selection (LLM-as-judge)
make eval-promptfoo    # Regression assertions
make eval-mcpevals     # LLM-scored quality rubric
```

### Phase 3 — Aggregate

```bash
make report            # NFR6 pass/fail verdict (aggregates all available results)
```

The report works with whatever results exist — you don't need all six harnesses to get a verdict.

### LLM Backend Selection

The LLM backend is auto-detected from environment variables. Set `LLM_PROVIDER` to force a specific backend, or let it auto-detect:

| Priority | Backend | Required env vars |
|---|---|---|
| 1 | Ollama (local) | `OLLAMA_BASE_URL` + Ollama running | 
| 2 | Vertex AI | `VERTEX_PROJECT` + `VERTEX_LOCATION` |
| 3 | OpenAI | `OPENAI_API_KEY` |

```bash
# Use Vertex AI instead of Ollama
LLM_PROVIDER=vertex_ai VERTEX_PROJECT=my-project make eval-detllm

# Use OpenAI
LLM_PROVIDER=openai OPENAI_API_KEY=sk-... make eval-detllm

# Force Ollama-direct mode (bypasses litellm, useful for seed control)
cd eval/detllm && python3 run_detllm.py --direct --corpus ../../corpus
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

### Server

| Variable | Default | Used by |
|---|---|---|
| `GEMARA_MCP_IMAGE` | `ghcr.io/gemaraproj/gemara-mcp:v0.1.0` | All MCP-connected evals |
| `GEMARA_MCP_MODE` | `artifact` | All MCP-connected evals |
| `CONTAINER_RUNTIME` | `docker` | All MCP-connected evals, Makefile |

### LLM Backend

| Variable | Default | Used by |
|---|---|---|
| `LLM_PROVIDER` | *(auto-detect)* | All LLM-using harnesses |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | detLLM, MCP Evals, shared provider |
| `OLLAMA_MODEL` | `qwen2.5:7b` | detLLM, MCP Evals, Promptfoo |
| `VERTEX_PROJECT` | — | Vertex AI provider |
| `VERTEX_LOCATION` | `us-central1` | Vertex AI provider |
| `VERTEX_MODEL` | `gemini-2.0-flash` | Vertex AI provider |
| `OPENAI_API_KEY` | — | OpenAI provider |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI provider |
| `EVAL_MODEL` | *(from provider)* | DeepEval, MCP Evals (litellm model string) |
| `LLM_PROVIDER_PROMPTFOO` | `ollama:chat:qwen2.5:7b` | Promptfoo provider string |

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
