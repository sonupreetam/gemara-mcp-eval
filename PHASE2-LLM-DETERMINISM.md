# Phase 2 — LLM Integration Quality Evaluation

This document describes the Phase 2 evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp). Phase 2 measures how well the LLM layer integrates with the gemara-mcp server.

**Phase 2 is advisory only.** Its results never affect the NFR6 pass/fail verdict. That verdict is determined exclusively by [Phase 1 (output determinism)](./PHASE1-OUTPUT-DETERMINISM.md).

---

## Why Phase 2 Exists

Phase 1 proves the server is deterministic. Phase 2 answers a separate question: when an LLM uses gemara-mcp as a tool, does it do so correctly and consistently?

| Question | Answered by |
|---|---|
| Does the server produce the same output for the same input? | Phase 1 |
| Does the LLM reliably select the right tools? | Phase 2 |
| Does the LLM produce quality responses when guided by gemara-mcp? | Phase 2 |
| Does LLM token variance affect the system? | Phase 2 (expected — not an NFR6 concern) |

Phase 2 results inform development quality and regression tracking. They are tagged `advisory: true` in the NFR6 report and excluded from the verdict score.

---

## Tools

### detLLM — Raw LLM Determinism

- Sends the same prompt to the LLM (via litellm) **multiple times**
- Measures output consistency at three tiers:
  - **Tier 0** — exact string match
  - **Tier 1** — semantic similarity above threshold
  - **Tier 2** — intent/structure match
- Does **not** connect to gemara-mcp; isolates the LLM layer in isolation
- Score = `passed / total_scenarios`

Output: `results/detllm.json`

### MCP Evals (`mcpevals`) — LLM-Scored Tool Response Quality

- Sends MCP tool calls **through an LLM agent** (the LLM decides which tool to invoke and how to use the response)
- Scores responses on five dimensions using an LLM-as-judge:
  - **Accuracy** — factual correctness of the response
  - **Completeness** — all required fields / content present
  - **Relevance** — response addresses the prompt intent
  - **Clarity** — response is well-structured and readable
  - **Reasoning** — the LLM's tool selection and usage logic is sound
- Requires Node.js; uses `npx ts-node eval-suite.ts`
- Score = `passed / evaluated` (scenarios that score above threshold)

Output: `results/mcpevals.json`

### Promptfoo — Assertion-Based Regression Testing

- Sends prompts to the LLM and runs assertion checks against the responses
- Assertions verify that expected keywords, artifact identifiers, and structural patterns appear in LLM output
- Used as a regression guard — catches regressions in how the LLM uses gemara-mcp tools across model or prompt changes
- Score = `passed / total` test assertions

Output: `results/promptfoo.json`

---

## Quick Start

```bash
# Phase 1 must be run first (or at least the gemara-mcp image must be built)
make eval-phase1
make report-phase1

# Install Phase 2 dependencies
pip install -r eval/detllm/requirements.txt
pip install -r eval/mcp-eval/requirements.txt
cd eval/mcpevals && npm install && cd ../..
npm install -g promptfoo

# Start Ollama with the required model
ollama pull qwen2.5:7b
ollama serve   # if not already running

# Run Phase 2 evaluations
make eval-phase2        # runs detllm + mcpevals + promptfoo

# Generate the Phase 2 advisory report
make report-phase2

# Optionally merge Phase 1 + Phase 2 into a single combined report
make report
```

To run each harness individually:

```bash
make eval-detllm        # detLLM only
make eval-mcpevals      # MCP Evals only
make eval-promptfoo     # Promptfoo only
make eval-correctness   # Promptfoo correctness suite (informational)
```

---

## Output

### Report files

| File | Contents |
|---|---|
| `results/detllm.json` | Per-scenario LLM consistency results with tier breakdown |
| `results/mcpevals.json` | Per-scenario LLM-scored quality results |
| `results/promptfoo.json` | Per-assertion Promptfoo results |
| `results/nfr6-phase2-report.json` | Structured advisory report (Phase 2) |
| `results/nfr6-phase2-report.md` | Human-readable markdown summary |
| `results/nfr6-report.json` | Combined Phase 1 + Phase 2 report (after `make report`) |

### Console summary

```
============================================================
NFR6 Compliance Report
============================================================

Generated:  2026-03-30T...
Phase:      Phase 2 (LLM advisory)
Threshold:  N/A (advisory only)
Tools:      3/4 evaluated

Per-Tool:
  detllm           XX.X%  PASS/FAIL [advisory]
  mcpevals         XX.X%  PASS/FAIL [advisory]
  promptfoo        XX.X%  PASS/FAIL [advisory]
```

### JSON structure

```python
import json

with open("results/nfr6-phase2-report.json") as f:
    report = json.load(f)

for a in report["per_tool_assessments"]:
    print(a["tool"], a["determinism_score"], a["advisory"])
    # advisory is always True for Phase 2 tools

# Combined report (after make report) preserves NFR6 verdict from Phase 1
with open("results/nfr6-report.json") as f:
    combined = json.load(f)

verdict = combined["nfr6_report"]["nfr6_verdict"]   # driven by Phase 1 only
advisory = combined["advisory_summary"]              # Phase 2 scores summary
```

---

## CI Integration

`.github/workflows/determinism-check.yml` defines the `llm-determinism` job for Phase 2.

```
workflow_dispatch / weekly schedule
          │
          ▼
  llm-determinism  (continue-on-error: true — never blocks PRs)
  ├── checkout (with submodules)
  ├── setup Python + Node.js
  ├── install Python deps (detllm + mcp-eval)
  ├── npm install (mcpevals)
  ├── install promptfoo
  ├── docker build gemara-mcp image
  ├── pull Ollama model (qwen2.5:7b)
  ├── make eval-phase2
  ├── make eval-correctness (informational, always runs)
  ├── make report-phase2
  └── upload results/ artifact
```

Phase 2 never gates a PR. It is informational by design.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMARA_MCP_IMAGE` | `ghcr.io/gemaraproj/gemara-mcp:v0.1.0` | Container image used by MCP-connected evals |
| `CONTAINER_RUNTIME` | `docker` | `docker` or `podman` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model used by detLLM, MCP Evals, Promptfoo |

---

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker or Podman
- [Ollama](https://ollama.ai/) with `qwen2.5:7b` pulled

---

## Related

- [PHASE1-OUTPUT-DETERMINISM.md](./PHASE1-OUTPUT-DETERMINISM.md) — Phase 1 documentation (NFR6 gate)
- [gemara](https://github.com/gemaraproj/gemara) — GRC Engineering Model (CUE schemas)
- [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — MCP Server
- [Issue #14](https://github.com/gemaraproj/gemara-mcp/issues/14) — Explore solutions for MCP Evaluation
