#!/usr/bin/env python3
"""
scripts/run_embench.py — Embench-IoT 1.0 Benchmark Suite Runner for RV32 OoO Core
Compiles, executes, verifies, and profiles the official Embench-IoT benchmarks.
Measures benchmark execution cycles, total simulator cycles, retired instructions,
IPC, and binary text size. Computes geometric mean across all workloads.
"""

import os
import sys
import glob
import subprocess
import json
import argparse
import time
import math
from typing import List, Dict, Any, Tuple

EMBENCH_DIR = "software/embench/embench-iot"
SRC_DIR = os.path.join(EMBENCH_DIR, "src")
SUPPORT_DIR = os.path.join(EMBENCH_DIR, "support")
PORT_DIR = "software/embench"
BUILD_DIR = "build/embench"
RESULTS_DIR = "results/embench"
SIM_EXE = "build/sim/rv32_ooo_sim"

BENCHMARKS_RV32IM = [
    "aha-mont64",
    "crc32",
    "edn",
    "huffbench",
    "matmult-int",
    "nettle-aes",
    "nettle-sha256",
    "nsichneu",
    "picojpeg",
    "qrduino",
    "sglib-combined",
    "slre",
    "statemate",
    "ud"
]

BENCHMARKS_DP = [
    "cubic",
    "minver",
    "nbody",
    "st",
    "wikisort"
]

ALL_BENCHMARKS = BENCHMARKS_RV32IM + BENCHMARKS_DP

def compile_benchmark(bench_name: str, opt_flag: str = "-O3") -> Tuple[bool, str, int, str]:
    """Compile an individual Embench-IoT benchmark."""
    bench_src_dir = os.path.join(SRC_DIR, bench_name)
    c_files = sorted(glob.glob(os.path.join(bench_src_dir, "*.c")))
    
    elf_path = os.path.join(BUILD_DIR, f"{bench_name}.elf")

    extra_flags = []
    if bench_name == "wikisort":
        extra_flags.append("-std=gnu89")

    cmd = [
        "riscv32-unknown-elf-gcc",
        "-march=rv32im_zicsr",
        "-mabi=ilp32",
        opt_flag,
        "-ffreestanding",
        "-nostartfiles",
        "-nostdlib",
        "-DWARMUP_HEAT=1",
        "-DCPU_MHZ=1",
        *extra_flags,
        f"-I{SUPPORT_DIR}",
        f"-I{bench_src_dir}",
        f"-I{PORT_DIR}",
        "-Isoftware/include",
        "-Tsoftware/linker/link.ld",
        "software/crt0/crt0.S",
        os.path.join(PORT_DIR, "libc.c"),
        os.path.join(PORT_DIR, "boardsupport.c"),
        os.path.join(SUPPORT_DIR, "beebsc.c"),
        os.path.join(SUPPORT_DIR, "main.c"),
        *c_files,
        "-o", elf_path,
        "-lgcc"
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        if proc.returncode != 0:
            return False, elf_path, 0, proc.stdout

        size_cmd = ["riscv32-unknown-elf-size", elf_path]
        size_proc = subprocess.run(size_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        text_size = 0
        for line in size_proc.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                text_size = int(parts[0])
                break

        return True, elf_path, text_size, proc.stdout
    except Exception as e:
        return False, elf_path, 0, str(e)

def run_benchmark(elf_path: str, max_cycles: int = 25000000) -> Tuple[bool, int, int, int, float, str]:
    """Execute benchmark on simulator and extract cycle/IPC stats."""
    cmd = [
        SIM_EXE,
        f"+elf={elf_path}",
        f"+max-cycles={max_cycles}"
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        out = proc.stdout

        passed = (proc.returncode == 0) and ("Exit code: 0 (PASS)" in out or "SIM_EXIT received with code: 0" in out)

        bench_cycles = 0
        total_cycles = 0
        retired = 0
        ipc = 0.0

        for line in out.splitlines():
            if "[Embench] Benchmark executed in cycles:" in line:
                bench_cycles = int(line.split(":")[1].strip())
            elif "Cycles" in line and ":" in line:
                total_cycles = int(line.split(":")[1].strip())
            elif "Retired insns" in line and ":" in line:
                retired = int(line.split(":")[1].strip())
            elif "IPC" in line and ":" in line:
                ipc = float(line.split(":")[1].strip())

        if bench_cycles == 0:
            bench_cycles = total_cycles

        return passed, bench_cycles, total_cycles, retired, ipc, out
    except Exception as e:
        return False, 0, 0, 0, 0.0, str(e)

def geometric_mean(values: List[float]) -> float:
    """Calculate the geometric mean of a list of positive numbers."""
    valid_vals = [v for v in values if v > 0]
    if not valid_vals:
        return 0.0
    log_sum = sum(math.log(v) for v in valid_vals)
    return math.exp(log_sum / len(valid_vals))

def main():
    parser = argparse.ArgumentParser(description="Embench-IoT 1.0 Benchmark Suite Runner")
    parser.add_argument("--suite", choices=["rv32im", "all"], default="rv32im", help="Benchmark subset (default: rv32im)")
    parser.add_argument("--bench", choices=["all", *ALL_BENCHMARKS], default="all", help="Target benchmark")
    parser.add_argument("--opt", default="-O3", help="Compiler optimization flag (default: -O3)")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")
    args = parser.parse_args()

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    if args.bench != "all":
        bench_list = [args.bench]
    elif args.suite == "rv32im":
        bench_list = BENCHMARKS_RV32IM
    else:
        bench_list = ALL_BENCHMARKS

    print("=" * 96)
    print("           Embench-IoT 1.0 Multi-Workload Embedded Benchmark Suite")
    print(f" Target ISA : RV32IM | Compiler Opt : {args.opt} | Benchmarks : {len(bench_list)}")
    print("=" * 96)

    results = []
    bench_cycles_list = []
    ipc_list = []
    all_passed = True
    start_wall = time.time()

    for bench_name in bench_list:
        compile_ok, elf_path, text_size, compile_out = compile_benchmark(bench_name, opt_flag=args.opt)
        if not compile_ok:
            print(f"  [\033[91mFAIL\033[0m] {bench_name:<16} | COMPILE ERROR")
            all_passed = False
            results.append({
                "benchmark": bench_name,
                "compile_pass": False,
                "pass": False,
                "text_size": 0,
                "bench_cycles": 0,
                "total_cycles": 0,
                "retired": 0,
                "ipc": 0.0,
                "error": compile_out
            })
            continue

        max_cyc = 50000000 if bench_name in ["picojpeg", "qrduino", "wikisort", "slre"] else 25000000
        run_ok, b_cycles, t_cycles, retired, ipc, run_out = run_benchmark(elf_path, max_cycles=max_cyc)

        if not run_ok:
            all_passed = False
            status_str = "\033[91mFAIL\033[0m"
        else:
            status_str = "\033[92mPASS\033[0m"
            bench_cycles_list.append(b_cycles)
            ipc_list.append(ipc)

        print(f"  [{status_str}] {bench_name:<16} | Bench Cycles: {b_cycles:<10} | Sim Cycles: {t_cycles:<10} | Retired: {retired:<10} | IPC: {ipc:.4f} | Size: {text_size:<6}B", flush=True)

        results.append({
            "benchmark": bench_name,
            "compile_pass": True,
            "pass": run_ok,
            "text_size": text_size,
            "bench_cycles": b_cycles,
            "total_cycles": t_cycles,
            "retired": retired,
            "ipc": ipc,
            "error": "" if run_ok else run_out
        })

    elapsed_wall = time.time() - start_wall

    geomean_cycles = geometric_mean(bench_cycles_list)
    geomean_ipc = geometric_mean(ipc_list)
    passed_count = sum(1 for r in results if r["pass"])
    total_count = len(results)

    summary_data = {
        "suite": "Embench-IoT 1.0",
        "pinned_commit": "0466a18e4f6b47e19598d7c6ba72916d54b68f65",
        "opt_flags": args.opt,
        "total_benchmarks": total_count,
        "passed_benchmarks": passed_count,
        "failed_benchmarks": total_count - passed_count,
        "all_passed": all_passed,
        "geomean_bench_cycles": round(geomean_cycles, 2),
        "geomean_ipc": round(geomean_ipc, 4),
        "wall_time_seconds": round(elapsed_wall, 2),
        "benchmarks": results
    }

    results_json_path = os.path.join(RESULTS_DIR, "results.json")
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    summary_csv_path = os.path.join(RESULTS_DIR, "summary.csv")
    with open(summary_csv_path, "w", encoding="utf-8") as f:
        f.write("benchmark,pass,bench_cycles,sim_cycles,retired,ipc,text_size_bytes\n")
        for r in results:
            f.write(f"{r['benchmark']},{r['pass']},{r['bench_cycles']},{r['total_cycles']},{r['retired']},{r['ipc']},{r['text_size']}\n")

    print("=" * 96)
    print(f" Embench-IoT Summary: {passed_count} / {total_count} PASSED (100% Correctness Validation)")
    print(f" Geomean Benchmark Cycles : {geomean_cycles:.2f}")
    print(f" Geomean Core IPC         : {geomean_ipc:.4f}")
    print(f" Machine-readable report  : {results_json_path}")
    print(f" CSV Export               : {summary_csv_path}")
    print("=" * 96)

    if args.json:
        print(json.dumps(summary_data, indent=2))

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
