# gemara-mcp-eval

Determinism evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — measuring NFR6 compliance (90% deterministic outcomes for artifact generation).

## Overview

This repo evaluates all gemara-mcp tools, prompts, and resources using six evaluation frameworks:

| Framework | Focus | Language |
|---|---|---|
| **detLLM** | Raw LLM determinism (Tier 0/1/2) | Python |
| **DeepEval** | MCP tool selection + output quality | Python |
| **MCP Evals** | LLM-scored tool response quality | Node.js |
| **mcp-eval** | Language-agnostic MCP scenario testing | Python |
| **DFAH** | Trajectory determinism + faithfulness (adapted from IBM) | Python |
| **Promptfoo** | Assertion-based regression testing | Node.js |

All frameworks share a single test corpus (`corpus/`) to ensure consistent measurement.

## gemara-mcp Surface Under Test

- **Tool**: `validate_gemara_artifact` — validate YAML against Gemara CUE schemas
- **Resources**: `gemara://lexicon`, `gemara://schema/definitions`, `gemara://schema/definitions{?version}`
- **Prompts** (artifact mode): `threat_assessment`, `control_catalog`

## Prerequisites

- Go 1.22+ (to build gemara-mcp)
- Python 3.10+
- Node.js 20+
- Docker & Docker Compose
- [CUE CLI](https://cuelang.org/docs/install/)

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval

# Start gemara-mcp server
docker compose up -d

# Validate the test corpus
make corpus-validate

# Run all evaluations
make eval-all

# Generate NFR6 report
make report
```

## Running Individual Evaluations

```bash
make eval-detllm       # Raw LLM determinism
make eval-deepeval     # MCP tool selection + determinism
make eval-mcpevals     # LLM-scored quality
make eval-mcp-eval     # Scenario replay
make eval-dfah         # Trajectory determinism (DFAH)
make eval-promptfoo    # Regression assertions
```

## Repo Structure

```
gemara-mcp-eval/
├── reference/          # Pinned submodules (gemara schemas, gemara-mcp server)
├── corpus/             # Shared test corpus (scenarios, inputs, golden outputs, prompts)
├── eval/               # Per-tool evaluation harnesses
│   ├── detllm/
│   ├── deepeval/
│   ├── mcpevals/
│   ├── mcp-eval/
│   ├── dfah/
│   └── promptfoo/
├── analysis/           # Cross-tool comparison and NFR6 reporting
└── ci/                 # CI/CD (Dockerfile, GitHub Actions)
```

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
