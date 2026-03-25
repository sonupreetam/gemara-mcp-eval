/**
 * MCP Evals configuration for gemara-mcp evaluation.
 *
 * Defines the MCP server connection and evaluation parameters.
 */
export const config = {
  mcpServer: {
    name: "gemara-mcp",
    command: "docker",
    args: [
      "run",
      "--rm",
      "-i",
      "ghcr.io/gemaraproj/gemara-mcp:v0.1.0",
      "serve",
      "--mode",
      "artifact",
    ],
  },
  evaluation: {
    model: "gpt-4o",
    temperature: 0,
    seed: 42,
    metrics: ["accuracy", "completeness", "relevance", "clarity", "reasoning"],
    threshold: 3.5, // minimum score out of 5
  },
};
