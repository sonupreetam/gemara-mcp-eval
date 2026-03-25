/**
 * MCP Evals configuration for gemara-mcp evaluation.
 *
 * Reads server and model settings from environment variables.
 * See .env.example in the project root for available options.
 */
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
    provider: "ollama",
    model: process.env.OLLAMA_MODEL || "qwen2.5:7b",
    baseUrl: process.env.OLLAMA_BASE_URL || "http://localhost:11434",
    temperature: 0,
    metrics: ["accuracy", "completeness", "relevance", "clarity", "reasoning"],
    threshold: 3.5,
  },
};
