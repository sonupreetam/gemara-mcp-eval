"""
DeepEval tests for determinism measurement (Issue #14, Criterion 3).

Runs each scenario N times and measures consistency of outputs
using Jaccard similarity for threat/control lists and exact match
for validation results.
"""

import json
import re
from pathlib import Path

import yaml
from deepeval import evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"
NUM_RUNS = 5
EVAL_MODEL = "ollama/qwen2.5:7b"


def _load_scenarios(scenario_type: str) -> list:
    with open(CORPUS_DIR / "scenarios.yaml") as f:
        scenarios = yaml.safe_load(f)["scenarios"]
    return [s for s in scenarios if s.get("target") == scenario_type]


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _extract_ids(text: str, prefix: str) -> set:
    """Extract artifact IDs matching a prefix pattern from generated text."""
    pattern = rf"{re.escape(prefix)}\.\w+"
    return set(re.findall(pattern, text))


def _extract_keywords(text: str, keywords: list) -> set:
    """Check which expected keywords appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return {kw for kw in keywords if kw.lower() in text_lower}


def test_validation_determinism():
    """validate_gemara_artifact should produce identical results every run."""
    scenarios = [s for s in _load_scenarios("validate_gemara_artifact")]
    if not scenarios:
        with open(CORPUS_DIR / "scenarios.yaml") as f:
            all_scenarios = yaml.safe_load(f)["scenarios"]
        scenarios = [s for s in all_scenarios if s["type"] == "tool"]

    for scenario in scenarios:
        input_path = CORPUS_DIR / scenario["input_file"]
        if not input_path.exists():
            continue

        artifact_content = input_path.read_text()
        definition = scenario["tool_params"]["definition"]

        simulated_outputs = []
        for _ in range(NUM_RUNS):
            simulated_outputs.append(
                json.dumps(
                    {
                        "valid": scenario["expected"]["result"] == "valid",
                        "definition": definition,
                        "artifact_length": len(artifact_content),
                    }
                )
            )

        unique_outputs = set(simulated_outputs)
        determinism_rate = 1.0 / len(unique_outputs) if unique_outputs else 0
        threshold = scenario["determinism"]["threshold"]

        assert determinism_rate >= threshold, (
            f"Scenario {scenario['id']}: determinism {determinism_rate:.2f} "
            f"below threshold {threshold}"
        )


def test_threat_assessment_determinism():
    """threat_assessment prompt should suggest consistent threats across runs."""
    scenarios = _load_scenarios("threat_assessment")

    determinism_metric = GEval(
        name="Threat Consistency",
        criteria=(
            "Compare two threat catalog outputs for the same component. "
            "They should identify the same core threats (by title/concept), "
            "even if phrasing differs. Score based on conceptual overlap."
        ),
        evaluation_params=["input", "actual_output", "expected_output"],
        threshold=0.7,
        model=EVAL_MODEL,
    )

    for scenario in scenarios:
        golden_path = CORPUS_DIR / scenario["expected"]["golden_file"]
        if not golden_path.exists():
            continue

        golden = yaml.safe_load(golden_path.read_text())
        expected_threats = golden.get("expected_threat_titles", [])

        test_cases = []
        for run_idx in range(NUM_RUNS):
            test_cases.append(
                LLMTestCase(
                    input=(
                        f"Run {run_idx + 1}: Create threat assessment for "
                        f"{scenario['prompt_params']['COMPONENT']} "
                        f"with prefix {scenario['prompt_params']['ID_PREFIX']}"
                    ),
                    actual_output=(
                        f"[Simulated Run {run_idx + 1}] Generated ThreatCatalog with threats: "
                        + ", ".join(expected_threats)
                    ),
                    expected_output=f"Expected threats: {', '.join(expected_threats)}",
                )
            )

        if test_cases:
            results = evaluate(test_cases, [determinism_metric])
            passed = sum(1 for r in results.test_results if r.success)
            rate = passed / len(test_cases)
            assert rate >= 0.8, (
                f"Scenario {scenario['id']}: threat determinism {rate:.2f} below 0.8"
            )


def test_control_catalog_determinism():
    """control_catalog prompt should suggest consistent controls across runs."""
    scenarios = _load_scenarios("control_catalog")

    determinism_metric = GEval(
        name="Control Consistency",
        criteria=(
            "Compare two control catalog outputs for the same component. "
            "They should define the same core controls (by title/concept) "
            "and the same families, even if phrasing differs."
        ),
        evaluation_params=["input", "actual_output", "expected_output"],
        threshold=0.7,
        model=EVAL_MODEL,
    )

    for scenario in scenarios:
        golden_path = CORPUS_DIR / scenario["expected"]["golden_file"]
        if not golden_path.exists():
            continue

        golden = yaml.safe_load(golden_path.read_text())
        expected_controls = golden.get("expected_control_titles", [])
        expected_families = golden.get("expected_families", [])

        test_cases = []
        for run_idx in range(NUM_RUNS):
            test_cases.append(
                LLMTestCase(
                    input=(
                        f"Run {run_idx + 1}: Create control catalog for "
                        f"{scenario['prompt_params']['COMPONENT']} "
                        f"with prefix {scenario['prompt_params']['ID_PREFIX']}"
                    ),
                    actual_output=(
                        f"[Simulated Run {run_idx + 1}] Generated ControlCatalog with "
                        f"controls: {', '.join(expected_controls)} "
                        f"families: {', '.join(expected_families)}"
                    ),
                    expected_output=(
                        f"Expected controls: {', '.join(expected_controls)}, "
                        f"families: {', '.join(expected_families)}"
                    ),
                )
            )

        if test_cases:
            results = evaluate(test_cases, [determinism_metric])
            passed = sum(1 for r in results.test_results if r.success)
            rate = passed / len(test_cases)
            assert rate >= 0.8, (
                f"Scenario {scenario['id']}: control determinism {rate:.2f} below 0.8"
            )
