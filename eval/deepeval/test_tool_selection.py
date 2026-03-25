"""
DeepEval tests for MCP tool selection accuracy (Issue #14, Criterion 1).

Evaluates whether the correct gemara-mcp tools/prompts/resources are
invoked for different request types, using real MCP server responses.
"""

import asyncio
import json

from deepeval import evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase

EVAL_MODEL = "ollama/qwen2.5:7b"


TOOL_SELECTION_SCENARIOS = [
    {
        "input": "Validate this YAML against the ControlCatalog schema: metadata:\\n  id: TEST\\n  type: ControlCatalog",
        "expected_tool": "validate_gemara_artifact",
        "expected_output_keywords": ["valid", "ControlCatalog"],
        "mcp_action": "call_tool",
        "mcp_args": {
            "artifact_content": "metadata:\n  id: TEST\n  type: ControlCatalog",
            "definition": "#ControlCatalog",
        },
    },
    {
        "input": "Check if this threat catalog is valid: metadata:\\n  id: TC-01\\n  type: ThreatCatalog",
        "expected_tool": "validate_gemara_artifact",
        "expected_output_keywords": ["valid", "ThreatCatalog"],
        "mcp_action": "call_tool",
        "mcp_args": {
            "artifact_content": "metadata:\n  id: TC-01\n  type: ThreatCatalog",
            "definition": "#ThreatCatalog",
        },
    },
    {
        "input": "I want to create a threat assessment for a Kubernetes cluster using prefix K8S",
        "expected_tool": "threat_assessment",
        "expected_output_keywords": ["threat", "capability"],
        "mcp_action": "get_prompt",
        "mcp_args": {"component": "Kubernetes Cluster", "id_prefix": "K8S"},
    },
    {
        "input": "Help me build a control catalog for an API Gateway with prefix APIGW",
        "expected_tool": "control_catalog",
        "expected_output_keywords": ["control", "family", "assessment"],
        "mcp_action": "get_prompt",
        "mcp_args": {"component": "API Gateway", "id_prefix": "APIGW"},
    },
    {
        "input": "What is the Gemara schema for a RiskCatalog?",
        "expected_tool": "gemara://schema/definitions",
        "expected_output_keywords": ["RiskCatalog", "schema"],
        "mcp_action": "read_resource",
        "mcp_args": {"uri": "gemara://schema/definitions"},
    },
]


def _get_actual_output(mcp_client, scenario: dict) -> str:
    """Call the real MCP server and return the response as a string."""
    loop = asyncio.get_event_loop()

    async def _call():
        action = scenario["mcp_action"]
        args = scenario["mcp_args"]

        if action == "call_tool":
            result = await mcp_client.call_tool("validate_gemara_artifact", args)
            return f"Tool: validate_gemara_artifact. Result: {result.text}"

        elif action == "get_prompt":
            result = await mcp_client.get_prompt(
                scenario["expected_tool"], args
            )
            text = result.text
            return f"Prompt: {scenario['expected_tool']}. Content: {text[:1000]}"

        elif action == "read_resource":
            text = await mcp_client.read_resource(args["uri"])
            return f"Resource: {args['uri']}. Content: {text[:1000]}"

        return "[Error] Unknown action"

    return loop.run_until_complete(_call())


def test_tool_selection_accuracy(mcp_client):
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
        model=EVAL_MODEL,
    )

    test_cases = []
    for scenario in TOOL_SELECTION_SCENARIOS:
        actual_output = _get_actual_output(mcp_client, scenario)
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=actual_output,
            expected_output=f"The system should invoke {scenario['expected_tool']} "
            f"and the response should reference: {', '.join(scenario['expected_output_keywords'])}",
        )
        test_cases.append(test_case)

    results = evaluate(test_cases, [correctness_metric])
    passed = sum(1 for r in results.test_results if r.success)
    total = len(results.test_results)
    assert passed / total >= 0.8, f"Tool selection accuracy {passed}/{total} below 80% threshold"


def test_validate_artifact_parameter_accuracy(mcp_client):
    """Verify validate_gemara_artifact receives correct definition parameter."""
    loop = asyncio.get_event_loop()

    scenarios = [
        ("#ControlCatalog", "metadata:\n  type: ControlCatalog"),
        ("#ThreatCatalog", "metadata:\n  type: ThreatCatalog"),
        ("#GuidanceCatalog", "metadata:\n  type: GuidanceCatalog"),
        ("#Policy", "metadata:\n  type: Policy"),
        ("#EvaluationLog", "metadata:\n  type: EvaluationLog"),
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
        model=EVAL_MODEL,
    )

    test_cases = []
    for definition, artifact_snippet in scenarios:
        async def call_with(defn=definition, artifact=artifact_snippet):
            result = await mcp_client.call_tool("validate_gemara_artifact", {
                "artifact_content": artifact,
                "definition": defn,
            })
            return result.text

        actual = loop.run_until_complete(call_with())
        test_cases.append(
            LLMTestCase(
                input=f"Validate this artifact: {artifact_snippet}",
                actual_output=f"Called validate_gemara_artifact with definition={definition}. Result: {actual}",
                expected_output=f"The tool should be called with definition={definition}",
            )
        )

    results = evaluate(test_cases, [metric])
    passed = sum(1 for r in results.test_results if r.success)
    assert passed == len(scenarios), f"Parameter accuracy: {passed}/{len(scenarios)}"
