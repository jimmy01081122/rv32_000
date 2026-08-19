#!/usr/bin/env bash
"""
scripts/verify_coremark_reproducibility.py — CoreMark Determinism and Reproducibility Verification Engine
Executes N independent CoreMark runs (10 iterations) and verifies cycle-level deterministic reproducibility.
Outputs results/<SHA>/coremark/coremark_reproducibility.json.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}\nOutput:\n{res.stdout}")
    return res.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CoreMark cycle reproducibility across multiple runs")
    parser.add_argument("--runs", type=int, default=5, help="Number of independent runs (default: 5)")
    parser.add_argument("--iterations", type=int, default=10, help="CoreMark iterations per run (default: 10)")
    parser.add_argument("--opt", type=str, default="-O3", help="Compiler optimization flag (default: -O3)")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory for reproducibility report")
    args = parser.parse_args()

    # Get Git SHA
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        git_sha = "uncommitted_reproducibility"

    out_dir = Path(args.out_dir) if args.out_dir else Path(f"results/{git_sha}/coremark")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"      CoreMark Cycle-Accurate Reproducibility Audit ({args.runs} Independent Runs)")
    print(f"      Tested Source SHA : {git_sha}")
    print(f"      Iterations / Run  : {args.iterations} | Optimization: {args.opt}")
    print("=" * 80)

    # 1. Compile CoreMark
    compile_cmd = ["bash", "scripts/compile_coremark.sh", str(args.iterations), "PERFORMANCE_RUN", args.opt]
    print(f"==> Compiling CoreMark binary ({args.iterations} iters, {args.opt})...")
    run_cmd(compile_cmd)

    elf_path = f"build/coremark/coremark_iter{args.iterations}.elf"
    if not os.path.exists(elf_path):
        print(f"ERROR: Compiled ELF {elf_path} not found!")
        return 1

    run_results = []
    benchmark_ticks_list = []
    sim_cycles_list = []
    retired_insns_list = []

    sim_exe = "build/sim/rv32_ooo_sim"

    for r in range(1, args.runs + 1):
        raw_log_path = out_dir / f"coremark_run{r}_iter{args.iterations}.log"
        print(f"  --> Run #{r} of {args.runs}...")
        
        sim_cmd = [sim_exe, f"+elf={elf_path}", "+max-cycles=10000000"]
        proc = subprocess.run(sim_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        raw_output = proc.stdout
        
        with open(raw_log_path, "w", encoding="utf-8") as f:
            f.write(raw_output)

        # Parse output using checker
        checker_cmd = [sys.executable, "scripts/check_coremark_result.py", str(raw_log_path), "--json", "--mode", "development"]
        checker_proc = subprocess.run(checker_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if checker_proc.returncode != 0:
            print(f"ERROR: Run #{r} check_coremark_result failed!\n{checker_proc.stdout}")
            return 1

        try:
            parsed = json.loads(checker_proc.stdout)
        except json.JSONDecodeError:
            print(f"ERROR: Unable to parse JSON from check_coremark_result on Run #{r}")
            return 1

        ticks = parsed["total_ticks"]
        cycles = parsed["sim_cycles"]
        retired = parsed["sim_retired"]
        ipc = parsed["sim_ipc"]
        score = parsed["recomputed_score"]
        crc_match = parsed["crc_match"]

        benchmark_ticks_list.append(ticks)
        sim_cycles_list.append(cycles)
        retired_insns_list.append(retired)

        run_results.append({
            "run_index": r,
            "benchmark_ticks": ticks,
            "sim_cycles": cycles,
            "retired_instructions": retired,
            "ipc": ipc,
            "coremark_mhz": score,
            "crc_match": crc_match,
            "log_file": str(raw_log_path)
        })
        print(f"      [Run {r}] Ticks: {ticks} | Sim Cycles: {cycles} | Retired: {retired} | Score: {score:.4f} CoreMark/MHz | CRC: {'PASS' if crc_match else 'FAIL'}")

    # Check Determinism
    all_ticks_identical = len(set(benchmark_ticks_list)) == 1
    all_cycles_identical = len(set(sim_cycles_list)) == 1
    all_retired_identical = len(set(retired_insns_list)) == 1

    is_deterministic = all_ticks_identical and all_cycles_identical and all_retired_identical

    report = {
        "tested_source_sha": git_sha,
        "compiler_opt": args.opt,
        "iterations_per_run": args.iterations,
        "total_runs": args.runs,
        "deterministic": is_deterministic,
        "all_ticks_identical": all_ticks_identical,
        "all_cycles_identical": all_cycles_identical,
        "all_retired_identical": all_retired_identical,
        "reference_benchmark_ticks": benchmark_ticks_list[0] if benchmark_ticks_list else None,
        "reference_sim_cycles": sim_cycles_list[0] if sim_cycles_list else None,
        "reference_retired_instructions": retired_insns_list[0] if retired_insns_list else None,
        "reference_coremark_mhz": run_results[0]["coremark_mhz"] if run_results else None,
        "runs": run_results
    }

    report_path = out_dir / "coremark_reproducibility.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 80)
    if is_deterministic:
        print(f"  [SUCCESS] 100% Deterministic Reproducibility Confirmed across {args.runs} runs!")
        print(f"  Exact Benchmark Ticks : {benchmark_ticks_list[0]}")
        print(f"  Exact CoreMark / MHz  : {run_results[0]['coremark_mhz']:.4f}")
        print(f"  JSON Evidence Report  : {report_path}")
        print("=" * 80)
        return 0
    else:
        print(f"  [FAIL] Nondeterminism Detected across runs!")
        print(f"  Ticks set : {set(benchmark_ticks_list)}")
        print(f"  Cycles set: {set(sim_cycles_list)}")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
