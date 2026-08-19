#!/usr/bin/env python3
"""
scripts/run_act4.py — RISC-V Architectural Certification Test (ACT4) Suite Runner
Compiles and executes the official RISC-V Architectural Certification Tests (ACT4)
on both DUT (rv32_ooo_sim) and Reference Simulator (Spike).
Collects machine-readable JSON metrics and verification report.
"""

import os
import sys
import glob
import subprocess
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

ACT4_ROOT = "verification/act4/riscv-arch-test"
DUT_CONFIG_DIR = "verification/act4/rv32_ooo"
BUILD_DIR = "build/act4"
REPORT_DIR = "verification/act4/report"
SIM_EXE = "build/sim/rv32_ooo_sim"

SUITES = {
    "RV32I": os.path.join(ACT4_ROOT, "tests/rv32i/I"),
    "RV32M": os.path.join(ACT4_ROOT, "tests/rv32i/M"),
    "Zicsr": os.path.join(ACT4_ROOT, "tests/rv32i/Zicsr"),
}

def compile_act_test(src_path: str, elf_path: str) -> Tuple[bool, str]:
    """Compile an ACT test assembly file into a bare-metal ELF."""
    test_file_name = os.path.basename(src_path)
    cmd = [
        "riscv32-unknown-elf-gcc",
        "-march=rv32im_zicsr",
        "-mabi=ilp32",
        "-static",
        "-mcmodel=medany",
        "-fvisibility=hidden",
        "-nostdlib",
        "-nostartfiles",
        f"-I{ACT4_ROOT}/tests/env",
        f"-I{DUT_CONFIG_DIR}",
        "-DTEST_FLEN=32",
        f"-DTEST_FILE=\"{test_file_name}\"",
        f"-T{DUT_CONFIG_DIR}/link.ld",
        src_path,
        "-o", elf_path
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        return (proc.returncode == 0), proc.stdout
    except Exception as e:
        return False, str(e)

def run_act_dut(elf_path: str) -> Tuple[bool, int, int, float, str]:
    """Run an ACT ELF on the DUT simulator."""
    cmd = [
        SIM_EXE,
        f"+elf={elf_path}",
        "+max-cycles=2000000"
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        out = proc.stdout
        passed = (proc.returncode == 0) and ("Exit code: 0 (PASS)" in out or "SIM_EXIT received with code: 0" in out)

        cycles = 0
        retired = 0
        ipc = 0.0
        for line in out.splitlines():
            if "Cycles" in line and ":" in line:
                cycles = int(line.split(":")[1].strip())
            elif "Retired insns" in line and ":" in line:
                retired = int(line.split(":")[1].strip())
            elif "IPC" in line and ":" in line:
                ipc = float(line.split(":")[1].strip())

        return passed, cycles, retired, ipc, out
    except Exception as e:
        return False, 0, 0, 0.0, str(e)

def run_act_spike(elf_path: str) -> Tuple[bool, str]:
    """Run an ACT ELF on Spike reference model."""
    cmd = [
        "spike",
        "--isa=rv32im_zicsr",
        "-m0x80000000:0x200000,0x10000000:0x1000",
        elf_path
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        return (proc.returncode == 0), proc.stdout
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="RISC-V ACT4 Certification Suite Runner")
    parser.add_argument("--suite", choices=["all", "RV32I", "RV32M", "Zicsr"], default="all", help="Target suite to run")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    suites_to_run = SUITES if args.suite == "all" else {args.suite: SUITES[args.suite]}

    all_tests: List[Dict[str, Any]] = []
    total_passed = 0
    total_failed = 0
    start_time = time.time()

    print("=" * 80)
    print("      RISC-V Architectural Certification Test (ACT4) Execution Engine     ")
    print("=" * 80)

    for suite_name, suite_path in suites_to_run.items():
        test_files = sorted(glob.glob(os.path.join(suite_path, "*.S")))
        print(f"\n--- Running Suite: {suite_name} ({len(test_files)} tests) ---")

        for src in test_files:
            test_name = os.path.splitext(os.path.basename(src))[0]
            elf_path = os.path.join(BUILD_DIR, f"{test_name}.elf")

            # 1. Compile
            compile_ok, compile_out = compile_act_test(src, elf_path)
            if not compile_ok:
                print(f"  [\033[91mFAIL\033[0m] {test_name:<24} | COMPILE ERROR")
                all_tests.append({
                    "name": test_name,
                    "suite": suite_name,
                    "compile_pass": False,
                    "dut_pass": False,
                    "spike_pass": False,
                    "pass": False,
                    "cycles": 0,
                    "retired": 0,
                    "ipc": 0.0,
                    "error": compile_out
                })
                total_failed += 1
                continue

            # 2. Run DUT
            dut_pass, cycles, retired, ipc, dut_out = run_act_dut(elf_path)

            # 3. Run Spike reference
            spike_pass, spike_out = run_act_spike(elf_path)

            overall_pass = dut_pass and spike_pass
            if overall_pass:
                total_passed += 1
                status_str = "\033[92mPASS\033[0m"
            else:
                total_failed += 1
                status_str = "\033[91mFAIL\033[0m"

            print(f"  [{status_str}] {test_name:<24} | Cycles: {cycles:<6} | Retired: {retired:<6} | IPC: {ipc:.4f} | DUT: {'PASS' if dut_pass else 'FAIL'} | Spike: {'PASS' if spike_pass else 'FAIL'}")

            all_tests.append({
                "name": test_name,
                "suite": suite_name,
                "compile_pass": True,
                "dut_pass": dut_pass,
                "spike_pass": spike_pass,
                "pass": overall_pass,
                "cycles": cycles,
                "retired": retired,
                "ipc": ipc,
                "error": "" if overall_pass else f"DUT_PASS={dut_pass}, SPIKE_PASS={spike_pass}"
            })

    elapsed = time.time() - start_time
    total_count = total_passed + total_failed

    summary_data = {
        "framework": "ACT4 / riscv-arch-test",
        "pinned_commit": "74efcaac81f48f437f58868771daf2ed2776d422",
        "udb_config": "verification/act4/rv32_ooo/rv32_ooo.yaml",
        "test_config": "verification/act4/rv32_ooo/test_config.yaml",
        "total_tests": total_count,
        "passed_tests": total_passed,
        "failed_tests": total_failed,
        "all_passed": (total_failed == 0),
        "elapsed_seconds": round(elapsed, 2),
        "results": all_tests
    }

    report_json_path = os.path.join(REPORT_DIR, "act4_summary.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f" ACT4 Certification Signoff: {total_passed} / {total_count} PASSED ({total_failed} failed)")
    print(f" Machine-readable report saved to: {report_json_path}")
    print("=" * 80)

    if args.json:
        print(json.dumps(summary_data, indent=2))

    sys.exit(0 if total_failed == 0 else 1)

if __name__ == "__main__":
    main()
