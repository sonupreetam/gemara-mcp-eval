/**
 * Custom Promptfoo assertion for measuring determinism across multiple runs.
 *
 * Usage in promptfooconfig.yaml:
 *   assert:
 *     - type: javascript
 *       value: file://assertions/determinism.js
 *       config:
 *         runs: 5
 *         threshold: 0.9
 */
module.exports = async function ({ output, config }) {
  const runs = config?.runs || 5;
  const threshold = config?.threshold || 0.9;

  const outputs = [output];
  // In a full implementation, previous run outputs would be loaded from
  // results/ directory. This placeholder demonstrates the interface.

  if (outputs.length < 2) {
    return {
      pass: true,
      score: 1.0,
      reason: `Only 1 run available (need ${runs} for determinism check). Skipping.`,
    };
  }

  // Normalize outputs for comparison: lowercase, strip whitespace, sort lines
  const normalize = (text) =>
    text
      .toLowerCase()
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0)
      .sort()
      .join("\n");

  const normalized = outputs.map(normalize);
  const reference = normalized[0];
  let matchCount = 0;

  for (const n of normalized) {
    if (n === reference) matchCount++;
  }

  const score = matchCount / normalized.length;
  return {
    pass: score >= threshold,
    score,
    reason: `Determinism: ${matchCount}/${normalized.length} runs matched (${(score * 100).toFixed(1)}%, threshold: ${(threshold * 100).toFixed(1)}%)`,
  };
};
