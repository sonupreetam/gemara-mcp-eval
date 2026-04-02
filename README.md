# gemara-mcp-eval

Determinism evaluation framework for [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — measuring NFR6 compliance (90% deterministic outcomes for artifact generation).

## NFR6 Objective

> The combination of the Context Tool and CUE Validation must ensure at least 90% deterministic outcomes for artifact generation.

"Deterministic outcomes" means: given the same input, the gemara-mcp server returns the **same output every time**. This is a property of the server, not of the LLM querying it.

## Evaluation Phases

The framework is split into two phases with a strict separation of concerns:

| Phase | Branch | Purpose | NFR6 role |
|---|---|---|---|
| **Phase 1** | `feat/phase1-report` | Output determinism — no LLM | **NFR6 gate** |
| **Phase 2** | `feat/phase2-report` | LLM integration quality | Advisory only |

### Phase 1 — Output Determinism

Measures whether gemara-mcp produces identical outputs for identical inputs across 20 repeated runs. No LLM is involved at any stage.

| Tool | What it measures | Runs per scenario |
|---|---|---|
| **DFAH** | Trajectory determinism + faithfulness via direct MCP calls | 20 |
| **mcp-eval** | Full MCP surface (tool + prompt) with exact-match across repeated runs | 20 |

**This is the NFR6 gate.** Phase 1 alone determines pass/fail.

See [PHASE1-OUTPUT-DETERMINISM.md](./PHASE1-OUTPUT-DETERMINISM.md) for full details on tools, scoring, corpus, and CI.

### Phase 2 — LLM Integration Quality

Measures how well the LLM layer works with gemara-mcp. Results are advisory — they inform quality but do not affect the NFR6 verdict.

| Tool | What it measures | Needs LLM |
|---|---|---|
| **detLLM** | Raw LLM output consistency across repeated calls | Yes |
| **MCP Evals** | LLM-scored tool response quality (accuracy, completeness, clarity) | Yes (LLM-as-judge) |
| **Promptfoo** | Assertion-based regression testing | Yes |

Phase 2 adds on top of Phase 1 — switch to `feat/phase2-report` when LLM infrastructure is available.

---

## Quick Start

```bash
git clone --recurse-submodules https://github.com/<your-user>/gemara-mcp-eval.git
cd gemara-mcp-eval
git checkout feat/phase1-report

pip install -r eval/dfah/requirements.txt
pip install -r eval/mcp-eval/requirements.txt

make corpus-validate
make eval-phase1
make report-phase1
```

No LLM, no Ollama, no Node.js needed for Phase 1.

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
│   └── mcp-eval/           # mcp-eval scenario runner
├── analysis/
│   └── nfr6_report.py      # NFR6 report generator
└── results/                # Generated at runtime (gitignored)
```

---

## gemara-mcp Surface Under Test

- **Tool**: `validate_gemara_artifact` — validate YAML against Gemara CUE schemas (`#ControlCatalog`, `#ThreatCatalog`, `#Policy`, `#EvaluationLog`)
- **Prompts**: `threat_assessment`, `control_catalog` — template-rendered content keyed by `component` and `id_prefix`

---

## Related

- [gemara](https://github.com/gemaraproj/gemara) — GRC Engineering Model (CUE schemas)
- [gemara-mcp](https://github.com/gemaraproj/gemara-mcp) — MCP Server
- [Issue #14](https://github.com/gemaraproj/gemara-mcp/issues/14) — Explore solutions for MCP Evaluation
- [DFAH paper](https://arxiv.org/abs/2601.15322) — Determinism-Faithfulness Assurance Harness

## License

Apache-2.0
