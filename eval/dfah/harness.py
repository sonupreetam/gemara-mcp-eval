"""
DFAH: Determinism-Faithfulness Assurance Harness for gemara-mcp.

Adapted from IBM's DFAH framework (arXiv:2601.15322) for compliance
domain evaluation. Measures trajectory determinism and evidence-conditioned
faithfulness across repeated runs of gemara-mcp tool-using scenarios.

Reference: https://github.com/ibm-client-engineering/output-drift-financial-llms
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import yaml


class TrajectoryAnalyzer:
    """Measures trajectory determinism across repeated agent runs."""

    def __init__(self, runs_per_case: int = 20):
        self.runs_per_case = runs_per_case

    def extract_tool_trajectory(self, agent_output: dict) -> list[str]:
        """Extract the ordered sequence of tool calls from an agent run."""
        trajectory = []
        for step in agent_output.get("steps", []):
            if "tool_call" in step:
                tool_name = step["tool_call"].get("name", "unknown")
                trajectory.append(tool_name)
        return trajectory

    def compute_trajectory_determinism(self, trajectories: list[list[str]]) -> float:
        """
        Compute the fraction of runs that produce the identical tool call sequence.

        Returns a score between 0.0 and 1.0 where 1.0 means all runs
        produced the same trajectory.
        """
        if not trajectories:
            return 0.0
        canonical = [tuple(t) for t in trajectories]
        counts = Counter(canonical)
        most_common_count = counts.most_common(1)[0][1]
        return most_common_count / len(trajectories)

    def compute_output_determinism(self, outputs: list[dict], match_type: str = "exact") -> float:
        """
        Compute output determinism using the specified matching strategy.

        match_type:
          - "exact": byte-for-byte comparison of normalized output
          - "jaccard": Jaccard similarity of extracted entity sets
          - "structural": JSON/YAML structural comparison
        """
        if not outputs:
            return 0.0

        if match_type == "exact":
            normalized = [json.dumps(o, sort_keys=True) for o in outputs]
            counts = Counter(normalized)
            return counts.most_common(1)[0][1] / len(normalized)

        elif match_type == "jaccard":
            entity_sets = []
            for o in outputs:
                entities = set()
                self._extract_entities(o, entities)
                entity_sets.append(entities)

            if len(entity_sets) < 2:
                return 1.0

            reference = entity_sets[0]
            similarities = []
            for es in entity_sets[1:]:
                if not reference and not es:
                    similarities.append(1.0)
                elif not reference or not es:
                    similarities.append(0.0)
                else:
                    intersection = reference & es
                    union = reference | es
                    similarities.append(len(intersection) / len(union))
            return float(np.mean(similarities))

        elif match_type == "structural":
            normalized = []
            for o in outputs:
                normalized.append(self._structural_normalize(o))
            counts = Counter(normalized)
            return counts.most_common(1)[0][1] / len(normalized)

        return 0.0

    def _extract_entities(self, obj, entities: set, prefix: str = ""):
        """Recursively extract identifiable entities from nested structures."""
        if isinstance(obj, dict):
            for key in ("id", "reference-id", "title", "name"):
                if key in obj:
                    entities.add(f"{prefix}{key}:{obj[key]}")
            for k, v in obj.items():
                self._extract_entities(v, entities, f"{prefix}{k}.")
        elif isinstance(obj, list):
            for item in obj:
                self._extract_entities(item, entities, prefix)
        elif isinstance(obj, str):
            id_pattern = re.compile(r"[A-Z0-9.-]+\.[A-Z]+\d+")
            for match in id_pattern.findall(obj):
                entities.add(f"id:{match}")

    def _structural_normalize(self, obj) -> str:
        """Produce a canonical string representation for structural comparison."""
        return json.dumps(obj, sort_keys=True, default=str)


class FaithfulnessAnalyzer:
    """Measures evidence-conditioned faithfulness of agent outputs."""

    def compute_faithfulness(self, output: dict, evidence: dict) -> float:
        """
        Score how well the output is grounded in the provided evidence.

        Returns a score between 0.0 and 1.0 where 1.0 means every claim
        in the output can be traced to the evidence.
        """
        output_entities = set()
        self._extract_claims(output, output_entities)

        evidence_entities = set()
        self._extract_claims(evidence, evidence_entities)

        if not output_entities:
            return 1.0

        grounded = output_entities & evidence_entities
        return len(grounded) / len(output_entities)

    def _extract_claims(self, obj, claims: set):
        """Extract verifiable claims from a data structure."""
        if isinstance(obj, dict):
            for key in ("id", "reference-id", "title", "text"):
                if key in obj and isinstance(obj[key], str):
                    claims.add(obj[key].strip().lower())
            for v in obj.values():
                self._extract_claims(v, claims)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_claims(item, claims)


def load_benchmark(benchmark_path: Path) -> list[dict]:
    with open(benchmark_path) as f:
        return json.load(f)


def simulate_agent_run(case: dict, run_idx: int) -> dict:
    """
    Placeholder for actual agent execution.

    In production, this calls the gemara-mcp server via MCP protocol
    and records the full tool call trajectory and final output.
    Replace this with actual MCP client invocation.
    """
    return {
        "case_id": case["id"],
        "run": run_idx,
        "steps": [
            {"tool_call": {"name": "validate_gemara_artifact", "args": {"definition": case.get("definition", "#ControlCatalog")}}},
        ],
        "output": case.get("expected_output", {}),
    }


def run_benchmark(benchmark_path: Path, runs: int = 20) -> dict:
    """Run a single benchmark file through the DFAH harness."""
    cases = load_benchmark(benchmark_path)
    analyzer = TrajectoryAnalyzer(runs_per_case=runs)
    faithfulness = FaithfulnessAnalyzer()

    results = []
    for case in cases:
        agent_runs = [simulate_agent_run(case, i) for i in range(runs)]

        trajectories = [analyzer.extract_tool_trajectory(r) for r in agent_runs]
        traj_determinism = analyzer.compute_trajectory_determinism(trajectories)

        outputs = [r["output"] for r in agent_runs]
        match_type = case.get("match_type", "jaccard")
        output_determinism = analyzer.compute_output_determinism(outputs, match_type)

        faith_scores = []
        evidence = case.get("evidence", {})
        for r in agent_runs:
            faith_scores.append(faithfulness.compute_faithfulness(r["output"], evidence))

        results.append({
            "case_id": case["id"],
            "trajectory_determinism": traj_determinism,
            "output_determinism": output_determinism,
            "faithfulness_mean": float(np.mean(faith_scores)),
            "faithfulness_std": float(np.std(faith_scores)),
            "runs": runs,
            "match_type": match_type,
        })

    traj_scores = [r["trajectory_determinism"] for r in results]
    output_scores = [r["output_determinism"] for r in results]
    faith_means = [r["faithfulness_mean"] for r in results]

    # Pearson correlation between determinism and faithfulness (DFAH key finding)
    correlation = 0.0
    if len(output_scores) > 2:
        from scipy.stats import pearsonr

        try:
            corr, p_value = pearsonr(output_scores, faith_means)
            correlation = float(corr)
        except Exception:
            correlation = 0.0

    return {
        "benchmark": benchmark_path.stem,
        "total_cases": len(cases),
        "runs_per_case": runs,
        "trajectory_determinism_mean": float(np.mean(traj_scores)),
        "output_determinism_mean": float(np.mean(output_scores)),
        "faithfulness_mean": float(np.mean(faith_means)),
        "determinism_faithfulness_correlation": correlation,
        "nfr6_threshold": 0.9,
        "nfr6_passed": float(np.mean(output_scores)) >= 0.9,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="DFAH harness for gemara-mcp determinism evaluation")
    parser.add_argument("--benchmarks", type=Path, default=Path(__file__).parent / "benchmarks")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent.parent / "results" / "dfah.json")
    args = parser.parse_args()

    benchmark_files = sorted(args.benchmarks.glob("*.json"))
    if not benchmark_files:
        print(f"No benchmark files found in {args.benchmarks}")
        sys.exit(1)

    print(f"DFAH Harness: {len(benchmark_files)} benchmarks, {args.runs} runs per case")

    all_results = []
    for bf in benchmark_files:
        print(f"\n  Running benchmark: {bf.stem}")
        result = run_benchmark(bf, runs=args.runs)
        all_results.append(result)
        status = "PASS" if result["nfr6_passed"] else "FAIL"
        print(f"    {status}: determinism={result['output_determinism_mean']:.3f}, "
              f"faithfulness={result['faithfulness_mean']:.3f}, "
              f"correlation={result['determinism_faithfulness_correlation']:.3f}")

    summary = {
        "tool": "dfah",
        "total_benchmarks": len(all_results),
        "nfr6_passed": all(r["nfr6_passed"] for r in all_results),
        "overall_determinism": float(np.mean([r["output_determinism_mean"] for r in all_results])),
        "overall_faithfulness": float(np.mean([r["faithfulness_mean"] for r in all_results])),
        "benchmarks": all_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nOverall: determinism={summary['overall_determinism']:.3f}, "
          f"faithfulness={summary['overall_faithfulness']:.3f}")
    print(f"NFR6 (>=0.9): {'PASS' if summary['nfr6_passed'] else 'FAIL'}")
    print(f"Results written to {args.output}")

    return 0 if summary["nfr6_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
