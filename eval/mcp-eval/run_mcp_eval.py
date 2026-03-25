"""
mcp-eval wrapper for gemara-mcp corpus.

Converts corpus scenarios into mcp-eval's scenario format and runs them
against the gemara-mcp server for language-agnostic evaluation.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

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


def run_scenarios(scenarios: list) -> list:
    """
    Execute mcp-eval scenarios against gemara-mcp.

    Placeholder: replace with actual mcp-eval client execution.
    """
    results = []
    for scenario in scenarios:
        results.append({
            "id": scenario["id"],
            "name": scenario["name"],
            "steps_total": len(scenario["steps"]),
            "steps_passed": 0,
            "status": "pending",
            "message": "Wire up mcp-eval client to execute against live gemara-mcp server.",
            "determinism": scenario.get("determinism", {}),
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="Run mcp-eval scenarios for gemara-mcp")
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent.parent / "results" / "mcp-eval.json")
    args = parser.parse_args()

    scenarios = load_corpus(args.corpus)
    mcp_scenarios = corpus_to_mcp_eval_scenarios(scenarios, args.corpus)

    # Write scenarios for reference
    scenarios_dir = Path(__file__).parent / "scenarios"
    scenarios_dir.mkdir(exist_ok=True)
    with open(scenarios_dir / "generated.json", "w") as f:
        json.dump(mcp_scenarios, f, indent=2)

    print(f"mcp-eval: {len(mcp_scenarios)} scenarios generated from corpus")

    results = run_scenarios(mcp_scenarios)

    summary = {
        "tool": "mcp-eval",
        "total_scenarios": len(results),
        "passed": sum(1 for r in results if r["status"] == "passed"),
        "pending": sum(1 for r in results if r["status"] == "pending"),
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Results written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
