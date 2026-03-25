# DFAH Evaluation

Determinism-Faithfulness Assurance Harness adapted from IBM's framework
([arXiv:2601.15322](https://arxiv.org/abs/2601.15322)) for the Gemara
compliance domain.

## Reference

- Paper: "Replayable Financial Agents: A Determinism-Faithfulness Assurance Harness for Tool-Using LLM Agents"
- Code: https://github.com/ibm-client-engineering/output-drift-financial-llms

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
# Run against live gemara-mcp server (spawns Docker container via stdio)
python harness.py --benchmarks benchmarks/ --runs 20 --output ../../results/dfah.json

# Run in simulation mode (no server required, uses fixture data)
python harness.py --simulate

# Analyze results
python analyze.py --input ../../results/dfah.json

# Or from repo root
make eval-dfah
```

## Server Connection

The harness connects to gemara-mcp via MCP stdio transport, spawning a Docker
container (`docker run --rm -i <image> serve --mode artifact`). Configure via
environment variables:

- `GEMARA_MCP_IMAGE` — Docker image (default: `ghcr.io/gemaraproj/gemara-mcp:v0.1.0`)
- `CONTAINER_RUNTIME` — Container runtime (default: `docker`)

Use `--simulate` to run offline with fixture data (no Docker required).

## Benchmarks

Three gemara-specific benchmarks adapted from DFAH's financial domain:

| Benchmark | DFAH Equivalent | Cases | Measures |
|---|---|---|---|
| `artifact-validation.json` | DataOps Exceptions | 5 (expandable to 50) | Validation result determinism |
| `control-suggestion.json` | Compliance Triage | 5 (expandable to 50) | Control selection consistency |
| `threat-mapping.json` | Portfolio Constraints | 5 (expandable to 50) | Threat identification consistency |

The **artifact-validation** benchmark calls `validate_gemara_artifact` directly
and works self-contained. The **threat-mapping** and **control-suggestion**
benchmarks retrieve MCP prompts; full agentic flow (generating artifacts from
prompts) requires an LLM backend.

## Key Metrics

- **Trajectory Determinism**: Do the same MCP tools get called in the same order?
- **Output Determinism**: Are the same controls/threats suggested? (Jaccard similarity)
- **Evidence-Conditioned Faithfulness**: Are outputs grounded in provided evidence?
- **Determinism-Faithfulness Correlation**: Does determinism correlate with faithfulness? (DFAH's key finding: r=0.45)
