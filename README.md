# gemara-mcp-eval

Determinism evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — measuring NFR6 compliance (90% deterministic outcomes for artifact generation).

## NFR6 Objective

> The combination of the Context Tool and CUE Validation must ensure at least 90% deterministic outcomes for artifact generation.

"Deterministic outcomes" means: given the same input, the gemara-mcp server returns the **same output every time**. This is a property of the server, not of the LLM querying it.

---

## Evaluation Phases

The framework is split into two phases with a strict separation of concerns:

| Phase | Purpose | NFR6 role | Needs LLM |
|---|---|---|---|
| **Phase 1** | Output determinism | **NFR6 gate** — determines pass/fail | No |
| **Phase 2** | LLM integration quality | Advisory only — never affects verdict | Yes |

Both phases live on this branch (`feat/phase2-report`).

### Phase 1 — Output Determinism

Measures whether gemara-mcp produces identical outputs for identical inputs across 20 repeated runs. No LLM is involved at any stage.

| Tool | What it measures | Runs per scenario |
|---|---|---|
| **DFAH** | Trajectory determinism + faithfulness via direct MCP calls | 20 |
| **mcp-eval** | Full MCP surface (tool + prompt) with exact-match across repeated runs | 20 |

**This is the NFR6 gate.** Phase 1 alone determines pass/fail.

See [PHASE1-OUTPUT-DETERMINISM.md](./PHASE1-OUTPUT-DETERMINISM.md) for full details.

### Phase 2 — LLM Integration Quality

Measures how well the LLM layer interacts with gemara-mcp. Results are advisory — they inform quality but do not affect the NFR6 verdict.

| Tool | What it measures | Needs LLM |
|---|---|---|
| **detLLM** | Raw LLM output consistency across repeated calls | Yes |
| **MCP Evals** | LLM-scored tool response quality (accuracy, completeness, clarity) | Yes (LLM-as-judge) |
| **Promptfoo** | Assertion-based regression testing | Yes |

See [PHASE2-LLM-DETERMINISM.md](./PHASE2-LLM-DETERMINISM.md) for full details.

---

## Quick Start

### Phase 1 — no LLM needed

```bash
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval

pip install -r eval/dfah/requirements.txt
pip install -r eval/mcp-eval/requirements.txt

make corpus-validate
make eval-phase1
make report-phase1
```

### Phase 2 — requires Ollama + Node.js

```bash
# After running Phase 1 above:
pip install -r eval/detllm/requirements.txt
pip install -r eval/mcp-eval/requirements.txt
cd eval/mcpevals && npm install && cd ../..
npm install -g promptfoo

make eval-phase2
make report-phase2

# Merge both reports into a single NFR6 report
make report
```

Each harness spawns its own `docker run --rm -i ghcr.io/gemaraproj/gemara-mcp:v0.1.0` process via MCP stdio transport. No `docker compose up` is needed.

---

## Make Targets

| Target | What it runs |
|---|---|
| `make corpus-validate` | Validate corpus inputs against Gemara CUE schemas |
| `make eval-phase1` | DFAH + mcp-eval (no LLM) |
| `make eval-phase2` | detLLM + MCP Evals + Promptfoo (needs LLM) |
| `make eval-full` | Phase 1 + Phase 2 |
| `make report-phase1` | NFR6 Phase 1 report → `results/nfr6-phase1-report.json` |
| `make report-phase2` | Advisory Phase 2 report → `results/nfr6-phase2-report.json` |
| `make report` | Merged report → `results/nfr6-report.json` (merges both if available) |

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
│   ├── dfah/               # Phase 1: DFAH harness + benchmarks
│   ├── mcp-eval/           # Phase 1: mcp-eval scenario runner
│   ├── detllm/             # Phase 2: raw LLM determinism
│   ├── mcpevals/           # Phase 2: LLM-scored MCP quality (Node.js)
│   └── promptfoo/          # Phase 2: assertion-based regression (Node.js)
├── analysis/
│   └── nfr6_report.py      # NFR6 report generator (supports --phase 1|2, --merge)
└── results/                # Generated at runtime (gitignored)
```

---

## gemara-mcp Surface Under Test

- **Tool**: `validate_gemara_artifact` — validate YAML against Gemara CUE schemas (`#ControlCatalog`, `#ThreatCatalog`, `#Policy`, `#EvaluationLog`)
- **Prompts**: `threat_assessment`, `control_catalog` — template-rendered content keyed by `component` and `id_prefix`

---

## Prerequisites

| Phase | Requirements |
|---|---|
| Phase 1 | Python 3.10+, Docker or Podman, [CUE CLI](https://cuelang.org/docs/install/) |
| Phase 2 | + Node.js 20+, [Ollama](https://ollama.ai/) with `qwen2.5:7b` |

---

## CI

`.github/workflows/determinism-check.yml` defines two jobs:

| Job | Triggers | Blocks PRs |
|---|---|---|
| `output-determinism` (Phase 1) | push, pull_request, workflow_dispatch | Yes — exits 1 on FAIL |
| `llm-determinism` (Phase 2) | workflow_dispatch, weekly schedule | No — `continue-on-error: true` |

---

## Related

- [gemara](https://github.com/gemaraproj/gemara) — GRC Engineering Model (CUE schemas)
- [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — MCP Server
- [Issue #14](https://github.com/gemaraproj/gemara-mcp/issues/14) — Explore solutions for MCP Evaluation
- [DFAH paper](https://arxiv.org/abs/2601.15322) — Determinism-Faithfulness Assurance Harness

## License

Apache-2.0
