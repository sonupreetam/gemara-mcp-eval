"""
Cross-tool comparison: aggregate results from all evaluation frameworks
and produce a side-by-side comparison.
"""

import argparse
import json
import sys
from pathlib import Path


TOOL_NAMES = ["detllm", "deepeval", "mcpevals", "mcp-eval", "dfah", "promptfoo"]


def load_results(results_dir: Path) -> dict:
    """Load all available result files."""
    results = {}
    for tool in TOOL_NAMES:
        path = results_dir / f"{tool}.json"
        if path.exists():
            with open(path) as f:
                results[tool] = json.load(f)
    return results


def extract_determinism_score(tool: str, data: dict) -> float | None:
    """Extract the primary determinism score from each tool's output format."""
    if tool == "detllm":
        passed = data.get("passed", 0)
        total = data.get("total_scenarios", 1)
        return passed / total if total > 0 else None

    elif tool == "dfah":
        return data.get("overall_determinism")

    elif tool == "deepeval":
        # DeepEval pytest results
        return None  # requires parsing pytest JSON output

    elif tool == "promptfoo":
        results = data.get("results", {}).get("results", [])
        if results:
            passed = sum(1 for r in results if r.get("success", False))
            return passed / len(results)
        return None

    elif tool in ("mcpevals", "mcp-eval"):
        passed = data.get("passed", 0)
        total = data.get("total", data.get("total_scenarios", 1))
        return passed / total if total > 0 else None

    return None


def compare(results_dir: Path) -> dict:
    results = load_results(results_dir)

    comparison = {
        "tools_available": list(results.keys()),
        "tools_missing": [t for t in TOOL_NAMES if t not in results],
        "scores": {},
    }

    for tool, data in results.items():
        score = extract_determinism_score(tool, data)
        comparison["scores"][tool] = {
            "determinism_score": score,
            "nfr6_passed": score is not None and score >= 0.9,
            "raw_summary": {
                k: v
                for k, v in data.items()
                if k in ("passed", "failed", "total_scenarios", "total", "overall_determinism", "overall_faithfulness", "nfr6_passed")
            },
        }

    scores = [s["determinism_score"] for s in comparison["scores"].values() if s["determinism_score"] is not None]
    if scores:
        comparison["aggregate"] = {
            "mean_determinism": sum(scores) / len(scores),
            "min_determinism": min(scores),
            "max_determinism": max(scores),
            "tools_reporting": len(scores),
            "nfr6_passed": (sum(scores) / len(scores)) >= 0.9,
        }

    return comparison


def main():
    parser = argparse.ArgumentParser(description="Compare results across evaluation tools")
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent.parent / "results")
    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"Results directory not found: {args.results_dir}")
        print("Run 'make eval-all' first.")
        sys.exit(1)

    comparison = compare(args.results_dir)

    print("=" * 70)
    print("Cross-Tool Determinism Comparison")
    print("=" * 70)

    print(f"\nTools available: {', '.join(comparison['tools_available']) or 'None'}")
    if comparison["tools_missing"]:
        print(f"Tools missing:   {', '.join(comparison['tools_missing'])}")

    print("\nPer-Tool Scores:")
    print(f"  {'Tool':<15} {'Determinism':>12} {'NFR6':>8}")
    print(f"  {'-' * 15} {'-' * 12} {'-' * 8}")
    for tool, scores in comparison["scores"].items():
        det = scores["determinism_score"]
        det_str = f"{det:.3f}" if det is not None else "N/A"
        nfr6 = "PASS" if scores["nfr6_passed"] else "FAIL"
        print(f"  {tool:<15} {det_str:>12} {nfr6:>8}")

    agg = comparison.get("aggregate")
    if agg:
        print(f"\nAggregate ({agg['tools_reporting']} tools):")
        print(f"  Mean:  {agg['mean_determinism']:.3f}")
        print(f"  Range: [{agg['min_determinism']:.3f}, {agg['max_determinism']:.3f}]")
        print(f"  NFR6:  {'PASS' if agg['nfr6_passed'] else 'FAIL'}")


if __name__ == "__main__":
    main()
