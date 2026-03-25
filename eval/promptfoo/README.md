# Promptfoo Evaluation

Assertion-based regression testing for gemara-mcp determinism.

## Setup

```bash
npm install -g promptfoo
```

## Run

```bash
# From this directory
npx promptfoo eval

# Or from repo root
make eval-promptfoo
```

## What it tests

- **Dimension 1** (tc-001 to tc-005): `validate_gemara_artifact` tool produces correct pass/fail results
- **Dimension 2** (tc-010 to tc-014): `threat_assessment` prompt generates expected threat categories
- **Dimension 3** (tc-020 to tc-024): `control_catalog` prompt generates expected control families

## Assertions

Each test case uses deterministic assertions (`contains`, `icontains`, `is-valid-yaml`) to verify
that generated artifacts contain expected keywords and structures. Custom determinism assertions
in `assertions/determinism.js` measure consistency across repeated runs.
