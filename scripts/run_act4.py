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
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

ACT4_ROOT = "verification/act4/riscv-arch-test"
CORE_CONFIG_DIR = "verification/act4/riscv-arch-test/config/cores/rv32_ooo"
ELF_DIR = "verification/act4/riscv-arch-test/work/rv32_ooo/elfs/rv32i"
REPORT_DIR = "verification/act4/report"
SIM_EXE = "build/sim/rv32_ooo_sim"

def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def ensure_act4_elfs():
    """Ensure ACT4 ELFs are built using the official framework and Sail reference."""
    elfs = sorted(glob.glob(f"{ELF_DIR}/**/*.elf", recursive=True))
    if len(elfs) >= 58:
        return elfs

    print("==> Building ACT4 self-checking ELFs via official Sail flow...")
    cmd = [
        "mise", "exec", "--",
        "make", f"CONFIG_FILES=config/cores/rv32_ooo/test_config.yaml"
    ]
    env = os.environ.copy()
    env["PATH"] = f"/home/a/.local/opt/riscv32-gcc/bin:/home/a/.local/opt/spike/bin:/home/a/.local/bin:{env.get('PATH', '')}"
    env["MISE_YES"] = "1"
    
    proc = subprocess.run(cmd, cwd=ACT4_ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"ACT4 framework build failed:\n{proc.stdout}\n{proc.stderr}")
        sys.exit(1)

    elfs = sorted(glob.glob(f"{ELF_DIR}/**/*.elf", recursive=True))
    return elfs

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
    env = os.environ.copy()
    env["PATH"] = f"/home/a/.local/opt/spike/bin:{env.get('PATH', '')}"

    try:
        proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        return (proc.returncode == 0), proc.stdout
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Official ACT4 Execution Engine")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--out-dir", default=REPORT_DIR, help="Directory to store reports")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("=" * 80)
    print("   RISC-V Architectural Certification Test (ACT4) Official Framework Runner ")
    print("=" * 80)

    elfs = ensure_act4_elfs()
    print(f"Discovered {len(elfs)} official framework-generated self-checking ELFs (Sail reference).")

    all_tests: List[Dict[str, Any]] = []
    elf_hashes: Dict[str, str] = {}
    total_passed = 0
    total_failed = 0
    start_time = time.time()

    for elf in elfs:
        rel_test = os.path.relpath(elf, ELF_DIR)
        suite_name = os.path.dirname(rel_test)
        test_name = os.path.basename(rel_test)
        elf_hash = sha256_file(elf)
        elf_hashes[rel_test] = elf_hash

        # Run on DUT
        dut_pass, cycles, retired, ipc, dut_out = run_act_dut(elf)

        # Run on Spike
        spike_pass, spike_out = run_act_spike(elf)

        overall_pass = dut_pass
        if overall_pass:
            total_passed += 1
            status_str = "\033[92mPASS\033[0m"
        else:
            total_failed += 1
            status_str = "\033[91mFAIL\033[0m"

        print(f"  [{status_str}] {rel_test:<32} | Cycles: {cycles:<6} | Retired: {retired:<6} | IPC: {ipc:.4f} | DUT: {'PASS' if dut_pass else 'FAIL'} | Spike: {'PASS' if spike_pass else 'FAIL'}")

        all_tests.append({
            "test": rel_test,
            "suite": suite_name,
            "elf_sha256": elf_hash,
            "dut_pass": dut_pass,
            "spike_pass": spike_pass,
            "pass": overall_pass,
            "cycles": cycles,
            "retired_insns": retired,
            "ipc": ipc,
            "error": "" if overall_pass else f"DUT_PASS={dut_pass}, SPIKE_PASS={spike_pass}"
        })

    elapsed = time.time() - start_time
    total_count = total_passed + total_failed

    summary_data = {
        "framework": "ACT4 / riscv-arch-test (Official Framework)",
        "reference_model": "sail_riscv_sim 0.13.1",
        "pinned_act_commit": "74efcaac81f48f437f58868771daf2ed2776d422",
        "udb_config": "verification/act4/riscv-arch-test/config/cores/rv32_ooo/rv32_ooo.yaml",
        "sail_config": "verification/act4/riscv-arch-test/config/cores/rv32_ooo/sail.json",
        "total_tests": total_count,
        "passed_tests": total_passed,
        "failed_tests": total_failed,
        "pass_rate_pct": round(100.0 * total_passed / total_count, 2) if total_count > 0 else 0.0,
        "all_passed": (total_failed == 0),
        "elapsed_seconds": round(elapsed, 2),
        "results": all_tests
    }

    report_json_path = os.path.join(args.out_dir, "act4_summary.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    hash_json_path = os.path.join(args.out_dir, "elf_hashes.json")
    with open(hash_json_path, "w", encoding="utf-8") as f:
        json.dump(elf_hashes, f, indent=2)

    print("\n" + "=" * 80)
    print(f" ACT4 Official Regression: {total_passed} / {total_count} PASSED ({total_failed} failed, {summary_data['pass_rate_pct']}%)")
    print(f" Summary report saved to : {report_json_path}")
    print(f" ELF hashes saved to    : {hash_json_path}")
    print("=" * 80)

    if args.json:
        print(json.dumps(summary_data, indent=2))

    sys.exit(0 if total_failed == 0 else 1)

if __name__ == "__main__":
    main()
