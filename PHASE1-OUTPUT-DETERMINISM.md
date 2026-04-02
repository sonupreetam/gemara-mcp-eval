# Phase 1 — Output Determinism Evaluation

This document describes the Phase 1 evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp), which is the **NFR6 gate**: the only evaluation that determines pass/fail for the 90% determinism requirement.

---

## NFR6 Objective

> The combination of the Context Tool and CUE Validation must ensure at least 90% deterministic outcomes for artifact generation.

"Deterministic outcomes for artifact generation" means: given the same input, the gemara-mcp server must produce the **same output every time**. This is a property of the server — not of the LLM querying it.

Phase 1 measures exactly this. No LLM is involved at any point.

---

## Why Phase 1 Alone Decides NFR6

A naive average across all evaluation tools conflates two different things:

| Phenomenon | Source | What it means |
|---|---|---|
| **Server output drift** | gemara-mcp bug or non-deterministic schema evaluation | Violates NFR6 |
| **LLM token variance** | Inherent temperature/sampling in the language model | Expected, not an NFR6 concern |

Including LLM-based tools (detLLM, MCP Evals, Promptfoo) in the NFR6 score would systematically undercount compliance because LLMs are never 100% consistent. Phase 1 isolates what the spec actually requires: the server's output is stable.

Phase 2 (LLM integration quality) is advisory — it informs quality but does not affect the verdict.

---

## Tools

### DFAH — Determinism-Faithfulness Assurance Harness

- Calls gemara-mcp directly via MCP stdio protocol
- Runs each benchmark case **20 times**, comparing all responses against run-0
- Computes trajectory determinism, faithfulness, and an overall score across three benchmark suites

| Benchmark | MCP surface exercised |
|---|---|
| `artifact-validation.json` | `validate_gemara_artifact` tool |
| `threat-mapping.json` | `threat_assessment` prompt |
| `control-suggestion.json` | `control_catalog` prompt |

Score = `overall_determinism` in `results/dfah.json` (weighted mean across all cases and suites).

### mcp-eval

- Converts `corpus/scenarios.yaml` into MCP stdio calls
- Runs each scenario **20 times** (from `determinism.runs: 20` in the corpus)
- Collects the raw response per run: JSON for tool calls, rendered text for prompt invocations
- Compares every run against run-0 using `match_type: exact`
- Computes `match_rate = matching_runs / 20`

A scenario **passes** only when both criteria are met:

1. **Functional assertion** — run-0 response satisfies the assertion (e.g. `$.valid == true`)
2. **Determinism** — `match_rate >= threshold` (corpus sets `threshold: 1.0`, i.e. 100% identical)

Score = `passed / total_scenarios` in `results/mcp-eval.json`.

---

## Test Corpus

`corpus/scenarios.yaml` — 15 scenarios, all configured with:

```yaml
determinism:
  runs: 20
  match_type: exact
  threshold: 1.0
```

| ID | Type | Surface | Description |
|---|---|---|---|
| tc-001 | tool | `validate_gemara_artifact` | Valid Layer 2 ControlCatalog |
| tc-002 | tool | `validate_gemara_artifact` | ControlCatalog missing required group |
| tc-003 | tool | `validate_gemara_artifact` | Valid Layer 2 ThreatCatalog |
| tc-004 | tool | `validate_gemara_artifact` | ThreatCatalog with wrong metadata type |
| tc-005 | tool | `validate_gemara_artifact` | Empty artifact content |
| tc-010 | prompt | `threat_assessment` | Kubernetes cluster |
| tc-011 | prompt | `threat_assessment` | CI/CD pipeline |
| tc-012 | prompt | `threat_assessment` | Distributed storage |
| tc-013 | prompt | `threat_assessment` | API gateway |
| tc-014 | prompt | `threat_assessment` | Secrets vault |
| tc-020 | prompt | `control_catalog` | Workload protection |
| tc-021 | prompt | `control_catalog` | Audit logging |
| tc-022 | prompt | `control_catalog` | IAM |
| tc-023 | prompt | `control_catalog` | Encryption at rest |
| tc-024 | prompt | `control_catalog` | Supply chain integrity |

Tool scenarios assert `valid: true` (valid inputs) or `valid: false` (invalid inputs). Prompt scenarios use `contains_any` to assert that expected threat/control identifiers appear in the rendered template.

---

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval
git checkout feat/phase1-report

# Install dependencies (no LLM, no Node.js needed)
pip install -r eval/dfah/requirements.txt
pip install -r eval/mcp-eval/requirements.txt

# Validate corpus inputs against Gemara CUE schemas
make corpus-validate

# Run Phase 1 evaluations
make eval-phase1        # runs eval-dfah + eval-mcp-eval in sequence

# Generate the NFR6 Phase 1 report
make report-phase1
```

Each harness spawns its own `docker run --rm -i ghcr.io/gemaraproj/gemara-mcp:v0.1.0` process via MCP stdio transport. No `docker compose up` is needed.

To run each harness individually:

```bash
make eval-dfah          # DFAH only
make eval-mcp-eval      # mcp-eval only
```

---

## Output

### Report files

| File | Contents |
|---|---|
| `results/dfah.json` | Raw DFAH results per benchmark and case |
| `results/mcp-eval.json` | Per-scenario results with `match_rate` per run |
| `results/nfr6-phase1-report.json` | Structured NFR6 report (Phase 1) |
| `results/nfr6-phase1-report.md` | Human-readable markdown summary |

### Console summary

```
============================================================
NFR6 Compliance Report
============================================================

Generated:  2026-03-30T...
Phase:      Phase 1 (output determinism)
Threshold:  90%
Score:      XX.X%
Verdict:    PASS / FAIL
Tools:      2/2 evaluated

Per-Tool:
  dfah                 100.0%  PASS
  mcp-eval              XX.X%  PASS / FAIL
```

### JSON structure

```python
import json

with open("results/nfr6-phase1-report.json") as f:
    report = json.load(f)

verdict = report["nfr6_report"]["nfr6_verdict"]   # "PASS" or "FAIL"
score   = report["nfr6_report"]["overall_determinism_score"]  # 0.0–1.0

for a in report["per_tool_assessments"]:
    print(a["tool"], a["determinism_score"], a["nfr6_contribution"])
```

The `overall_determinism_score` is the mean of DFAH and mcp-eval scores. Verdict is PASS when score ≥ 90%.

---

## CI Integration

`.github/workflows/determinism-check.yml` defines the `output-determinism` job. It runs on every push, pull request, and manual dispatch (`workflow_dispatch`). No LLM backend or Node.js is required.

```
push / pull_request / workflow_dispatch
          │
          ▼
  output-determinism
  ├── checkout (with submodules)
  ├── install Python deps (dfah + mcp-eval only)
  ├── docker build gemara-mcp image
  ├── make corpus-validate
  ├── make eval-phase1
  ├── make report-phase1
  ├── upload results/ artifact
  └── check verdict → exit 1 if FAIL
```

The threshold check reads directly from the JSON report:

```python
verdict = report["nfr6_report"]["nfr6_verdict"]
sys.exit(0 if verdict == "PASS" else 1)
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMARA_MCP_IMAGE` | `ghcr.io/gemaraproj/gemara-mcp:v0.1.0` | Container image used by both harnesses |
| `GEMARA_MCP_MODE` | `artifact` | Server mode passed to container |
| `CONTAINER_RUNTIME` | `docker` | `docker` or `podman` |

---

## Prerequisites

- Python 3.10+
- Docker or Podman
- [CUE CLI](https://cuelang.org/docs/install/) (for `make corpus-validate` only)

No Ollama, no Vertex AI, no OpenAI, no Node.js.

---

## Adding Phase 2 (LLM Advisory)

Phase 2 is available on this branch (`feat/phase2-report`). It adds LLM integration quality tooling (detLLM, MCP Evals, Promptfoo) whose results are tagged `advisory: true` and never affect the NFR6 verdict.

```bash
make eval-phase2        # requires Ollama + Node.js
make report-phase2      # produces results/nfr6-phase2-report.json
make report             # merges phase1 + phase2 into results/nfr6-report.json
```

See [PHASE2-LLM-DETERMINISM.md](./PHASE2-LLM-DETERMINISM.md) for full details.

---

## Related

- [gemara](https://github.com/gemaraproj/gemara) — GRC Engineering Model (CUE schemas)
- [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — MCP Server
- [Issue #14](https://github.com/gemaraproj/gemara-mcp/issues/14) — Explore solutions for MCP Evaluation
- [DFAH paper](https://arxiv.org/abs/2601.15322) — Determinism-Faithfulness Assurance Harness
