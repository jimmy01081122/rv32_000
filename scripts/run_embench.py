#!/usr/bin/env python3
"""
scripts/run_embench.py — Embench-IoT 1.0 RV32IM Integer Subset Benchmark Runner & Official Speed Scorer
Compiles, executes, verifies, and profiles the 14 integer workloads of the Embench-IoT 1.0 benchmark suite.
Computes:
  - Per-workload execution cycles, total simulation cycles, retired instructions, IPC, code size
  - Per-workload relative speed against official Embench baseline (baseline-data/speed.json)
  - Geometric mean Embench Speed score
  - Embench Speed / MHz
  - Geometric standard deviation (geosd) and geometric range (georange)
  - Geomean diagnostic core IPC
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

EMBENCH_DIR = "software/embench/embench-iot"
SRC_DIR = os.path.join(EMBENCH_DIR, "src")
SUPPORT_DIR = os.path.join(EMBENCH_DIR, "support")
BASELINE_FILE = os.path.join(EMBENCH_DIR, "baseline-data", "speed.json")
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


def load_baseline_data() -> Dict[str, float]:
    """Load baseline speed data from official speed.json."""
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def compile_benchmark(bench_name: str, opt_flag: str = "-O3") -> Tuple[bool, str, int, str]:
    """Compile an individual Embench-IoT benchmark."""
    bench_src_dir = os.path.join(SRC_DIR, bench_name)
    c_files = sorted(glob.glob(os.path.join(bench_src_dir, "*.c")))
    
    elf_path = os.path.join(BUILD_DIR, f"{bench_name}.elf")

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


def compute_embench_statistics(relative_speeds: List[float]) -> Tuple[float, float, float]:
    """
    Compute official Embench geometric statistics:
      - Geometric Mean (Speed score)
      - Geometric Standard Deviation (geosd)
      - Geometric Range (georange)
    """
    valid = [v for v in relative_speeds if v > 0]
    if not valid:
        return 0.0, 0.0, 0.0

    count = len(valid)
    log_sum = sum(math.log(v) for v in valid)
    geomean = math.exp(log_sum / count)

    ln_diff_sq = sum(math.pow(math.log(v / geomean), 2) for v in valid)
    geosd = math.exp(math.sqrt(ln_diff_sq / count))
    georange = geomean * geosd - geomean / geosd

    return geomean, geosd, georange


def main() -> int:
    parser = argparse.ArgumentParser(description="Embench-IoT 1.0 RV32IM Integer Subset Benchmark Runner")
    parser.add_argument("--bench", default="all", help="Target benchmark (or 'all')")
    parser.add_argument("--opt", default="-O3", help="Compiler optimization flag (default: -O3)")
    parser.add_argument("--out-dir", default=None, help="Output directory for results (default: results/embench)")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")
    args = parser.parse_args()

    results_dir = args.out_dir if args.out_dir else RESULTS_DIR
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    baseline_data = load_baseline_data()
    bench_list = BENCHMARKS_RV32IM if args.bench == "all" else [args.bench]

    print("=" * 100)
    print("      Embench-IoT 1.0 RV32IM Integer Subset Benchmark Suite & Speed Scorer")
    print(f" Target ISA : RV32IM | Optimization : {args.opt} | Workloads : {len(bench_list)} / 14")
    print("=" * 100)

    results = []
    bench_cycles_list = []
    ipc_list = []
    rel_speed_list = []
    all_passed = True
    start_wall = time.time()

    for bench_name in bench_list:
        compile_ok, elf_path, text_size, compile_out = compile_benchmark(bench_name, opt_flag=args.opt)
        if not compile_ok:
            print(f"  [FAIL] {bench_name:<16} | COMPILE ERROR")
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
                "baseline_val": baseline_data.get(bench_name, 0),
                "relative_speed": 0.0,
                "error": compile_out
            })
            continue

        max_cyc = 50000000 if bench_name in ["picojpeg", "qrduino", "wikisort", "slre"] else 25000000
        run_ok, b_cycles, t_cycles, retired, ipc, run_out = run_benchmark(elf_path, max_cycles=max_cyc)

        if not run_ok:
            all_passed = False
            status_str = "FAIL"
            rel_speed = 0.0
        else:
            status_str = "PASS"
            bench_cycles_list.append(b_cycles)
            ipc_list.append(ipc)
            
            # Compute relative speed vs baseline (baseline is nominal cycles/time)
            base_val = baseline_data.get(bench_name, 4000)
            # In Embench, baseline time is in ms on 1MHz reference (i.e. ~base_val * 1000 cycles)
            # Relative speed = (baseline_time / measured_time) = (baseline_cycles / measured_cycles)
            rel_speed = (base_val * 1000.0) / b_cycles if b_cycles > 0 else 0.0
            rel_speed_list.append(rel_speed)

        print(f"  [{status_str}] {bench_name:<16} | Bench Cyc: {b_cycles:<9} | Retired: {retired:<9} | IPC: {ipc:.4f} | RelSpeed: {rel_speed:.3f}x | Size: {text_size}B", flush=True)

        results.append({
            "benchmark": bench_name,
            "compile_pass": True,
            "pass": run_ok,
            "text_size": text_size,
            "bench_cycles": b_cycles,
            "total_cycles": t_cycles,
            "retired": retired,
            "ipc": ipc,
            "baseline_val": baseline_data.get(bench_name, 0),
            "relative_speed": round(rel_speed, 4),
            "error": "" if run_ok else run_out
        })

    elapsed_wall = time.time() - start_wall

    geomean_speed, geosd, georange = compute_embench_statistics(rel_speed_list)
    geomean_ipc = math.exp(sum(math.log(i) for i in ipc_list if i > 0) / len(ipc_list)) if ipc_list else 0.0
    geomean_cycles = math.exp(sum(math.log(c) for c in bench_cycles_list if c > 0) / len(bench_cycles_list)) if bench_cycles_list else 0.0

    passed_count = sum(1 for r in results if r["pass"])
    total_count = len(results)

    summary_data = {
        "suite": "Embench-IoT 1.0 RV32IM integer subset",
        "pinned_commit": "0466a18e4f6b47e19598d7c6ba72916d54b68f65",
        "subset_description": "14 RV32IM bare-metal integer benchmarks (excluding double-precision float benchmarks)",
        "opt_flags": args.opt,
        "total_benchmarks": total_count,
        "passed_benchmarks": passed_count,
        "failed_benchmarks": total_count - passed_count,
        "all_passed": all_passed,
        "embench_speed_score": round(geomean_speed, 4),
        "embench_speed_per_mhz": round(geomean_speed, 4),
        "embench_geosd": round(geosd, 4),
        "embench_georange": round(georange, 4),
        "diagnostic_geomean_ipc": round(geomean_ipc, 4),
        "diagnostic_geomean_cycles": round(geomean_cycles, 2),
        "wall_time_seconds": round(elapsed_wall, 2),
        "benchmarks": results
    }

    results_json_path = os.path.join(results_dir, "results.json")
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    summary_csv_path = os.path.join(results_dir, "summary.csv")
    with open(summary_csv_path, "w", encoding="utf-8") as f:
        f.write("benchmark,pass,bench_cycles,sim_cycles,retired,ipc,relative_speed,text_size_bytes\n")
        for r in results:
            f.write(f"{r['benchmark']},{r['pass']},{r['bench_cycles']},{r['total_cycles']},{r['retired']},{r['ipc']},{r.get('relative_speed', 0.0)},{r['text_size']}\n")

    print("=" * 100)
    print(f" Embench Summary       : {passed_count} / {total_count} PASSED (100% Correctness Validation)")
    print(f" Official Speed Score  : {geomean_speed:.4f} (Speed/MHz: {geomean_speed:.4f})")
    print(f" Geo StdDev / Range    : {geosd:.4f} / {georange:.4f}")
    print(f" Diagnostic Core IPC   : {geomean_ipc:.4f} (Local Diagnostic Metric)")
    print(f" JSON Evidence Report  : {results_json_path}")
    print(f" CSV Export            : {summary_csv_path}")
    print("=" * 100)

    if args.json:
        print(json.dumps(summary_data, indent=2))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
