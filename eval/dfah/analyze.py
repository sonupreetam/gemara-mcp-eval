"""
DFAH analysis: cross-benchmark comparison and determinism-faithfulness correlation.

Reads DFAH results and produces summary statistics and visualizations.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def analyze_results(results_path: Path) -> dict:
    with open(results_path) as f:
        data = json.load(f)

    analysis = {
        "summary": {
            "overall_determinism": data["overall_determinism"],
            "overall_faithfulness": data["overall_faithfulness"],
            "nfr6_passed": data["nfr6_passed"],
            "nfr6_threshold": 0.9,
        },
        "per_benchmark": [],
        "determinism_distribution": {},
    }

    for bench in data.get("benchmarks", []):
        det_scores = [r["output_determinism"] for r in bench["results"]]
        faith_scores = [r["faithfulness_mean"] for r in bench["results"]]

        analysis["per_benchmark"].append({
            "name": bench["benchmark"],
            "cases": bench["total_cases"],
            "determinism": {
                "mean": float(np.mean(det_scores)),
                "std": float(np.std(det_scores)),
                "min": float(np.min(det_scores)),
                "max": float(np.max(det_scores)),
                "pct_above_90": float(np.mean([1 for s in det_scores if s >= 0.9])),
            },
            "faithfulness": {
                "mean": float(np.mean(faith_scores)),
                "std": float(np.std(faith_scores)),
            },
            "correlation": bench["determinism_faithfulness_correlation"],
        })

    all_det = []
    for bench in data.get("benchmarks", []):
        for r in bench["results"]:
            all_det.append(r["output_determinism"])

    if all_det:
        analysis["determinism_distribution"] = {
            "total_cases": len(all_det),
            "mean": float(np.mean(all_det)),
            "std": float(np.std(all_det)),
            "p25": float(np.percentile(all_det, 25)),
            "p50": float(np.percentile(all_det, 50)),
            "p75": float(np.percentile(all_det, 75)),
            "p90": float(np.percentile(all_det, 90)),
            "pct_above_90": float(np.mean([1 for s in all_det if s >= 0.9]) * 100),
        }

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Analyze DFAH results")
    parser.add_argument("--input", type=Path, default=Path(__file__).parent.parent.parent / "results" / "dfah.json")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Results file not found: {args.input}")
        print("Run 'make eval-dfah' first.")
        sys.exit(1)

    analysis = analyze_results(args.input)

    print("=" * 60)
    print("DFAH Analysis Report")
    print("=" * 60)
    print(f"\nOverall Determinism: {analysis['summary']['overall_determinism']:.3f}")
    print(f"Overall Faithfulness: {analysis['summary']['overall_faithfulness']:.3f}")
    print(f"NFR6 (>=0.9): {'PASS' if analysis['summary']['nfr6_passed'] else 'FAIL'}")

    print("\nPer-Benchmark Breakdown:")
    for bench in analysis["per_benchmark"]:
        print(f"\n  {bench['name']} ({bench['cases']} cases)")
        print(f"    Determinism: {bench['determinism']['mean']:.3f} "
              f"(std={bench['determinism']['std']:.3f}, "
              f"min={bench['determinism']['min']:.3f}, "
              f"max={bench['determinism']['max']:.3f})")
        print(f"    Faithfulness: {bench['faithfulness']['mean']:.3f}")
        corr = bench['correlation']
        print(f"    Det-Faith Correlation: {corr:.3f}" if corr is not None else "    Det-Faith Correlation: N/A")

    dist = analysis.get("determinism_distribution", {})
    if dist:
        print(f"\nDistribution ({dist['total_cases']} total cases):")
        print(f"  p25={dist['p25']:.3f}, p50={dist['p50']:.3f}, "
              f"p75={dist['p75']:.3f}, p90={dist['p90']:.3f}")
        print(f"  Cases >=90% determinism: {dist['pct_above_90']:.1f}%")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"\nAnalysis written to {args.output}")


if __name__ == "__main__":
    main()
