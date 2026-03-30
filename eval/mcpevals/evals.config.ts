/**
 * MCP Evals configuration for gemara-mcp evaluation.
 *
 * Reads server and model settings from environment variables.
 * Supports Ollama, Vertex AI, and OpenAI as LLM backends.
 *
 * Provider resolution order:
 *   1. LLM_PROVIDER env var (explicit)
 *   2. Ollama (if OLLAMA_BASE_URL / OLLAMA_MODEL set)
 *   3. Vertex AI (if VERTEX_PROJECT set)
 *   4. OpenAI (if OPENAI_API_KEY set)
 *   5. Default: Ollama at localhost:11434
 */

function resolveEvalProvider(): {
  baseUrl: string;
  apiKey: string;
  model: string;
  provider: string;
} {
  const explicit = (process.env.LLM_PROVIDER || "").toLowerCase();

  if (explicit === "openai" || (!explicit && process.env.OPENAI_API_KEY)) {
    return {
      provider: "openai",
      baseUrl: "https://api.openai.com/v1",
      apiKey: process.env.OPENAI_API_KEY || "",
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
    };
  }

  if (explicit === "vertex_ai" || (!explicit && process.env.VERTEX_PROJECT)) {
    const project = process.env.VERTEX_PROJECT || "";
    const location = process.env.VERTEX_LOCATION || "us-central1";
    const model = process.env.VERTEX_MODEL || "gemini-2.0-flash";
    return {
      provider: "vertex_ai",
      baseUrl: `https://${location}-aiplatform.googleapis.com/v1/projects/${project}/locations/${location}/endpoints/openapi`,
      apiKey: process.env.GOOGLE_API_KEY || "vertex",
      model,
    };
  }

  // Default: Ollama (OpenAI-compatible endpoint)
  const ollamaBase = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
  return {
    provider: "ollama",
    baseUrl: `${ollamaBase}/v1`,
    apiKey: "ollama",
    model: process.env.OLLAMA_MODEL || "qwen2.5:7b",
  };
}

const evalProvider = resolveEvalProvider();

export const config = {
  mcpServer: {
    name: "gemara-mcp",
    command: process.env.CONTAINER_RUNTIME || "docker",
    args: [
      "run",
      "--rm",
      "-i",
      process.env.GEMARA_MCP_IMAGE || "ghcr.io/gemaraproj/gemara-mcp:v0.1.0",
      "serve",
      "--mode",
      process.env.GEMARA_MCP_MODE || "artifact",
    ],
  },
  evaluation: {
    provider: evalProvider.provider,
    model: evalProvider.model,
    baseUrl: evalProvider.baseUrl,
    apiKey: evalProvider.apiKey,
    temperature: 0,
    metrics: ["accuracy", "completeness", "relevance", "clarity", "reasoning"],
    threshold: 3.5,
  },
};
