"""
mcp-eval wrapper for gemara-mcp corpus.

Converts corpus scenarios into mcp-eval's scenario format and executes them
against the gemara-mcp server via MCP stdio transport.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.mcp_client import GemaraMCPClient

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"


def load_corpus(corpus_dir: Path) -> list:
    with open(corpus_dir / "scenarios.yaml") as f:
        return yaml.safe_load(f)["scenarios"]


def corpus_to_mcp_eval_scenarios(scenarios: list, corpus_dir: Path) -> list:
    """Convert corpus scenarios to mcp-eval scenario format."""
    mcp_scenarios = []

    for scenario in scenarios:
        if scenario["type"] == "tool":
            input_file = corpus_dir / scenario["input_file"]
            artifact_content = input_file.read_text() if input_file.exists() else ""

            mcp_scenarios.append({
                "id": scenario["id"],
                "name": scenario["name"],
                "steps": [
                    {
                        "action": "call_tool",
                        "tool": "validate_gemara_artifact",
                        "arguments": {
                            "artifact_content": artifact_content,
                            "definition": scenario["tool_params"]["definition"],
                        },
                        "assertions": [
                            {
                                "type": "json_path",
                                "path": "$.valid",
                                "expected": scenario["expected"]["result"] == "valid",
                            }
                        ],
                    }
                ],
                "determinism": scenario["determinism"],
            })

        elif scenario["type"] == "prompt":
            params = scenario.get("prompt_params", {})
            mcp_scenarios.append({
                "id": scenario["id"],
                "name": scenario["name"],
                "steps": [
                    {
                        "action": "invoke_prompt",
                        "prompt": scenario["target"],
                        "arguments": params,
                        "assertions": [
                            {
                                "type": "contains_any",
                                "values": scenario["expected"].get(
                                    "threats_must_include",
                                    scenario["expected"].get("controls_must_include", []),
                                ),
                            }
                        ],
                    }
                ],
                "determinism": scenario["determinism"],
            })

    return mcp_scenarios


def check_assertion(assertion: dict, result_data: dict | str) -> tuple[bool, str]:
    """Evaluate a single assertion against the result data."""
    atype = assertion["type"]

    if atype == "json_path":
        path = assertion["path"]
        expected = assertion["expected"]
        if path == "$.valid" and isinstance(result_data, dict):
            actual = result_data.get("valid")
            if actual == expected:
                return True, f"$.valid == {expected}"
            return False, f"$.valid: expected {expected}, got {actual}"
        return False, f"Unsupported json_path: {path}"

    elif atype == "contains_any":
        values = assertion.get("values", [])
        text = result_data if isinstance(result_data, str) else json.dumps(result_data)
        text_lower = text.lower()
        found = [v for v in values if v.lower() in text_lower]
        if found:
            return True, f"Found {len(found)}/{len(values)}: {found}"
        return False, f"None of {values} found in response"

    return False, f"Unknown assertion type: {atype}"


async def execute_step(client: GemaraMCPClient, step: dict) -> dict:
    """Execute a single scenario step against the MCP server."""
    action = step["action"]

    if action == "call_tool":
        result = await client.call_tool(step["tool"], step.get("arguments", {}))
        try:
            result_data = result.json
        except (json.JSONDecodeError, ValueError):
            result_data = {"raw": result.text, "is_error": result.is_error}

        assertion_results = []
        for assertion in step.get("assertions", []):
            passed, msg = check_assertion(assertion, result_data)
            assertion_results.append({"passed": passed, "message": msg})

        all_passed = all(a["passed"] for a in assertion_results)
        return {
            "action": action,
            "tool": step["tool"],
            "result": result_data,
            "assertions": assertion_results,
            "passed": all_passed,
        }

    elif action == "invoke_prompt":
        prompt_name = step["prompt"]
        prompt_args = step.get("arguments", {})
        prompt_args_str = {k: str(v) for k, v in prompt_args.items()}

        result = await client.get_prompt(prompt_name, prompt_args_str)
        result_text = result.text

        assertion_results = []
        for assertion in step.get("assertions", []):
            passed, msg = check_assertion(assertion, result_text)
            assertion_results.append({"passed": passed, "message": msg})

        all_passed = all(a["passed"] for a in assertion_results)
        return {
            "action": action,
            "prompt": prompt_name,
            "result_length": len(result_text),
            "assertions": assertion_results,
            "passed": all_passed,
        }

    return {"action": action, "passed": False, "message": f"Unknown action: {action}"}


async def run_scenarios(client: GemaraMCPClient, scenarios: list) -> list:
    """Execute mcp-eval scenarios against the live gemara-mcp server."""
    results = []
    for scenario in scenarios:
        steps_total = len(scenario["steps"])
        step_results = []

        for step in scenario["steps"]:
            try:
                step_result = await execute_step(client, step)
                step_results.append(step_result)
            except Exception as e:
                step_results.append({
                    "action": step["action"],
                    "passed": False,
                    "message": f"Error: {e}",
                })

        steps_passed = sum(1 for s in step_results if s.get("passed"))
        all_passed = steps_passed == steps_total

        results.append({
            "id": scenario["id"],
            "name": scenario["name"],
            "steps_total": steps_total,
            "steps_passed": steps_passed,
            "status": "passed" if all_passed else "failed",
            "message": "All steps passed" if all_passed else f"{steps_passed}/{steps_total} steps passed",
            "step_results": step_results,
            "determinism": scenario.get("determinism", {}),
        })
    return results


async def run_all(args) -> int:
    scenarios = load_corpus(args.corpus)
    mcp_scenarios = corpus_to_mcp_eval_scenarios(scenarios, args.corpus)

    scenarios_dir = Path(__file__).parent / "scenarios"
    scenarios_dir.mkdir(exist_ok=True)
    with open(scenarios_dir / "generated.json", "w") as f:
        json.dump(mcp_scenarios, f, indent=2)

    print(f"mcp-eval: {len(mcp_scenarios)} scenarios generated from corpus")

    async with GemaraMCPClient() as client:
        print("Connected to gemara-mcp server")
        results = await run_scenarios(client, mcp_scenarios)

    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"Results: {passed} passed, {failed} failed")

    summary = {
        "tool": "mcp-eval",
        "total_scenarios": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Results written to {args.output}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run mcp-eval scenarios for gemara-mcp")
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent.parent / "results" / "mcp-eval.json")
    args = parser.parse_args()

    sys.exit(asyncio.run(run_all(args)))


if __name__ == "__main__":
    main()
