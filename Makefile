# =============================================================================
# rv32-ooo  Top-level Makefile
# All EDA tool invocations go through Docker.
# Toolchain versions are frozen in toolchain.lock.
# =============================================================================

SHELL         := bash
.SHELLFLAGS   := -euo pipefail -c
.DEFAULT_GOAL := help

# ── Image names ───────────────────────────────────────────────────────────────
SIM_IMAGE     ?= rv32ooo-sim:g1
FP_IMAGE      ?= rv32ooo-fp:p1
SYN_IMAGE     ?= rv32ooo-syn:g1
ACT_IMAGE     ?= $(SIM_IMAGE)
JOBS          ?= $(shell nproc)
PROXY_CA      ?= $(if $(CODEX_PROXY_CERT),/etc/ssl/certs/ca-certificates.crt,)
ifneq ($(strip $(PROXY_CA)),)
DOCKER_SECRETS = --secret id=proxy_ca,src=$(PROXY_CA)
endif
PROJECT_ROOT  := $(CURDIR)
SIM_BINARY    := build/sim/rv32_ooo_sim
RTL_FILES     := $(shell cat sim/scripts/rv32_ooo_core.f)
SIM_SOURCES   := sim/tb/sim_main.cpp sim/tb/sim_mem.cpp $(wildcard sim/tb/*.h)

# Keep buildx state writable without replacing Docker's registry configuration.
export BUILDX_CONFIG ?= $(PROJECT_ROOT)/build/buildx

# ── Docker run common flags ───────────────────────────────────────────────────
DOCKER_RUN    := docker run --rm \
                  --user $(shell id -u):$(shell id -g) \
                  -v $(PROJECT_ROOT):/workspace \
                  -w /workspace

# Interactive docker run (adds -it)
DOCKER_IT     := docker run --rm -it \
                  --user $(shell id -u):$(shell id -g) \
                  -v $(PROJECT_ROOT):/workspace \
                  -w /workspace

# ─────────────────────────────────────────────────────────────────────────────
# BUILD CONTAINERS
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: docker-build-sim
docker-build-sim: ## Build the simulation/verification Docker image
	docker build \
	  $(DOCKER_SECRETS) \
	  --build-arg NJOBS=$(JOBS) \
	  -t $(SIM_IMAGE) \
	  containers/rv32ooo/
	@echo "✓ $(SIM_IMAGE) built"

.PHONY: docker-build-syn
docker-build-syn: ## Build the synthesis Docker image
	docker build \
	  $(DOCKER_SECRETS) \
	  -t $(SYN_IMAGE) \
	  containers/rv32ooo-syn/
	@echo "✓ $(SYN_IMAGE) built"

.PHONY: docker-build-fp
docker-build-fp: ## Build the optional RV32IMF benchmark toolchain image (requires SIM_IMAGE)
	docker build \
	  $(DOCKER_SECRETS) \
	  --build-arg SIM_BASE_IMAGE=$(SIM_IMAGE) \
	  -t $(FP_IMAGE) \
	  containers/rv32ooo-fp/
	@echo "✓ $(FP_IMAGE) built"

.PHONY: docker-build
docker-build: docker-build-sim docker-build-syn ## Build both Docker images

.PHONY: deps-init check-env check-signoff-env
deps-init: ## Fetch benchmark and ACT4 submodules at the tracked commits
	git submodule update --init --depth 1 -- software/embench/embench-iot verification/act4/riscv-arch-test

check-env: ## Check Docker, tool images and pinned source dependencies
	SIM_IMAGE=$(SIM_IMAGE) SYN_IMAGE=$(SYN_IMAGE) bash scripts/check_environment.sh

check-signoff-env: ## Also check the ACT4 reference-model/generator tools
	SIM_IMAGE=$(SIM_IMAGE) SYN_IMAGE=$(SYN_IMAGE) ACT_IMAGE=$(ACT_IMAGE) bash scripts/check_environment.sh --signoff

.PHONY: check-fp-env
check-fp-env: ## Check the separate RV32IMF/ilp32f workload toolchain
	$(DOCKER_RUN) $(FP_IMAGE) -c 'set -eu; \
	  test "$$(riscv-none-elf-gcc -march=rv32imf_zicsr -mabi=ilp32f -print-multi-directory)" = rv32imf_zicsr/ilp32f; \
	  test -f "$$(riscv-none-elf-gcc -march=rv32imf_zicsr -mabi=ilp32f -print-file-name=libm.a)"; \
	  riscv-none-elf-gcc --version | head -1'

.PHONY: check-fp-sources fetch-fp-sources
check-fp-sources: ## Verify pinned CMSIS-DSP, KissFFT and PolyBench sources
	python3 scripts/prepare_fp_sources.py

fetch-fp-sources: ## Fetch missing FP32 sources, then verify their pinned identities
	python3 scripts/prepare_fp_sources.py --fetch

.PHONY: qualify-embench-fp-reference qualify-embench-fp-dut check-minver-fp
qualify-embench-fp-reference: check-fp-env ## Build and self-check all 19 programs on Spike
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/qualify_embench_candidates.py --toolchain fp --suite full --run-spike'

qualify-embench-fp-dut: check-fp-env sim-build ## Also run all 19 programs on the current DUT (diagnostic)
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/qualify_embench_candidates.py --toolchain fp --suite full --run-spike --run-dut'

check-minver-fp: check-fp-env sim-build ## Regress the FP-store workload against native, Spike and DUT
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/qualify_embench_candidates.py --toolchain fp --suite full --bench minver --run-spike --run-dut'

.PHONY: qualify-fp-fir-pilot
qualify-fp-fir-pilot: check-fp-env check-fp-sources sim-build ## Probe one provisional FIR fixture on native, Spike and DUT
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/qualify_fp_fir_pilot.py --run-dut'

.PHONY: qualify-fp-balanced-reference qualify-fp-balanced-dut
qualify-fp-balanced-reference: check-fp-env check-fp-sources ## Numerically probe all eight provisional FP32 cases on host and Spike
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/qualify_fp_balanced.py'

qualify-fp-balanced-dut: check-fp-env check-fp-sources sim-build ## Also validate every FP32 output on the DUT
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/qualify_fp_balanced.py --run-dut'

.PHONY: check-lsu-interface
check-lsu-interface: check-fp-env sim-build compile-tests ## Check request backpressure and precise load/store access faults with assertions
	$(DOCKER_RUN) $(FP_IMAGE) -c 'SIM_BUILD_DIR=build/sim-assert SIM_ASSERTIONS=1 bash scripts/build_sim.sh $(JOBS)'
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/check_lsu_interface.py'

.PHONY: check-fma-finite compare-fp-contraction
check-fma-finite: check-fp-env sim-build ## Check exact finite FMA values/flags against integer reference and Spike
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/check_fma_finite.py'

compare-fp-contraction: check-fma-finite check-fp-sources ## Matched off/fast FP32 numerical and retired-FMA comparison
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/compare_fp_contraction.py'

.PHONY: profile-fp-bottlenecks
profile-fp-bottlenecks: compare-fp-contraction ## Diagnose FIR/BiCG instruction removal and retirement gaps
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/profile_fp_bottlenecks.py'

.PHONY: profile-lsu-candidates
profile-lsu-candidates: check-fp-env sim-build ## Profile six qualified cases at response delays 1/2/4 before LSU selection
	$(DOCKER_RUN) $(FP_IMAGE) -c 'python3 scripts/profile_lsu_candidates.py'

.PHONY: summarize-embench-fp-dut
summarize-embench-fp-dut: ## Check complete DUT evidence and list each workload's diagnostic cycles
	python3 scripts/summarize_embench_fp_dut.py

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
	  set -eu; \
	  verilator --version; \
	  test -x /opt/spike/bin/spike; \
	  spike -h; \
	  riscv32-unknown-elf-gcc --version; \
	  python3 --version; \
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
smoke: ## Run sv2v + Yosys hierarchy smoke-test
	$(DOCKER_RUN) $(SYN_IMAGE) -c "bash sim/scripts/yosys_hierarchy_smoke.sh"

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
sim-build: $(SIM_BINARY) ## Build the C++ simulator only when its sources change

$(SIM_BINARY): $(RTL_FILES) $(SIM_SOURCES) scripts/build_sim.sh sim/scripts/rv32_ooo_core.f toolchain.lock containers/rv32ooo/Dockerfile Makefile
	$(DOCKER_RUN) $(SIM_IMAGE) -c "bash scripts/build_sim.sh $(JOBS)"
	@touch $(SIM_BINARY)

# Usage: make sim ELF=build/tests/hello.elf
ELF ?= build/tests/hello.elf
SIM_ARGS ?=

.PHONY: sim
sim: ## Run simulation with specified ELF (set ELF=<path>)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  ./build/sim/rv32_ooo_sim +elf=$(ELF) $(SIM_ARGS) \
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
	$(DOCKER_RUN) $(ACT_IMAGE) -c "\
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
embench-run: sim-build ## Run existing Embench 14-workload subset (EMBENCH_BENCH=<name|all>, EMBENCH_OPT=<-O3|-O2>)
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
	  set -euo pipefail; \
	  bash scripts/compile_coremark.sh 1 VALIDATION_RUN -O2 && \
	  ./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter1.elf +max-cycles=2000000 | tee build/coremark/smoke.log && \
	  python3 scripts/check_coremark_result.py build/coremark/smoke.log --mode development \
	  "

.PHONY: coremark
coremark: sim-build ## Run CoreMark benchmark and compute CoreMark/MHz (set ITER=<N>)
	$(DOCKER_RUN) $(SIM_IMAGE) -c "\
	  set -euo pipefail; \
	  bash scripts/compile_coremark.sh $(ITER) PERFORMANCE_RUN $(OPT) && \
	  ./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter$(ITER).elf +max-cycles=10000000 | tee build/coremark/performance.log && \
	  python3 scripts/check_coremark_result.py build/coremark/performance.log --mode development \
	  "


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHESIS (G15)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: synth
synth: ## Run generic Yosys synthesis and structural checks
	$(DOCKER_RUN) $(SYN_IMAGE) -c "\
	  bash syn/scripts/synth_yosys.sh \
	  "

# ─────────────────────────────────────────────────────────────────────────────
# MASTER SIGNOFF
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: signoff
signoff: ## Run existing regression/archive gates (see docs/STATUS.md for scope)
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "ERROR: Working tree is dirty! 'make signoff' requires a clean git working tree."; \
		git status --short; \
		exit 1; \
	fi
	@echo "Starting master signoff from clean commit $$(git rev-parse HEAD)..."
	SIM_IMAGE=$(SIM_IMAGE) SYN_IMAGE=$(SYN_IMAGE) ACT_IMAGE=$(ACT_IMAGE) JOBS=$(JOBS) bash scripts/run_signoff.sh

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
