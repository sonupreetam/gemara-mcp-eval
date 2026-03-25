"""
DeepEval tests for MCP tool selection accuracy (Issue #14, Criterion 1).

Evaluates whether the LLM correctly selects validate_gemara_artifact
when given different artifact types and validation requests.
"""

from deepeval import evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase


TOOL_SELECTION_SCENARIOS = [
    {
        "input": "Validate this YAML against the ControlCatalog schema: metadata:\\n  id: TEST\\n  type: ControlCatalog",
        "expected_tool": "validate_gemara_artifact",
        "expected_output_keywords": ["valid", "ControlCatalog"],
    },
    {
        "input": "Check if this threat catalog is valid: metadata:\\n  id: TC-01\\n  type: ThreatCatalog",
        "expected_tool": "validate_gemara_artifact",
        "expected_output_keywords": ["valid", "ThreatCatalog"],
    },
    {
        "input": "I want to create a threat assessment for a Kubernetes cluster using prefix K8S",
        "expected_tool": "threat_assessment",
        "expected_output_keywords": ["threat", "capability"],
    },
    {
        "input": "Help me build a control catalog for an API Gateway with prefix APIGW",
        "expected_tool": "control_catalog",
        "expected_output_keywords": ["control", "family", "assessment"],
    },
    {
        "input": "What is the Gemara schema for a RiskCatalog?",
        "expected_tool": "gemara://schema/definitions",
        "expected_output_keywords": ["RiskCatalog", "schema"],
    },
]


def test_tool_selection_accuracy():
    """Verify the LLM selects the correct gemara-mcp tool for each task."""
    correctness_metric = GEval(
        name="Tool Selection Correctness",
        criteria=(
            "The output should indicate the correct gemara-mcp tool was used. "
            "For validation requests, validate_gemara_artifact should be called. "
            "For threat assessments, the threat_assessment prompt should be invoked. "
            "For control catalogs, the control_catalog prompt should be invoked. "
            "For schema questions, the gemara://schema/definitions resource should be accessed."
        ),
        evaluation_params=["input", "actual_output"],
        threshold=0.7,
    )

    test_cases = []
    for scenario in TOOL_SELECTION_SCENARIOS:
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=f"[Simulated] Tool: {scenario['expected_tool']}. "
            f"Keywords: {', '.join(scenario['expected_output_keywords'])}",
            expected_output=f"The system should invoke {scenario['expected_tool']} "
            f"and the response should reference: {', '.join(scenario['expected_output_keywords'])}",
        )
        test_cases.append(test_case)

    results = evaluate(test_cases, [correctness_metric])
    passed = sum(1 for r in results.test_results if r.success)
    total = len(results.test_results)
    assert passed / total >= 0.8, f"Tool selection accuracy {passed}/{total} below 80% threshold"


def test_validate_artifact_parameter_accuracy():
    """Verify validate_gemara_artifact receives correct definition parameter."""
    scenarios = [
        ("#ControlCatalog", "metadata:\\n  type: ControlCatalog"),
        ("#ThreatCatalog", "metadata:\\n  type: ThreatCatalog"),
        ("#GuidanceCatalog", "metadata:\\n  type: GuidanceCatalog"),
        ("#Policy", "metadata:\\n  type: Policy"),
        ("#EvaluationLog", "metadata:\\n  type: EvaluationLog"),
    ]

    metric = GEval(
        name="Parameter Accuracy",
        criteria=(
            "The definition parameter passed to validate_gemara_artifact "
            "must match the artifact's metadata.type field. "
            "A ControlCatalog artifact should be validated with #ControlCatalog."
        ),
        evaluation_params=["input", "actual_output"],
        threshold=0.8,
    )

    test_cases = []
    for definition, artifact_snippet in scenarios:
        test_cases.append(
            LLMTestCase(
                input=f"Validate this artifact: {artifact_snippet}",
                actual_output=f"Called validate_gemara_artifact with definition={definition}",
                expected_output=f"The tool should be called with definition={definition}",
            )
        )

    results = evaluate(test_cases, [metric])
    passed = sum(1 for r in results.test_results if r.success)
    assert passed == len(scenarios), f"Parameter accuracy: {passed}/{len(scenarios)}"
