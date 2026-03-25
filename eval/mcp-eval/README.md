# mcp-eval Evaluation

Language-agnostic MCP scenario testing using mcp-eval.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
# Generate scenarios from corpus and run
python run_mcp_eval.py --corpus ../../corpus --output ../../results/mcp-eval.json

# Or from repo root
make eval-mcp-eval
```

## What it tests

- Replays corpus scenarios as structured MCP interactions
- Dataset-driven: feeds the shared corpus directly
- Reports per-scenario pass/fail with step-level metrics
