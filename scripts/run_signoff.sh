#!/usr/bin/env bash
# Host-side signoff orchestration: each tool runs in its own toolchain image.
set -euo pipefail
project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
SIM_IMAGE=${SIM_IMAGE:-rv32ooo-sim:g1}
SYN_IMAGE=${SYN_IMAGE:-rv32ooo-syn:g1}
ACT_IMAGE=${ACT_IMAGE:-$SIM_IMAGE}
export SIM_IMAGE SYN_IMAGE ACT_IMAGE

if [ -n "$(git status --porcelain)" ]; then
  echo 'ERROR: Signoff requires a clean committed working tree.' >&2
  git status --short
  exit 1
fi
bash scripts/check_environment.sh --signoff

run_image() {
  local image=$1
  shift
  docker run --rm --pull=never --user "$(id -u):$(id -g)" \
    -v "$project_root:/workspace" -w /workspace --entrypoint '' "$image" "$@"
}
run_sim() { run_image "$SIM_IMAGE" "$@"; }
run_syn() { run_image "$SYN_IMAGE" "$@"; }
run_act() { run_image "$ACT_IMAGE" "$@"; }

GIT_SHA=$(git rev-parse HEAD)
OUT_DIR="results/$GIT_SHA"
ARCHIVE_FILE="results/archive_$GIT_SHA.tar.gz"
if [ -e "$OUT_DIR" ] || [ -e "$ARCHIVE_FILE" ]; then
  echo "ERROR: Existing evidence for $GIT_SHA will not be overwritten: $OUT_DIR" >&2
  exit 1
fi
mkdir -p "$OUT_DIR"/{coremark,embench,act4,spike_diff,synthesis}
printf 'Commit: %s\nUTC: %s\nHost: %s\nGit clean: YES\n' \
  "$GIT_SHA" "$(date -u +%FT%TZ)" "$(uname -srmo)" > "$OUT_DIR/environment.txt"
{
  printf 'SIM_IMAGE=%s\nSYN_IMAGE=%s\nACT_IMAGE=%s\n' "$SIM_IMAGE" "$SYN_IMAGE" "$ACT_IMAGE"
  docker image inspect --format '{{.Id}}' "$SIM_IMAGE" "$SYN_IMAGE" "$ACT_IMAGE"
  run_sim bash -euc 'verilator --version; riscv32-unknown-elf-gcc --version; spike -h; python3 --version'
  run_act sail_riscv_sim --version
  run_syn yosys -V
  run_syn sv2v --numeric-version
} > "$OUT_DIR/tool_versions.txt" 2>&1

# Independent signoff rebuild; everyday make sim-build remains incremental.
rm -rf build/sim build/tests
make sim-build compile-tests
run_sim python3 scripts/test_spike_diff_negative.py | tee "$OUT_DIR/spike_diff/selftest.log"
run_sim python3 scripts/run_spike_diff.py --json | tee "$OUT_DIR/spike_diff/lockstep.log"
cp build/tests/diff_results.json "$OUT_DIR/spike_diff/diff_results.json"
run_act python3 scripts/run_act4.py --json --out-dir "$OUT_DIR/act4" | tee "$OUT_DIR/act4/act4_run.log"

run_sim python3 scripts/verify_coremark_reproducibility.py \
  --runs 5 --iterations 10 --opt=-O3 --out-dir "$OUT_DIR/coremark"
run_sim bash scripts/compile_coremark.sh 26 PERFORMANCE_RUN -O3 1000000
run_sim ./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter26.elf +max-cycles=20000000 \
  > "$OUT_DIR/coremark/coremark_official_26iter.log"
run_sim python3 scripts/check_coremark_result.py "$OUT_DIR/coremark/coremark_official_26iter.log" \
  --json --mode official | tee "$OUT_DIR/coremark/result_official_26iter.json"
run_sim bash scripts/compile_coremark.sh 1 VALIDATION_RUN -O3 1000000
run_sim ./build/sim/rv32_ooo_sim +elf=build/coremark/coremark_iter1.elf +max-cycles=2000000 \
  > "$OUT_DIR/coremark/coremark_iter1.log"
run_sim python3 scripts/check_coremark_result.py "$OUT_DIR/coremark/coremark_iter1.log" \
  --json --mode development | tee "$OUT_DIR/coremark/result_iter1.json"
run_sim python3 scripts/run_embench.py --bench all --opt=-O3 --out-dir "$OUT_DIR/embench" --json \
  | tee "$OUT_DIR/embench/embench_run.log"

run_syn bash syn/scripts/synth_yosys.sh
cp build/syn/{synth.log,rv32_ooo_core_netlist.v,synthesis_summary.json} "$OUT_DIR/synthesis/"
(cd "$OUT_DIR" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
run_sim python3 scripts/check_signoff_acceptance.py "$OUT_DIR"
# Publish an archive only after all acceptance gates pass.
tar -czf "$ARCHIVE_FILE" -C results "$GIT_SHA"
sha256sum "$ARCHIVE_FILE" > "$ARCHIVE_FILE.sha256"
echo "Signoff passed: $OUT_DIR ($ARCHIVE_FILE)"
