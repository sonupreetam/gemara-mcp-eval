"""
detLLM wrapper for gemara-mcp corpus.

Reads prompt templates from the shared corpus and runs each through detLLM
to measure raw LLM determinism (Tier 0/1/2) independent of the MCP server.

Uses Ollama (local) as the LLM backend via its HTTP API.
"""

import argparse
import json
import sys
import urllib.request
from collections import Counter
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


def ollama_generate(base_url: str, model: str, prompt: str, temperature: float = 0.0, seed: int = 42) -> str:
    """Call Ollama's /api/generate endpoint and return the response text."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
        },
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data.get("response", "")


class OllamaAdapter:
    """detLLM BackendAdapter that calls a local Ollama instance."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434",
                 temperature: float = 0.0, seed: int = 42):
        self._model = model
        self._base_url = base_url
        self._temperature = temperature
        self._seed = seed

    def capabilities(self):
        from detllm.backends.base import BackendCapabilities
        return BackendCapabilities(
            supports_tier1_fixed_batch=True,
            supports_scores=False,
            supports_torch_deterministic=False,
            notes=["Ollama local model via HTTP API"],
        )

    def generate(self, prompts: list[str], **kwargs) -> list[dict]:
        results = []
        for prompt in prompts:
            text = ollama_generate(
                self._base_url, self._model, prompt,
                self._temperature, self._seed,
            )
            results.append({"text": text, "finish_reason": "stop"})
        return results


def run_detllm_check(prompt_entry: dict, config: dict) -> dict:
    """Run a single prompt through detLLM with Ollama adapter."""
    try:
        from detllm import check

        adapter = OllamaAdapter(
            model=config["model"],
            base_url=config.get("ollama_base_url", "http://localhost:11434"),
            temperature=config.get("temperature", 0.0),
            seed=config.get("seed", 42),
        )
        report = check(
            backend="custom",
            model=config["model"],
            prompts=[prompt_entry["prompt"]],
            runs=config["runs"],
            batch_size=config["batch_size"],
            tier=config["tier"],
            backend_adapter=adapter,
        )
        match_rate = getattr(report, "match_rate", None)
        if match_rate is None:
            match_rate = report.get("match_rate", 0.0) if isinstance(report, dict) else 0.0
        deterministic = getattr(report, "deterministic", None)
        if deterministic is None:
            deterministic = report.get("deterministic", False) if isinstance(report, dict) else False

        return {
            "scenario_id": prompt_entry["id"],
            "tier": config["tier"],
            "runs": config["runs"],
            "deterministic": deterministic,
            "match_rate": match_rate,
            "threshold": prompt_entry["threshold"],
            "passed": match_rate >= prompt_entry["threshold"],
        }
    except Exception as e:
        return {
            "scenario_id": prompt_entry["id"],
            "error": str(e),
            "passed": False,
        }


def run_direct_ollama(prompt_entry: dict, config: dict) -> dict:
    """Measure determinism by calling Ollama directly N times."""
    base_url = config.get("ollama_base_url", "http://localhost:11434")
    runs = config.get("runs", 5)
    outputs = []

    for _ in range(runs):
        text = ollama_generate(
            base_url, config["model"], prompt_entry["prompt"],
            config.get("temperature", 0.0), config.get("seed", 42),
        )
        outputs.append(text)

    counts = Counter(outputs)
    most_common = counts.most_common(1)[0][1]
    match_rate = most_common / len(outputs)
    unique_count = len(counts)

    return {
        "scenario_id": prompt_entry["id"],
        "runs": runs,
        "unique_outputs": unique_count,
        "match_rate": match_rate,
        "deterministic": unique_count == 1,
        "threshold": prompt_entry["threshold"],
        "passed": match_rate >= prompt_entry["threshold"],
    }


def main():
    parser = argparse.ArgumentParser(description="Run detLLM determinism checks on gemara-mcp corpus")
    parser.add_argument("--corpus", type=Path, default=Path(__file__).parent.parent.parent / "corpus")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config.yaml")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent.parent / "results" / "detllm.json")
    parser.add_argument("--direct", action="store_true", help="Skip detLLM framework, call Ollama directly")
    parser.add_argument("--max-scenarios", type=int, default=0, help="Limit number of scenarios (0=all)")
    args = parser.parse_args()

    config = load_config(args.config)
    scenarios = load_corpus(args.corpus)
    prompts = build_prompts(args.corpus, scenarios)

    if args.max_scenarios > 0:
        prompts = prompts[:args.max_scenarios]

    print(f"Running detLLM checks: {len(prompts)} prompts, {config['runs']} runs each")
    print(f"Model: {config['model']}, Backend: {'direct ollama' if args.direct else 'detllm+ollama adapter'}")

    results = []
    for prompt_entry in prompts:
        print(f"  Checking {prompt_entry['id']}...")
        if args.direct:
            result = run_direct_ollama(prompt_entry, config)
        else:
            result = run_detllm_check(prompt_entry, config)
            if result.get("error"):
                print(f"    detLLM failed ({result['error']}), falling back to direct Ollama...")
                result = run_direct_ollama(prompt_entry, config)
        results.append(result)
        status = "PASS" if result.get("passed") else "FAIL"
        print(f"    {status}: match_rate={result.get('match_rate', 'N/A')}")

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
