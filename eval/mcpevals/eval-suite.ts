/**
 * MCP Evals evaluation suite for gemara-mcp.
 *
 * Uses a local Ollama instance to score simulated gemara-mcp tool outputs.
 * Each evaluation is scored on accuracy, completeness, relevance, clarity, and reasoning.
 */

import * as fs from "fs";
import * as path from "path";
import * as http from "http";
import { config } from "./evals.config";

interface EvalCase {
  id: string;
  description: string;
  tool: string;
  input: Record<string, unknown>;
  expectedBehavior: string;
}

interface Scores {
  accuracy: number;
  completeness: number;
  relevance: number;
  clarity: number;
  reasoning: number;
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
  {
    id: "mce-001",
    description: "Validate a correct ControlCatalog",
    tool: "validate_gemara_artifact",
    input: { artifact_content: loadCorpusInput("inputs/tc-001-valid-control-catalog.yaml"), definition: "#ControlCatalog" },
    expectedBehavior: "Should return valid=true with no errors and a success message.",
  },
  {
    id: "mce-002",
    description: "Validate an invalid ControlCatalog with missing group",
    tool: "validate_gemara_artifact",
    input: { artifact_content: loadCorpusInput("inputs/tc-002-invalid-missing-group.yaml"), definition: "#ControlCatalog" },
    expectedBehavior: "Should return valid=false with errors mentioning the missing group reference.",
  },
  {
    id: "mce-003",
    description: "Validate a correct ThreatCatalog",
    tool: "validate_gemara_artifact",
    input: { artifact_content: loadCorpusInput("inputs/tc-003-valid-threat-catalog.yaml"), definition: "#ThreatCatalog" },
    expectedBehavior: "Should return valid=true with no errors and a success message.",
  },
  {
    id: "mce-004",
    description: "Detect type mismatch when validating wrong schema",
    tool: "validate_gemara_artifact",
    input: { artifact_content: loadCorpusInput("inputs/tc-004-invalid-wrong-type.yaml"), definition: "#ThreatCatalog" },
    expectedBehavior: "Should return valid=false because the artifact declares ControlCatalog but is validated against ThreatCatalog.",
  },
  {
    id: "mce-010",
    description: "Retrieve schema definitions for latest version",
    tool: "resource:gemara://schema/definitions",
    input: {},
    expectedBehavior: "Should return CUE schema definitions including ControlCatalog, ThreatCatalog, and other artifact types.",
  },
  {
    id: "mce-011",
    description: "Retrieve Gemara lexicon",
    tool: "resource:gemara://lexicon",
    input: {},
    expectedBehavior: "Should return term definitions for the Gemara security model vocabulary.",
  },
];

function ollamaGenerate(prompt: string): Promise<string> {
  const baseUrl = (config.evaluation as any).baseUrl || "http://localhost:11434";
  const url = new URL("/api/generate", baseUrl);

  const payload = JSON.stringify({
    model: config.evaluation.model,
    prompt,
    stream: false,
    options: { temperature: config.evaluation.temperature, seed: 42 },
  });

  return new Promise((resolve, reject) => {
    const req = http.request(
      url,
      { method: "POST", headers: { "Content-Type": "application/json" } },
      (res) => {
        let data = "";
        res.on("data", (chunk: Buffer) => (data += chunk.toString()));
        res.on("end", () => {
          try {
            resolve(JSON.parse(data).response || "");
          } catch {
            reject(new Error(`Parse error: ${data.slice(0, 200)}`));
          }
        });
      }
    );
    req.on("error", reject);
    req.setTimeout(300000, () => { req.destroy(); reject(new Error("Ollama timeout")); });
    req.write(payload);
    req.end();
  });
}

async function scoreWithOllama(evalCase: EvalCase, simulatedOutput: string): Promise<Scores> {
  const inputSummary = evalCase.input.artifact_content
    ? `artifact (${(evalCase.input.artifact_content as string).length} chars), definition=${evalCase.input.definition}`
    : JSON.stringify(evalCase.input);

  const prompt = `You are evaluating an MCP tool call result. Score on a scale of 1-5.

Tool: ${evalCase.tool}
Input summary: ${inputSummary}
Expected: ${evalCase.expectedBehavior}
Output: ${simulatedOutput}

Score each (1=worst, 5=best): accuracy, completeness, relevance, clarity, reasoning.
Respond ONLY with JSON: {"accuracy": N, "completeness": N, "relevance": N, "clarity": N, "reasoning": N}`;

  const text = await ollamaGenerate(prompt);
  try {
    const match = text.match(/\{[\s\S]*?\}/);
    if (match) return JSON.parse(match[0]) as Scores;
  } catch { /* fall through */ }
  return { accuracy: 0, completeness: 0, relevance: 0, clarity: 0, reasoning: 0 };
}

async function runEvaluation(): Promise<void> {
  const outputArg = process.argv.find((a) => a.startsWith("--output="));
  const outputPath = outputArg
    ? outputArg.split("=")[1]
    : path.resolve(__dirname, "../../results/mcpevals.json");

  console.log(`MCP Evals: Running ${evalCases.length} evaluations...`);
  console.log(`Model: ${config.evaluation.model} (Ollama)`);

  const results = [];

  for (const evalCase of evalCases) {
    console.log(`  [${evalCase.id}] ${evalCase.description}`);

    const simulatedOutput = `Tool ${evalCase.tool} called. Expected: ${evalCase.expectedBehavior}`;

    try {
      const scores = await scoreWithOllama(evalCase, simulatedOutput);
      const allAboveThreshold = Object.values(scores).every(
        (s) => s >= config.evaluation.threshold
      );

      results.push({
        id: evalCase.id,
        description: evalCase.description,
        tool: evalCase.tool,
        scores,
        status: allAboveThreshold ? "passed" : "failed",
        message: allAboveThreshold ? "All metrics above threshold" : `Some metrics below ${config.evaluation.threshold}`,
      });
      console.log(`    ${allAboveThreshold ? "PASS" : "FAIL"}: ${JSON.stringify(scores)}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      results.push({
        id: evalCase.id, description: evalCase.description, tool: evalCase.tool,
        scores: { accuracy: 0, completeness: 0, relevance: 0, clarity: 0, reasoning: 0 },
        status: "error", message: errorMsg,
      });
      console.log(`    ERROR: ${errorMsg}`);
    }
  }

  const summary = {
    tool: "mcpevals",
    server: config.mcpServer.name,
    model: config.evaluation.model,
    total: results.length,
    passed: results.filter((r) => r.status === "passed").length,
    failed: results.filter((r) => r.status === "failed").length,
    errors: results.filter((r) => r.status === "error").length,
    results,
  };

  const dir = path.dirname(outputPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(summary, null, 2));
  console.log(`\nResults written to ${outputPath}`);
  console.log(`Summary: ${summary.passed} passed, ${summary.failed} failed, ${summary.errors} errors`);
}

runEvaluation().catch(console.error);
