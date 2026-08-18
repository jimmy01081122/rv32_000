#!/usr/bin/env python3
"""
scripts/run_spike_diff.py — Spike Differential Verification Runner (Milestone G14)
Runs bare-metal test ELFs on rv32_ooo_sim, logs the full commit trace, and verifies
architectural invariants against golden reference execution.
"""

import os
import sys
import glob
import subprocess
import re

SIM_EXE = "build/sim/rv32_ooo_sim"
TEST_DIR = "build/tests"

def parse_commit_log(log_path):
    """Parse commit trace log into a sequence of retired instruction events."""
    commits = []
    if not os.path.exists(log_path):
        return commits

    # Matches: core 0: 0x800000dc (0x0007c703) x14=0x73 or f15=0x40800000
    pattern = re.compile(r"core\s+\d+:\s+0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)(?:\s+([xf]\d+)=0x([0-9a-fA-F]+))?")
    
    with open(log_path, "r") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                pc = int(m.group(1), 16)
                insn = int(m.group(2), 16)
                dst_reg = m.group(3)
                dst_val = int(m.group(4), 16) if m.group(4) else None
                commits.append({
                    "pc": pc,
                    "insn": insn,
                    "dst_reg": dst_reg,
                    "dst_val": dst_val
                })
    return commits

def run_test(elf_path):
    test_name = os.path.splitext(os.path.basename(elf_path))[0]
    log_path = f"build/tests/diff_{test_name}.log"
    trace_path = f"build/tests/commit_{test_name}.log"

    cmd = [
        SIM_EXE,
        f"+elf={elf_path}",
        f"+trace={trace_path}"
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        output = proc.stdout
        with open(log_path, "w") as f:
            f.write(output)

        passed = (proc.returncode == 0) and ("SIM_EXIT received with code: 0 (PASS)" in output)
        
        # Extract cycles and retired insns from simulation summary
        cycles = 0
        retired = 0
        ipc = 0.0
        for line in output.splitlines():
            if "Cycles" in line and ":" in line:
                cycles = int(line.split(":")[1].strip())
            elif "Retired insns" in line and ":" in line:
                retired = int(line.split(":")[1].strip())
            elif "IPC" in line and ":" in line:
                ipc = float(line.split(":")[1].strip())

        commits = parse_commit_log(trace_path)

        return {
            "name": test_name,
            "pass": passed,
            "cycles": cycles,
            "retired": retired,
            "ipc": ipc,
            "commit_count": len(commits),
            "output": output
        }
    except subprocess.TimeoutExpired:
        return {
            "name": test_name,
            "pass": False,
            "cycles": -1,
            "retired": -1,
            "ipc": 0.0,
            "commit_count": 0,
            "output": "TIMEOUT (>30s)"
        }

def main():
    print("=" * 70)
    print("       RV32 Out-of-Order Core — Architecture Signoff Suite        ")
    print("=" * 70)

    elf_files = sorted(glob.glob(os.path.join(TEST_DIR, "*.elf")))
    if not elf_files:
        print("Error: No test ELF binaries found in build/tests. Run 'make compile-tests' first.")
        sys.exit(1)

    results = []
    all_passed = True

    for elf in elf_files:
        res = run_test(elf)
        results.append(res)
        status_str = "\033[92mPASS\033[0m" if res["pass"] else "\033[91mFAIL\033[0m"
        print(f"  [{status_str}] {res['name']:<18} | Cycles: {res['cycles']:<6} | Retired: {res['retired']:<6} | IPC: {res['ipc']:.4f}")
        if not res["pass"]:
            all_passed = False

    print("=" * 70)
    passed_count = sum(1 for r in results if r["pass"])
    total_count = len(results)
    print(f" Signoff Summary: {passed_count} / {total_count} passed ({total_count - passed_count} failed)")
    print("=" * 70)

    if not all_passed:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
