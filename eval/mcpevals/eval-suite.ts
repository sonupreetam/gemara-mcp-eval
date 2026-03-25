/**
 * MCP Evals evaluation suite for gemara-mcp.
 *
 * Tests all gemara-mcp tools, resources, and prompts using LLM-scored metrics.
 * Each evaluation is scored on accuracy, completeness, relevance, clarity, and reasoning.
 */

import * as fs from "fs";
import * as path from "path";
import { config } from "./evals.config";

interface EvalCase {
  id: string;
  description: string;
  tool: string;
  input: Record<string, unknown>;
  expectedBehavior: string;
}

const CORPUS_DIR = path.resolve(__dirname, "../../corpus");

function loadCorpusInput(filename: string): string {
  const fullPath = path.join(CORPUS_DIR, filename);
  if (fs.existsSync(fullPath)) {
    return fs.readFileSync(fullPath, "utf-8");
  }
  return "";
}

const evalCases: EvalCase[] = [
  // Tool: validate_gemara_artifact
  {
    id: "mce-001",
    description: "Validate a correct ControlCatalog",
    tool: "validate_gemara_artifact",
    input: {
      artifact_content: loadCorpusInput(
        "inputs/tc-001-valid-control-catalog.yaml"
      ),
      definition: "#ControlCatalog",
    },
    expectedBehavior:
      "Should return valid=true with no errors and a success message.",
  },
  {
    id: "mce-002",
    description: "Validate an invalid ControlCatalog with missing group",
    tool: "validate_gemara_artifact",
    input: {
      artifact_content: loadCorpusInput(
        "inputs/tc-002-invalid-missing-group.yaml"
      ),
      definition: "#ControlCatalog",
    },
    expectedBehavior:
      "Should return valid=false with errors mentioning the missing group reference.",
  },
  {
    id: "mce-003",
    description: "Validate a correct ThreatCatalog",
    tool: "validate_gemara_artifact",
    input: {
      artifact_content: loadCorpusInput(
        "inputs/tc-003-valid-threat-catalog.yaml"
      ),
      definition: "#ThreatCatalog",
    },
    expectedBehavior:
      "Should return valid=true with no errors and a success message.",
  },
  {
    id: "mce-004",
    description: "Detect type mismatch when validating wrong schema",
    tool: "validate_gemara_artifact",
    input: {
      artifact_content: loadCorpusInput(
        "inputs/tc-004-invalid-wrong-type.yaml"
      ),
      definition: "#ThreatCatalog",
    },
    expectedBehavior:
      "Should return valid=false because the artifact declares ControlCatalog but is validated against ThreatCatalog.",
  },

  // Resource: gemara://schema/definitions
  {
    id: "mce-010",
    description: "Retrieve schema definitions for latest version",
    tool: "resource:gemara://schema/definitions",
    input: {},
    expectedBehavior:
      "Should return CUE schema definitions including ControlCatalog, ThreatCatalog, and other artifact types.",
  },

  // Resource: gemara://lexicon
  {
    id: "mce-011",
    description: "Retrieve Gemara lexicon",
    tool: "resource:gemara://lexicon",
    input: {},
    expectedBehavior:
      "Should return term definitions for the Gemara security model vocabulary.",
  },
];

async function runEvaluation(): Promise<void> {
  const outputArg = process.argv.find((a) => a.startsWith("--output="));
  const outputPath = outputArg
    ? outputArg.split("=")[1]
    : path.resolve(__dirname, "../../results/mcpevals.json");

  console.log(`MCP Evals: Running ${evalCases.length} evaluations...`);
  console.log(`Server: ${config.mcpServer.name}`);
  console.log(`Model: ${config.evaluation.model}`);

  const results = [];

  for (const evalCase of evalCases) {
    console.log(`  [${evalCase.id}] ${evalCase.description}`);

    // Placeholder: in production this calls the MCP server and scores the response
    results.push({
      id: evalCase.id,
      description: evalCase.description,
      tool: evalCase.tool,
      expectedBehavior: evalCase.expectedBehavior,
      scores: {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        clarity: 0,
        reasoning: 0,
      },
      status: "pending",
      message:
        "Wire up @mcp-evals/core client to execute against live gemara-mcp server.",
    });
  }

  const summary = {
    tool: "mcpevals",
    server: config.mcpServer.name,
    model: config.evaluation.model,
    total: results.length,
    passed: results.filter(
      (r) =>
        Object.values(r.scores as Record<string, number>).every(
          (s) => s >= config.evaluation.threshold
        ) && r.status === "passed"
    ).length,
    results,
  };

  const dir = path.dirname(outputPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(outputPath, JSON.stringify(summary, null, 2));
  console.log(`\nResults written to ${outputPath}`);
}

runEvaluation().catch(console.error);
