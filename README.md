# gemara-mcp-eval

Determinism evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — measuring NFR6 compliance (90% deterministic outcomes for artifact generation).

## NFR6 Objective

> The combination of the Context Tool and CUE Validation must ensure at least 90% deterministic outcomes for artifact generation.

"Deterministic outcomes for artifact generation" means: given the same input, the gemara-mcp server must produce the same output every time. This is a property of the **server** — not of the LLM querying it.

This distinction drives the two-phase evaluation architecture.

---

## Evaluation Architecture

The framework is split into two phases with a clear separation of concerns:

### Phase 1 — Output Determinism (this branch)

Measures whether gemara-mcp produces **identical outputs** for identical inputs across repeated runs. No LLM is involved.

| Tool | What it measures | Connects to MCP | Runs per scenario |
|---|---|---|---|
| **DFAH** | Trajectory determinism + faithfulness across 20 runs | Yes (stdio) | 20 |
| **mcp-eval** | Full MCP surface (tool + prompt) with repeated-run exact match | Yes (stdio) | 20 |

**This is the NFR6 gate.** Phase 1 alone determines pass/fail.

### Phase 2 — LLM Integration Quality (additive, `feat/phase2-report`)

Measures how well the LLM layer works with gemara-mcp. Results are **advisory only** — they inform but do not affect the NFR6 verdict.

| Tool | What it measures | Needs LLM |
|---|---|---|
| **detLLM** | Raw LLM output consistency across repeated calls | Yes |
| **MCP Evals** | LLM-scored tool response quality (accuracy, completeness, clarity) | Yes (LLM-as-judge) |
| **Promptfoo** | Assertion-based regression testing via LLM | Yes |

Phase 2 tooling lives in the `feat/phase2-report` branch and can be layered on when LLM infrastructure is available.

---

## Why Separate Phases?

A naive average across all six tools conflates two different things:

- **LLM non-determinism** — the LLM produces slightly different text each call; this is inherent and expected
- **Server output determinism** — gemara-mcp's CUE validation and prompt templates are deterministic; they must return identical results every time

Including LLM-based tools in the NFR6 score would systematically undercount compliance because LLMs are never 100% consistent. Phase 1 isolates what the spec actually requires: the server's output is stable.

---

## gemara-mcp Surface Under Test

- **Tool**: `validate_gemara_artifact` — validate YAML against Gemara CUE schemas (`#ControlCatalog`, `#ThreatCatalog`, `#Policy`, `#EvaluationLog`)
- **Prompts**: `threat_assessment`, `control_catalog` — template-rendered prompt content keyed by `component` and `id_prefix`

## Test Corpus

15 scenarios in `corpus/scenarios.yaml`, all configured with `determinism: {runs: 20, match_type: exact, threshold: 1.0}`:

| ID | Type | Description |
|---|---|---|
| tc-001 | tool | Validate valid Layer 2 ControlCatalog |
| tc-002 | tool | Validate ControlCatalog missing required group |
| tc-003 | tool | Validate valid Layer 2 ThreatCatalog |
| tc-004 | tool | Validate ThreatCatalog with wrong metadata type |
| tc-005 | tool | Validate empty artifact content |
| tc-010..014 | prompt | Threat assessment — Kubernetes, CI/CD, storage, API gateway, secrets vault |
| tc-020..024 | prompt | Control catalog — workload protection, logging, IAM, encryption, supply chain |

Each tool scenario runs `validate_gemara_artifact` 20 times and checks that `valid: true/false` is identical across all runs. Each prompt scenario invokes the prompt 20 times and checks that the rendered template text is byte-for-byte identical.

---

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval
git checkout feat/phase1-report

# Install dependencies (no LLM needed)
pip install -r eval/dfah/requirements.txt
pip install -r eval/mcp-eval/requirements.txt

# Validate the test corpus against Gemara CUE schemas
make corpus-validate

# Run Phase 1 evaluations (DFAH + mcp-eval)
make eval-phase1

# Generate the NFR6 Phase 1 report
make report-phase1
```

`eval-phase1` spawns the gemara-mcp container automatically via MCP stdio transport — no `docker compose up` needed.

---

## How Determinism Is Measured

### DFAH (Determinism-Faithfulness Assurance Harness)

DFAH calls gemara-mcp directly via MCP protocol for each benchmark case across 3 benchmark suites:

- `artifact-validation.json` — `validate_gemara_artifact` tool calls
- `threat-mapping.json` — `threat_assessment` prompt invocations  
- `control-suggestion.json` — `control_catalog` prompt invocations

Each case is run **20 times**. DFAH computes:
- **Trajectory determinism** — fraction of runs where the full response matches run-0 (exact or Jaccard similarity)
- **Faithfulness** — whether the response content is consistent with the input
- **Overall determinism score** — weighted average across all cases and benchmarks

### mcp-eval

mcp-eval converts the shared `corpus/scenarios.yaml` into MCP stdio calls and runs each scenario **20 times**:

1. For each run, the step response is collected (raw JSON for tool calls, rendered text for prompts)
2. All 20 responses are compared against run-0 using `match_type: exact`
3. `match_rate = matching_runs / 20`
4. A scenario **passes** only when:
   - The assertion is correct (functional correctness on run-0)
   - `match_rate >= threshold` (1.0 = 100% identical outputs)

This means a scenario where the server returns different output on any of 20 runs will fail — which is exactly what NFR6 requires.

---

## Making and Reading the Report

```bash
make report-phase1
```

Produces `results/nfr6-phase1-report.json` and `results/nfr6-phase1-report.md`.

```
NFR6 Compliance Report
============================================================
Phase:     Phase 1 (output determinism)
Threshold: 90%
Score:     <overall>
Verdict:   PASS / FAIL

Per-Tool:
  dfah            100.0%  PASS
  mcp-eval         XX.X%  PASS / FAIL
```

The overall score is the mean of DFAH and mcp-eval scores. Verdict is PASS when score ≥ 90%.

To check the verdict in CI or a script:

```python
import json, sys
with open("results/nfr6-phase1-report.json") as f:
    r = json.load(f)
verdict = r["nfr6_report"]["nfr6_verdict"]
score   = r["nfr6_report"]["overall_determinism_score"]
print(f"{verdict} ({score:.1%})")
sys.exit(0 if verdict == "PASS" else 1)
```

---

## CI

The `output-determinism` job in `.github/workflows/determinism-check.yml` runs on every push, pull request, and manual dispatch. It:

1. Builds the gemara-mcp Docker image from the pinned submodule
2. Runs `make eval-phase1`
3. Runs `make report-phase1`
4. Checks the NFR6 verdict — fails the job if the score is below 90%

No LLM backend, no Ollama, no Node.js — only Python + Docker.

---

## Repo Structure

```
gemara-mcp-eval/
├── reference/              # Pinned submodules (Gemara schemas + gemara-mcp server)
├── corpus/
│   ├── scenarios.yaml      # 15 scenarios shared by all harnesses
│   └── inputs/             # YAML artifact files for tool scenarios
├── eval/
│   ├── shared/             # Shared MCP stdio client (Python)
│   ├── dfah/               # DFAH harness + benchmarks
│   │   └── benchmarks/     # artifact-validation, threat-mapping, control-suggestion
│   └── mcp-eval/           # mcp-eval scenario runner
├── analysis/
│   └── nfr6_report.py      # NFR6 report generator (--phase 1 for Phase 1 output)
└── results/                # Generated at runtime (gitignored)
```

---

## Prerequisites

- Python 3.10+
- Docker or Podman (for running gemara-mcp server via stdio)
- [CUE CLI](https://cuelang.org/docs/install/) (for corpus validation only)

No LLM, no Ollama, no Node.js needed for Phase 1.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMARA_MCP_IMAGE` | `ghcr.io/gemaraproj/gemara-mcp:v0.1.0` | Container image for gemara-mcp server |
| `GEMARA_MCP_MODE` | `artifact` | Server mode |
| `CONTAINER_RUNTIME` | `docker` | `docker` or `podman` |

---

## Adding Phase 2 (LLM Advisory)

The `feat/phase2-report` branch extends this branch with `eval-phase2`, `report-phase2`, and the `llm-determinism` CI job. Phase 2 adds detLLM, MCP Evals, and Promptfoo. Their results are tagged `advisory: true` and do not contribute to the NFR6 verdict.

```bash
git checkout feat/phase2-report
make eval-phase2        # requires Ollama / Vertex AI / OpenAI
make report-phase2      # produces nfr6-phase2-report.json
make report             # merges phase1 + phase2 into nfr6-report.json
```

---

## Related

- [gemara](https://github.com/gemaraproj/gemara) — GRC Engineering Model (CUE schemas)
- [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — MCP Server
- [Issue #14](https://github.com/gemaraproj/gemara-mcp/issues/14) — Explore solutions for MCP Evaluation
- [DFAH paper](https://arxiv.org/abs/2601.15322) — Determinism-Faithfulness Assurance Harness

## License

Apache-2.0
