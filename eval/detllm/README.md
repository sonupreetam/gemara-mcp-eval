# detLLM Evaluation

Raw LLM determinism measurement independent of the MCP server layer.

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your-key
```

## Run

```bash
# From this directory
python run_detllm.py --corpus ../../corpus --output ../../results/detllm.json

# Or from repo root
make eval-detllm
```

## What it measures

- **Tier 0**: Generates artifacts and deterministic diffs (no equality guarantee)
- **Tier 1**: Verifies run-to-run repeatability for fixed batch size
- **Tier 2**: Score/logprob equality (capability-gated)

Each corpus prompt is run N times (default: 20) and compared for consistency.
This isolates LLM-level determinism from MCP server behavior.
