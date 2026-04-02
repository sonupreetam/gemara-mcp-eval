.PHONY: all corpus-validate eval-phase1 eval-phase2 eval-all eval-full eval-detllm eval-deepeval eval-mcpevals eval-mcp-eval eval-dfah eval-promptfoo eval-correctness report report-phase1 report-phase2 clean

-include .env
export

CORPUS_DIR := corpus
EVAL_DIR := eval
ANALYSIS_DIR := analysis
RESULTS_DIR := results
CONTAINER_RUNTIME ?= docker

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
	$(CONTAINER_RUNTIME) compose up -d
	@echo "Waiting for gemara-mcp to be ready..."
	@sleep 3

server-down:
	$(CONTAINER_RUNTIME) compose down

# --- Individual Evaluations ---

eval-detllm: $(RESULTS_DIR)
	@echo "==> Running detLLM determinism measurement..."
	cd $(EVAL_DIR)/detllm && python3 run_detllm.py \
		--corpus ../../$(CORPUS_DIR) \
		--output ../../$(RESULTS_DIR)/detllm.json \
		$(DETLLM_ARGS)
	@echo "==> detLLM complete."

eval-deepeval: $(RESULTS_DIR)
	@echo "==> Running DeepEval determinism evaluation..."
	cd $(EVAL_DIR)/deepeval && python3 -m pytest \
		test_determinism.py \
		--tb=short -q \
		--json-report --json-report-file=../../$(RESULTS_DIR)/deepeval.json
	@echo "==> DeepEval complete."

eval-mcpevals: $(RESULTS_DIR)
	@echo "==> Running MCP Evals..."
	cd $(EVAL_DIR)/mcpevals && npx ts-node eval-suite.ts \
		--output=../../$(RESULTS_DIR)/mcpevals.json
	@echo "==> MCP Evals complete."

eval-mcp-eval: $(RESULTS_DIR)
	@echo "==> Running mcp-eval scenarios..."
	cd $(EVAL_DIR)/mcp-eval && python3 run_mcp_eval.py \
		--corpus ../../$(CORPUS_DIR) \
		--output ../../$(RESULTS_DIR)/mcp-eval.json
	@echo "==> mcp-eval complete."

eval-dfah: $(RESULTS_DIR)
	@echo "==> Running DFAH trajectory determinism harness..."
	cd $(EVAL_DIR)/dfah && python3 harness.py \
		--benchmarks benchmarks/ \
		--output ../../$(RESULTS_DIR)/dfah.json
	@echo "==> DFAH complete."

eval-promptfoo: $(RESULTS_DIR)
	@echo "==> Running Promptfoo determinism suite..."
	cd $(EVAL_DIR)/promptfoo && npx promptfoo eval \
		--output ../../$(RESULTS_DIR)/promptfoo.json
	@echo "==> Promptfoo determinism complete."

eval-correctness: $(RESULTS_DIR)
	@echo "==> Running Promptfoo correctness suite..."
	cd $(EVAL_DIR)/promptfoo && npx promptfoo eval \
		-c promptfooconfig-correctness.yaml \
		--output ../../$(RESULTS_DIR)/promptfoo-correctness.json
	@echo "==> Promptfoo correctness complete."

eval-all: eval-phase1

eval-phase1: eval-dfah eval-mcp-eval

eval-phase2: eval-detllm eval-deepeval eval-mcpevals eval-promptfoo

eval-full: eval-phase1 eval-phase2

# --- Analysis ---

report: $(RESULTS_DIR)
	@echo "==> Generating NFR6 compliance report..."
	@if [ -f $(RESULTS_DIR)/nfr6-phase1-report.json ] && [ -f $(RESULTS_DIR)/nfr6-phase2-report.json ]; then \
		echo "Merging Phase 1 + Phase 2 reports..."; \
		python3 $(ANALYSIS_DIR)/nfr6_report.py \
			--merge \
			--phase1-report $(RESULTS_DIR)/nfr6-phase1-report.json \
			--phase2-report $(RESULTS_DIR)/nfr6-phase2-report.json \
			--output $(RESULTS_DIR)/nfr6-report.json; \
	elif [ -f $(RESULTS_DIR)/nfr6-phase1-report.json ]; then \
		echo "Using Phase 1 report (Phase 2 not run)..."; \
		cp $(RESULTS_DIR)/nfr6-phase1-report.json $(RESULTS_DIR)/nfr6-report.json; \
	else \
		python3 $(ANALYSIS_DIR)/nfr6_report.py \
			--results-dir $(RESULTS_DIR) \
			--threshold 0.9 \
			--output $(RESULTS_DIR)/nfr6-report.json; \
	fi
	@echo "==> NFR6 report: $(RESULTS_DIR)/nfr6-report.json"

report-phase1: $(RESULTS_DIR)
	@echo "==> Generating Phase 1 NFR6 report (output determinism, no LLM)..."
	python3 $(ANALYSIS_DIR)/nfr6_report.py \
		--phase 1 \
		--results-dir $(RESULTS_DIR) \
		--threshold 0.9 \
		--output $(RESULTS_DIR)/nfr6-phase1-report.json
	@echo "==> Phase 1 NFR6 report: $(RESULTS_DIR)/nfr6-phase1-report.json"

report-phase2: $(RESULTS_DIR)
	@echo "==> Generating Phase 2 advisory report (LLM integration quality)..."
	python3 $(ANALYSIS_DIR)/nfr6_report.py \
		--phase 2 \
		--results-dir $(RESULTS_DIR) \
		--output $(RESULTS_DIR)/nfr6-phase2-report.json
	@echo "==> Phase 2 advisory report: $(RESULTS_DIR)/nfr6-phase2-report.json"

compare:
	python3 $(ANALYSIS_DIR)/compare_results.py \
		--results-dir $(RESULTS_DIR)

# --- Helpers ---

$(RESULTS_DIR):
	mkdir -p $(RESULTS_DIR)

clean:
	rm -rf $(RESULTS_DIR)
	@echo "Results cleaned."
