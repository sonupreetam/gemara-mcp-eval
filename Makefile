.PHONY: all corpus-validate eval-all eval-detllm eval-deepeval eval-mcpevals eval-mcp-eval eval-dfah eval-promptfoo report clean

CORPUS_DIR := corpus
EVAL_DIR := eval
ANALYSIS_DIR := analysis
RESULTS_DIR := results

all: eval-all report

# --- Corpus ---

corpus-validate:
	@echo "==> Validating test corpus inputs against Gemara CUE schemas..."
	@for f in $(CORPUS_DIR)/inputs/tc-*-valid-*.yaml; do \
		echo "  Validating $$f"; \
		cue vet reference/gemara/layer-2.cue "$$f" 2>/dev/null || \
		cue vet reference/gemara/layer-3.cue "$$f" 2>/dev/null || \
		echo "  WARN: $$f did not match any layer schema"; \
	done
	@echo "==> Corpus validation complete."

# --- Infrastructure ---

server-up:
	docker compose up -d
	@echo "Waiting for gemara-mcp to be ready..."
	@sleep 3

server-down:
	docker compose down

# --- Individual Evaluations ---

eval-detllm: $(RESULTS_DIR)
	@echo "==> Running detLLM determinism measurement..."
	cd $(EVAL_DIR)/detllm && python run_detllm.py \
		--corpus ../../$(CORPUS_DIR) \
		--output ../../$(RESULTS_DIR)/detllm.json
	@echo "==> detLLM complete."

eval-deepeval: $(RESULTS_DIR)
	@echo "==> Running DeepEval MCP evaluation..."
	cd $(EVAL_DIR)/deepeval && python -m pytest \
		test_tool_selection.py test_determinism.py \
		--tb=short -q \
		--json-report=../../$(RESULTS_DIR)/deepeval.json
	@echo "==> DeepEval complete."

eval-mcpevals: $(RESULTS_DIR)
	@echo "==> Running MCP Evals..."
	cd $(EVAL_DIR)/mcpevals && npx ts-node eval-suite.ts \
		--output ../../$(RESULTS_DIR)/mcpevals.json
	@echo "==> MCP Evals complete."

eval-mcp-eval: $(RESULTS_DIR)
	@echo "==> Running mcp-eval scenarios..."
	cd $(EVAL_DIR)/mcp-eval && python run_mcp_eval.py \
		--corpus ../../$(CORPUS_DIR) \
		--output ../../$(RESULTS_DIR)/mcp-eval.json
	@echo "==> mcp-eval complete."

eval-dfah: $(RESULTS_DIR)
	@echo "==> Running DFAH trajectory determinism harness..."
	cd $(EVAL_DIR)/dfah && python harness.py \
		--benchmarks benchmarks/ \
		--output ../../$(RESULTS_DIR)/dfah.json
	@echo "==> DFAH complete."

eval-promptfoo: $(RESULTS_DIR)
	@echo "==> Running Promptfoo regression suite..."
	cd $(EVAL_DIR)/promptfoo && npx promptfoo eval \
		--output ../../$(RESULTS_DIR)/promptfoo.json
	@echo "==> Promptfoo complete."

eval-all: eval-detllm eval-deepeval eval-mcpevals eval-mcp-eval eval-dfah eval-promptfoo

# --- Analysis ---

report: $(RESULTS_DIR)
	@echo "==> Generating NFR6 compliance report..."
	python $(ANALYSIS_DIR)/nfr6_report.py \
		--results-dir $(RESULTS_DIR) \
		--threshold 0.9 \
		--output $(RESULTS_DIR)/nfr6-report.json
	@echo "==> NFR6 report: $(RESULTS_DIR)/nfr6-report.json"

compare:
	python $(ANALYSIS_DIR)/compare_results.py \
		--results-dir $(RESULTS_DIR)

# --- Helpers ---

$(RESULTS_DIR):
	mkdir -p $(RESULTS_DIR)

clean:
	rm -rf $(RESULTS_DIR)
	@echo "Results cleaned."
