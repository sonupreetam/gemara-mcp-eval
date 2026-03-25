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
export OPENAI_API_KEY=your-key
```

## Run

```bash
# Run the harness
python harness.py --benchmarks benchmarks/ --runs 20 --output ../../results/dfah.json

# Analyze results
python analyze.py --input ../../results/dfah.json

# Or from repo root
make eval-dfah
```

## Benchmarks

Three gemara-specific benchmarks adapted from DFAH's financial domain:

| Benchmark | DFAH Equivalent | Cases | Measures |
|---|---|---|---|
| `control-suggestion.json` | Compliance Triage | 5 (expandable to 50) | Control selection consistency |
| `threat-mapping.json` | Portfolio Constraints | 5 (expandable to 50) | Threat identification consistency |
| `artifact-validation.json` | DataOps Exceptions | 5 (expandable to 50) | Validation result determinism |

## Key Metrics

- **Trajectory Determinism**: Do the same MCP tools get called in the same order?
- **Output Determinism**: Are the same controls/threats suggested? (Jaccard similarity)
- **Evidence-Conditioned Faithfulness**: Are outputs grounded in provided evidence?
- **Determinism-Faithfulness Correlation**: Does determinism correlate with faithfulness? (DFAH's key finding: r=0.45)
