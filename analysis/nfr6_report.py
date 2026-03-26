"""
NFR6 Compliance Report Generator.

Aggregates results from all evaluation tools and produces a structured
report on whether the 90% determinism threshold is met.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


TOOL_NAMES = ["detllm", "deepeval", "mcp-eval", "dfah", "promptfoo"]
NFR6_THRESHOLD = 0.9


def _sanitize_for_json(obj):
    """Replace NaN/Infinity with None so json.dump produces valid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def load_results(results_dir: Path) -> dict:
    results = {}
    for tool in TOOL_NAMES:
        path = results_dir / f"{tool}.json"
        if path.exists():
            with open(path) as f:
                results[tool] = json.load(f)
    return results


def assess_tool(tool: str, data: dict) -> dict:
    """Assess a single tool's contribution to NFR6."""
    assessment = {
        "tool": tool,
        "available": True,
        "determinism_score": None,
        "nfr6_contribution": "unknown",
        "details": {},
    }

    if tool == "detllm":
        passed = data.get("passed", 0)
        total = data.get("total_scenarios", 0)
        if total > 0:
            score = passed / total
            assessment["determinism_score"] = score
            assessment["nfr6_contribution"] = "pass" if score >= NFR6_THRESHOLD else "fail"
            assessment["details"] = {"passed": passed, "total": total, "tier": data.get("config", {}).get("tier", "unknown")}

    elif tool == "dfah":
        score = data.get("overall_determinism", 0)
        assessment["determinism_score"] = score
        assessment["nfr6_contribution"] = "pass" if score >= NFR6_THRESHOLD else "fail"
        assessment["details"] = {
            "trajectory_determinism": data.get("benchmarks", [{}])[0].get("trajectory_determinism_mean", "N/A") if data.get("benchmarks") else "N/A",
            "faithfulness": data.get("overall_faithfulness", "N/A"),
            "correlation": data.get("benchmarks", [{}])[0].get("determinism_faithfulness_correlation", "N/A") if data.get("benchmarks") else "N/A",
        }

    elif tool == "promptfoo":
        results = data.get("results", {}).get("results", [])
        if results:
            passed = sum(1 for r in results if r.get("success", False))
            score = passed / len(results)
            assessment["determinism_score"] = score
            assessment["nfr6_contribution"] = "pass" if score >= NFR6_THRESHOLD else "fail"
            assessment["details"] = {"passed": passed, "total": len(results)}

    elif tool == "deepeval":
        summary = data.get("summary", {})
        passed = summary.get("passed", data.get("passed", 0))
        total = summary.get("total", data.get("total", 0))
        if total > 0:
            score = passed / total
            assessment["determinism_score"] = score
            assessment["nfr6_contribution"] = "pass" if score >= NFR6_THRESHOLD else "fail"
            assessment["details"] = {"passed": passed, "total": total, "note": data.get("note", "")}

    elif tool in ("mcpevals", "mcp-eval"):
        passed = data.get("passed", 0)
        total = data.get("total", data.get("total_scenarios", 0))
        pending = data.get("pending", 0)
        evaluated = total - pending
        if evaluated > 0:
            score = passed / evaluated
            assessment["determinism_score"] = score
            assessment["nfr6_contribution"] = "pass" if score >= NFR6_THRESHOLD else "fail"
            assessment["details"] = {"passed": passed, "evaluated": evaluated, "pending": pending, "total": total}
        elif pending > 0:
            assessment["determinism_score"] = None
            assessment["nfr6_contribution"] = "pending"
            assessment["details"] = {"passed": 0, "evaluated": 0, "pending": pending, "total": total}

    return assessment


def generate_report(results_dir: Path, threshold: float) -> dict:
    results = load_results(results_dir)
    assessments = []

    for tool in TOOL_NAMES:
        if tool in results:
            assessments.append(assess_tool(tool, results[tool]))
        else:
            assessments.append({
                "tool": tool,
                "available": False,
                "determinism_score": None,
                "nfr6_contribution": "not_available",
                "details": {},
            })

    available_scores = [a["determinism_score"] for a in assessments if a["determinism_score"] is not None]

    overall_score = sum(available_scores) / len(available_scores) if available_scores else 0
    nfr6_passed = overall_score >= threshold

    report = {
        "nfr6_report": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "threshold": threshold,
            "overall_determinism_score": overall_score,
            "nfr6_verdict": "PASS" if nfr6_passed else "FAIL",
            "tools_evaluated": len(available_scores),
            "tools_total": len(TOOL_NAMES),
        },
        "per_tool_assessments": assessments,
        "dimensions": {
            "validation_determinism": {
                "description": "validate_gemara_artifact produces identical results for identical inputs",
                "target": 1.0,
            },
            "threat_generation_determinism": {
                "description": "threat_assessment prompt suggests same threats for same component",
                "target": 0.8,
            },
            "control_generation_determinism": {
                "description": "control_catalog prompt suggests same controls for same component",
                "target": 0.8,
            },
        },
    }

    return report


TOOL_DESCRIPTIONS = {
    "dfah": {
        "full_name": "Determinism-Faithfulness Assurance Harness",
        "phase": "Phase 1 (No LLM)",
        "what_it_measures": "Calls gemara-mcp directly via MCP protocol, 20 runs per scenario, and compares outputs for exact/Jaccard/structural match.",
        "dimensions": "Artifact validation, threat mapping, control suggestion",
        "failure_mode": "Output drift between repeated runs of the same input",
    },
    "promptfoo": {
        "full_name": "Promptfoo LLM Regression Suite",
        "phase": "Phase 2 (LLM)",
        "what_it_measures": "Sends prompts to the LLM (ollama qwen2.5:7b) and checks that responses contain expected validation keywords.",
        "dimensions": "Artifact validation (LLM layer)",
        "failure_mode": "LLM response no longer matches expected assertions across model or prompt changes",
    },
    "detllm": {
        "full_name": "detLLM Determinism Measurement",
        "phase": "Phase 2 (LLM)",
        "what_it_measures": "Sends the same prompt to the LLM multiple times and measures output consistency.",
        "dimensions": "Raw LLM output stability",
        "failure_mode": "LLM produces different outputs for identical prompts",
    },
    "deepeval": {
        "full_name": "DeepEval Determinism Evaluation",
        "phase": "Phase 2 (LLM)",
        "what_it_measures": "Pytest-based evaluation using DeepEval metrics for tool selection and validation determinism.",
        "dimensions": "Tool selection, validation correctness",
        "failure_mode": "LLM selects different tools or produces inconsistent judgments",
    },
    "mcp-eval": {
        "full_name": "MCP Eval Scenarios",
        "phase": "Phase 1 (No LLM)",
        "what_it_measures": "End-to-end MCP scenario execution against gemara-mcp, comparing results to golden outputs.",
        "dimensions": "Full MCP surface (tools, resources, prompts)",
        "failure_mode": "MCP server responses diverge from golden reference outputs",
    },
}


def generate_markdown(report: dict, results_dir: Path) -> str:
    """Generate a human-readable markdown summary of the NFR6 report."""
    nfr6 = report["nfr6_report"]
    assessments = report["per_tool_assessments"]
    verdict_icon = "PASS" if nfr6["nfr6_verdict"] == "PASS" else "FAIL"

    lines = [
        "# NFR6 Determinism Compliance Report",
        "",
        f"**Generated:** {nfr6['generated_at']}",
        f"**Threshold:** {nfr6['threshold']:.0%} deterministic outcomes",
        f"**Overall Score:** {nfr6['overall_determinism_score']:.1%}",
        f"**Verdict:** {verdict_icon}",
        f"**Tools Evaluated:** {nfr6['tools_evaluated']}/{nfr6['tools_total']}",
        "",
        "---",
        "",
        "## Per-Tool Results",
        "",
    ]

    evaluated = [a for a in assessments if a["available"] and a["determinism_score"] is not None]
    not_run = [a for a in assessments if not a["available"]]

    for a in evaluated:
        tool = a["tool"]
        desc = TOOL_DESCRIPTIONS.get(tool, {})
        score = a["determinism_score"]
        score_str = f"{score:.1%}"
        status = "PASS" if a["nfr6_contribution"] == "pass" else "FAIL"

        lines.append(f"### {desc.get('full_name', tool)} (`{tool}`)")
        lines.append("")
        lines.append(f"| | |")
        lines.append(f"|---|---|")
        lines.append(f"| **Score** | {score_str} ({status}) |")
        lines.append(f"| **Phase** | {desc.get('phase', 'N/A')} |")
        lines.append(f"| **What it measures** | {desc.get('what_it_measures', 'N/A')} |")
        lines.append(f"| **Dimensions covered** | {desc.get('dimensions', 'N/A')} |")
        lines.append(f"| **Failure mode** | {desc.get('failure_mode', 'N/A')} |")

        details = a.get("details", {})
        if tool == "dfah":
            traj = details.get("trajectory_determinism", "N/A")
            faith = details.get("faithfulness", "N/A")
            traj_str = f"{traj:.1%}" if isinstance(traj, (int, float)) else traj
            faith_str = f"{faith:.1%}" if isinstance(faith, (int, float)) else faith

            dfah_path = results_dir / "dfah.json"
            benchmarks_summary = ""
            if dfah_path.exists():
                with open(dfah_path) as f:
                    dfah_data = json.load(f)
                benchmarks = dfah_data.get("benchmarks", [])
                total_cases = sum(b.get("total_cases", 0) for b in benchmarks)
                runs_per = benchmarks[0].get("runs_per_case", "?") if benchmarks else "?"
                benchmarks_summary = f"{len(benchmarks)} benchmarks, {total_cases} cases, {runs_per} runs each = {total_cases * int(runs_per)} total invocations"

            lines.append("")
            lines.append(f"**Detail:** trajectory determinism {traj_str}, faithfulness {faith_str}")
            if benchmarks_summary:
                lines.append(f"**Coverage:** {benchmarks_summary}")

        elif tool == "promptfoo":
            passed = details.get("passed", 0)
            total = details.get("total", 0)
            lines.append("")
            lines.append(f"**Detail:** {passed}/{total} test assertions passed")

        elif tool == "detllm":
            passed = details.get("passed", 0)
            total = details.get("total", 0)
            tier = details.get("tier", "unknown")
            lines.append("")
            lines.append(f"**Detail:** {passed}/{total} scenarios (tier: {tier})")

        elif tool == "deepeval":
            passed = details.get("passed", 0)
            total = details.get("total", 0)
            lines.append("")
            lines.append(f"**Detail:** {passed}/{total} test cases passed")

        elif tool == "mcp-eval":
            passed = details.get("passed", 0)
            evaluated_count = details.get("evaluated", 0)
            pending = details.get("pending", 0)
            lines.append("")
            lines.append(f"**Detail:** {passed}/{evaluated_count} evaluated, {pending} pending")

        lines.append("")

    if not_run:
        lines.append("## Not Evaluated")
        lines.append("")
        tool_list = ", ".join(
            f"`{a['tool']}` ({TOOL_DESCRIPTIONS.get(a['tool'], {}).get('full_name', a['tool'])})"
            for a in not_run
        )
        lines.append(f"The following tools were not run: {tool_list}.")
        lines.append("")
        lines.append("These can be enabled with `make eval-full` when LLM and MCP infrastructure is available.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## NFR6 Dimensions",
        "",
        "| Dimension | Target | Description |",
        "|---|---|---|",
    ])
    for dim_key, dim in report.get("dimensions", {}).items():
        target = dim.get("target", "N/A")
        target_str = f"{target:.0%}" if isinstance(target, (int, float)) else target
        lines.append(f"| {dim_key.replace('_', ' ').title()} | {target_str} | {dim.get('description', '')} |")

    lines.extend([
        "",
        "---",
        "",
        f"*Machine-readable report: `results/nfr6-report.json`*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate NFR6 compliance report")
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent.parent / "results")
    parser.add_argument("--threshold", type=float, default=NFR6_THRESHOLD)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent / "results" / "nfr6-report.json")
    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"Results directory not found: {args.results_dir}")
        print("Run 'make eval-all' first to generate results.")
        sys.exit(1)

    report = generate_report(args.results_dir, args.threshold)

    report = _sanitize_for_json(report)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    md_path = args.output.with_suffix(".md")
    with open(md_path, "w") as f:
        f.write(generate_markdown(report, args.results_dir))

    nfr6 = report["nfr6_report"]
    print("=" * 60)
    print("NFR6 Compliance Report")
    print("=" * 60)
    print(f"\nGenerated:  {nfr6['generated_at']}")
    print(f"Threshold:  {nfr6['threshold']:.0%}")
    print(f"Score:      {nfr6['overall_determinism_score']:.1%}")
    print(f"Verdict:    {nfr6['nfr6_verdict']}")
    print(f"Tools:      {nfr6['tools_evaluated']}/{nfr6['tools_total']} evaluated")

    print("\nPer-Tool:")
    for a in report["per_tool_assessments"]:
        if not a["available"]:
            print(f"  {a['tool']:<15} {'N/A':>8}  NOT AVAILABLE")
        elif a["nfr6_contribution"] == "pending":
            pending = a["details"].get("pending", 0)
            print(f"  {a['tool']:<15} {'N/A':>8}  PENDING ({pending} scenarios awaiting live execution)")
        else:
            score = a["determinism_score"]
            score_str = f"{score:.1%}" if score is not None else "N/A"
            print(f"  {a['tool']:<15} {score_str:>8}  {a['nfr6_contribution'].upper()}")

    print(f"\nReports written to:")
    print(f"  JSON:     {args.output}")
    print(f"  Markdown: {md_path}")
    return 0 if nfr6["nfr6_verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
