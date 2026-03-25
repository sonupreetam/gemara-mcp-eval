# DeepEval Evaluation

MCP tool selection accuracy and N-run determinism measurement using DeepEval.

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your-key
```

## Run

```bash
# From this directory
python -m pytest test_tool_selection.py test_determinism.py -v

# Or from repo root
make eval-deepeval
```

## Test files

- `test_tool_selection.py` — Criterion 1: Are the right tools called for the right task?
- `test_determinism.py` — Criterion 3: Are results deterministic across runs?
- `conftest.py` — Shared fixtures loading from the corpus
