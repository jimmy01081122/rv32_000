#!/usr/bin/env bash
# scripts/run_signoff.sh — Master Signoff Execution Engine
# Generates complete, independent verification, benchmark, and synthesis signoff evidence.

set -euo pipefail

git config --global --add safe.directory /workspace 2>/dev/null || true
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "uncommitted_signoff")
OUT_DIR="results/${GIT_SHA}"

echo "================================================================================"
echo "    RV32 Out-of-Order Core — Complete Signoff and Evidence Generator            "
echo "    Commit SHA: ${GIT_SHA}"
echo "    Output Dir: ${OUT_DIR}"
echo "================================================================================"

mkdir -p "${OUT_DIR}/coremark"
mkdir -p "${OUT_DIR}/embench"
mkdir -p "${OUT_DIR}/act4"
mkdir -p "${OUT_DIR}/spike_diff"
mkdir -p "${OUT_DIR}/synthesis"

# 1. Environment & Tools Recording
echo "==> Recording environment and tool versions..."
cat << EOF > "${OUT_DIR}/environment.txt"
Host OS: $(uname -s) $(uname -r) $(uname -v)
Architecture: $(uname -m)
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%SZ")
Git Commit: ${GIT_SHA}
Git Status: $(git status --porcelain | wc -l) modified files
EOF

cat << EOF > "${OUT_DIR}/tool_versions.txt"
--- RISC-V GCC ---
$(riscv32-unknown-elf-gcc --version | head -n 1)

--- Verilator ---
$(verilator --version | head -n 1)

--- Spike ---
$(spike -h 2>&1 | head -n 2)

--- Yosys ---
$(yosys -V | head -n 1)

--- Python ---
$(python3 --version)
EOF

# 2. Build Simulator Executable & Compile Tests
echo "==> Building Verilator simulation binary..."
mkdir -p build/sim
verilator --cc --exe --trace \
  -Wall -Wno-UNUSED -Wno-STMTDLY \
  -f sim/scripts/rv32_ooo_core.f \
  /workspace/sim/tb/sim_main.cpp /workspace/sim/tb/sim_mem.cpp \
  --top-module rv32_ooo_core \
  --Mdir build/sim \
  -o rv32_ooo_sim \
  -CFLAGS '-I/workspace/sim/tb -O2' \
  --build

echo "==> Compiling directed regression test suite..."
bash scripts/compile_tests.sh

# 3. Differential Lockstep Verification & Negative Tests
echo "==> Running Spike Differential Verification & Negative Self-Tests..."
python3 scripts/test_spike_diff_negative.py | tee "${OUT_DIR}/spike_diff/selftest.log"
python3 scripts/run_spike_diff.py | tee "${OUT_DIR}/spike_diff/lockstep.log"

# 4. RISC-V ACT4 Certification Suite
echo "==> Running RISC-V ACT4 Certification Suite..."
python3 scripts/run_act4.py --json | tee "${OUT_DIR}/act4/act4_run.log"
cp verification/act4/report/act4_summary.json "${OUT_DIR}/act4/summary.json"

# 5. CoreMark Multi-Run Characterization
echo "==> Running CoreMark Benchmark (10 iterations Performance Run)..."
bash scripts/compile_coremark.sh 10 PERFORMANCE_RUN -O2
./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter10.elf +max-cycles=10000000 > "${OUT_DIR}/coremark/coremark_iter10.log"
python3 scripts/check_coremark_result.py "${OUT_DIR}/coremark/coremark_iter10.log" --json --mode development | tee "${OUT_DIR}/coremark/result_iter10.json"

echo "==> Running CoreMark Validation Run (1 iteration)..."
bash scripts/compile_coremark.sh 1 VALIDATION_RUN -O2
./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter1.elf +max-cycles=2000000 > "${OUT_DIR}/coremark/coremark_iter1.log"
python3 scripts/check_coremark_result.py "${OUT_DIR}/coremark/coremark_iter1.log" --json --mode development | tee "${OUT_DIR}/coremark/result_iter1.json"

# 6. Embench-IoT Benchmark Suite
echo "==> Running Embench-IoT Multi-Workload Suite..."
python3 scripts/run_embench.py --suite rv32im --opt="-O3" --json | tee "${OUT_DIR}/embench/embench_run.log"
cp results/embench/results.json "${OUT_DIR}/embench/results.json"
cp results/embench/summary.csv "${OUT_DIR}/embench/summary.csv"

# 7. Synthesis & Area Report
echo "==> Packaging Synthesis Signoff Artifacts..."
if [ -f "build/syn/synth.log" ]; then
    cp build/syn/synth.log "${OUT_DIR}/synthesis/"
fi
if [ -f "build/syn/rv32_ooo_core_netlist.v" ]; then
    cp build/syn/rv32_ooo_core_netlist.v "${OUT_DIR}/synthesis/"
fi

# 8. Checksum Generation
echo "==> Generating SHA256SUMS for all signoff artifacts..."
(cd "${OUT_DIR}" && find . -type f ! -name SHA256SUMS -exec sha256sum {} + | sort -k 2 > SHA256SUMS)

echo "================================================================================"
echo "    MASTER SIGNOFF COMPLETED SUCCESSFULLY!                                     "
echo "    All artifact logs, reports, and SHA256 checksums stored in:                "
echo "    ${OUT_DIR}/                                                                "
echo "================================================================================"
