"""
detLLM wrapper for gemara-mcp corpus.

Reads prompt templates from the shared corpus and runs each through detLLM
to measure raw LLM determinism (Tier 0/1/2) independent of the MCP server.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_corpus(corpus_dir: Path) -> dict:
    scenarios_path = corpus_dir / "scenarios.yaml"
    with open(scenarios_path) as f:
        return yaml.safe_load(f)["scenarios"]


def build_prompts(corpus_dir: Path, scenarios: list) -> list:
    """Build concrete prompts from corpus scenarios."""
    prompts = []

    for scenario in scenarios:
        if scenario["type"] == "tool":
            input_file = corpus_dir / scenario["input_file"]
            if not input_file.exists():
                continue
            artifact_content = input_file.read_text()
            definition = scenario["tool_params"]["definition"]
            prompt = (
                f"Validate the following YAML artifact against the Gemara {definition} schema. "
                f"Return JSON with fields: valid (boolean), errors (array), message (string).\n\n"
                f"```yaml\n{artifact_content}\n```"
            )
            prompts.append(
                {
                    "id": scenario["id"],
                    "prompt": prompt,
                    "match_type": scenario["determinism"]["match_type"],
                    "threshold": scenario["determinism"]["threshold"],
                }
            )
        elif scenario["type"] == "prompt":
            template_file = corpus_dir / scenario["prompt_template"]
            if not template_file.exists():
                continue
            template = template_file.read_text()
            params = scenario.get("prompt_params", {})
            prompt = template
            for key, value in params.items():
                prompt = prompt.replace(f"{{{{{key}}}}}", value)
            prompts.append(
                {
                    "id": scenario["id"],
                    "prompt": prompt,
                    "match_type": scenario["determinism"]["match_type"],
                    "threshold": scenario["determinism"]["threshold"],
                }
            )
    return prompts


def run_detllm_check(prompt_entry: dict, config: dict) -> dict:
    """Run a single prompt through detLLM and return the result."""
    try:
        from detllm import check

        report = check(
            backend=config["backend"],
            model=config["model"],
            prompts=[prompt_entry["prompt"]],
            runs=config["runs"],
            batch_size=config["batch_size"],
            tier=config["tier"],
        )
        return {
            "scenario_id": prompt_entry["id"],
            "tier": config["tier"],
            "runs": config["runs"],
            "deterministic": report.get("deterministic", False),
            "match_rate": report.get("match_rate", 0.0),
            "threshold": prompt_entry["threshold"],
            "passed": report.get("match_rate", 0.0) >= prompt_entry["threshold"],
        }
    except ImportError:
        return {
            "scenario_id": prompt_entry["id"],
            "error": "detllm not installed. Run: pip install 'detllm[test]'",
            "passed": False,
        }
    except Exception as e:
        return {
            "scenario_id": prompt_entry["id"],
            "error": str(e),
            "passed": False,
        }


def main():
    parser = argparse.ArgumentParser(description="Run detLLM determinism checks on gemara-mcp corpus")
    parser.add_argument("--corpus", type=Path, default=Path(__file__).parent.parent.parent / "corpus")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config.yaml")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent.parent / "results" / "detllm.json")
    args = parser.parse_args()

    config = load_config(args.config)
    scenarios = load_corpus(args.corpus)
    prompts = build_prompts(args.corpus, scenarios)

    print(f"Running detLLM checks: {len(prompts)} prompts, {config['runs']} runs each, Tier {config['tier']}")

    results = []
    for prompt_entry in prompts:
        print(f"  Checking {prompt_entry['id']}...")
        result = run_detllm_check(prompt_entry, config)
        results.append(result)
        status = "PASS" if result.get("passed") else "FAIL"
        print(f"    {status}: {result.get('match_rate', 'N/A')}")

    summary = {
        "tool": "detllm",
        "config": {k: v for k, v in config.items() if k != "output_dir"},
        "total_scenarios": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "failed": sum(1 for r in results if not r.get("passed")),
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary: {summary['passed']}/{summary['total_scenarios']} passed")
    print(f"Results written to {args.output}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
