# =============================================================================
# rv32-ooo  Top-level Makefile
# All EDA tool invocations go through Docker.
# Toolchain versions are frozen in toolchain.lock.
# =============================================================================

SHELL         := bash
.SHELLFLAGS   := -euo pipefail -c
.DEFAULT_GOAL := help

# ── Image names ───────────────────────────────────────────────────────────────
SIM_IMAGE     := rv32ooo-sim:g1
SYN_IMAGE     := rv32ooo-syn:g1
PROJECT_ROOT  := $(CURDIR)

# ── Docker run common flags ───────────────────────────────────────────────────
DOCKER_RUN    := docker run --rm \
                  -v $(PROJECT_ROOT):/workspace \
                  -w /workspace \
                  -e HOME=/tmp

# Interactive docker run (adds -it)
DOCKER_IT     := docker run --rm -it \
                  -v $(PROJECT_ROOT):/workspace \
                  -w /workspace \
                  -e HOME=/tmp

# ─────────────────────────────────────────────────────────────────────────────
# BUILD CONTAINERS
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: docker-build-sim
docker-build-sim: ## Build the simulation/verification Docker image
	docker build \
	  --build-arg NJOBS=$$(nproc) \
	  -t $(SIM_IMAGE) \
	  containers/rv32ooo/
	@echo "✓ $(SIM_IMAGE) built"

.PHONY: docker-build-syn
docker-build-syn: ## Build the synthesis Docker image
	docker build \
	  --build-arg NJOBS=$$(nproc) \
	  -t $(SYN_IMAGE) \
	  containers/rv32ooo-syn/
	@echo "✓ $(SYN_IMAGE) built"

.PHONY: docker-build
docker-build: docker-build-sim docker-build-syn ## Build both Docker images

# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE SHELLS
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: sim-shell
sim-shell: ## Launch interactive shell in simulation container
	$(DOCKER_IT) $(SIM_IMAGE)

.PHONY: syn-shell
syn-shell: ## Launch interactive shell in synthesis container
	$(DOCKER_IT) $(SYN_IMAGE)

# ─────────────────────────────────────────────────────────────────────────────
# TOOL VERSION CHECKS
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: check-tools
check-tools: ## Verify all tool versions in simulation container
	@echo "=== Simulation container tool versions ==="
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  echo '--- Verilator ---'  && verilator --version; \
	  echo '--- Yosys ---'      && yosys -V; \
	  echo '--- Spike ---'      && (spike -h 2>&1 || true); \
	  echo '--- RISC-V GCC ---' && riscv32-unknown-elf-gcc --version; \
	  echo '--- Python ---'     && python3 --version; \
	  echo '--- pyelftools ---' && python3 -c 'import elftools; print(elftools.__version__)'; \
	"

.PHONY: check-syn-tools
check-syn-tools: ## Verify tool versions in synthesis container
	@echo "=== Synthesis container tool versions ==="
	$(DOCKER_RUN) $(SYN_IMAGE) -c "\
	  echo '--- Yosys ---' && yosys -V; \
	"

# ─────────────────────────────────────────────────────────────────────────────
# RTL HIERARCHY SMOKE TEST  (G1 exit criterion)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: smoke
smoke: ## Run Yosys hierarchy smoke-test (G1 exit criterion)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "bash sim/scripts/yosys_hierarchy_smoke.sh"

# ─────────────────────────────────────────────────────────────────────────────
# VERILATOR ELABORATION / LINT
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Verilator --lint-only on all RTL
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  verilator --lint-only \
	    -Wall \
	    -Wno-UNUSED -Wno-STMTDLY \
	    -f sim/scripts/rv32_ooo_core.f \
	    --top-module rv32_ooo_core \
	  "

.PHONY: elab
elab: ## Full Verilator elaboration (minimal SV testbench)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  verilator --cc \
	    -Wall \
	    -Wno-UNUSED -Wno-STMTDLY \
	    -f sim/scripts/rv32_ooo_core.f \
	    sim/tb/rv32_ooo_core_tb.sv \
	    --top-module rv32_ooo_core_tb \
	    --build \
	    -Mdir build/verilator_elab \
	  "

# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION PLATFORM (G2)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: sim-build
sim-build: ## Build the C++ Verilator simulator binary (G2 platform)
	mkdir -p build/sim
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  verilator --cc --exe --trace \
	    -Wall -Wno-UNUSED -Wno-STMTDLY \
	    -f sim/scripts/rv32_ooo_core.f \
	    /workspace/sim/tb/sim_main.cpp /workspace/sim/tb/sim_mem.cpp \
	    --top-module rv32_ooo_core \
	    --Mdir build/sim \
	    -o rv32_ooo_sim \
	    -CFLAGS '-I/workspace/sim/tb -O2' \
	    --build \
	"

# Usage: make sim ELF=build/tests/hello.elf
ELF ?= build/tests/hello.elf

.PHONY: sim
sim: ## Run simulation with specified ELF (set ELF=<path>)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  ./build/sim/rv32_ooo_sim +elf=$(ELF) \
	  "

# ─────────────────────────────────────────────────────────────────────────────
# COMPILE RISC-V TEST PROGRAMS
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: compile-tests
compile-tests: ## Cross-compile directed tests (bare-metal elf)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  bash scripts/compile_tests.sh \
	  "

.PHONY: test
test: sim-build compile-tests ## Run full regression test suite
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  bash scripts/run_all_tests.sh \
	  "

.PHONY: diff-test
diff-test: sim-build compile-tests ## Run architectural signoff / commit trace verification
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  python3 scripts/run_spike_diff.py \
	  "

.PHONY: diff-selftest
diff-selftest: ## Run differential verification negative self-tests
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  python3 scripts/test_spike_diff_negative.py \
	  "

# ─────────────────────────────────────────────────────────────────────────────
# RISC-V ARCHITECTURAL CERTIFICATION (ACT4)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: act4-build
act4-build: sim-build ## Prepare ACT4 framework and configurations

.PHONY: act4-run
act4-run: sim-build ## Run full RISC-V ACT4 certification suite (RV32I, RV32M, Zicsr)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  python3 scripts/run_act4.py \
	  "

.PHONY: act4-report
act4-report: ## Display ACT4 certification summary report
	cat verification/act4/report/act4_summary.json

# ─────────────────────────────────────────────────────────────────────────────
# EMBENCH-IOT 1.0 BENCHMARK SUITE
# ─────────────────────────────────────────────────────────────────────────────

EMBENCH_BENCH ?= all
EMBENCH_OPT ?= -O3

.PHONY: embench-run
embench-run: sim-build ## Run Embench-IoT suite (set EMBENCH_BENCH=<name|all>, EMBENCH_OPT=<-O3|-O2>)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  python3 scripts/run_embench.py --bench $(EMBENCH_BENCH) --opt=\"$(EMBENCH_OPT)\" \
	  "

.PHONY: embench-report
embench-report: ## Display Embench-IoT results report
	cat results/embench/results.json

# ─────────────────────────────────────────────────────────────────────────────
# COREMARK BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

ITER ?= 10
RUN_TYPE ?= PERFORMANCE_RUN
OPT ?= -O2

.PHONY: coremark-compile
coremark-compile: ## Cross-compile official EEMBC CoreMark (set ITER=<N>, RUN_TYPE=<PERFORMANCE_RUN|VALIDATION_RUN>)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  bash scripts/compile_coremark.sh $(ITER) $(RUN_TYPE) $(OPT) \
	  "

.PHONY: coremark-smoke
coremark-smoke: sim-build ## Run CoreMark smoke test (1 iteration, validation run)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  bash scripts/compile_coremark.sh 1 VALIDATION_RUN -O2 && \
	  ./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter1.elf +max-cycles=2000000 \
	  "

.PHONY: coremark
coremark: sim-build ## Run CoreMark benchmark and compute CoreMark/MHz (set ITER=<N>)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  bash scripts/compile_coremark.sh $(ITER) PERFORMANCE_RUN $(OPT) && \
	  ./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter$(ITER).elf +max-cycles=10000000 \
	  "


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHESIS (G15)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: synth
synth: ## Run full Yosys synthesis flow (Milestone G15)
	$(DOCKER_RUN) $(SYN_IMAGE) -c "\
	  bash syn/scripts/synth_yosys.sh \
	  "

# ─────────────────────────────────────────────────────────────────────────────
# MASTER SIGNOFF
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: signoff
signoff: ## Execute complete multi-benchmark, certification, and synthesis signoff
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "ERROR: Working tree is dirty! 'make signoff' requires a clean git working tree."; \
		git status --short; \
		exit 1; \
	fi
	@echo "Starting master signoff from clean commit $$(git rev-parse HEAD)..."
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  bash scripts/run_signoff.sh \
	  "

# ─────────────────────────────────────────────────────────────────────────────
# CLEAN
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove all build artifacts
	rm -rf build/

.PHONY: docker-clean
docker-clean: ## Remove rv32ooo Docker images
	-docker rmi $(SIM_IMAGE) $(SYN_IMAGE)

# ─────────────────────────────────────────────────────────────────────────────
# HELP
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@echo ""
	@echo "rv32-ooo Makefile — all tools run inside Docker"
	@echo ""
	@echo "Quick start:"
	@echo "  make docker-build-sim    # build simulation container"
	@echo "  make check-tools         # verify tool versions inside Docker"
	@echo "  make lint                # Verilator lint"
	@echo "  make compile-tests       # Cross-compile bare-metal test programs"
	@echo "  make sim-build           # Build C++ simulator executable"
	@echo "  make sim ELF=<path>      # Run bare-metal ELF simulation"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf ""} \
	      /^[a-zA-Z0-9_-]+:.*?##/ { printf "  %-24s %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)
	@echo ""
