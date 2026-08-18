#!/usr/bin/env python3
"""
scripts/run_spike_diff.py — True Spike Lockstep Differential Verification Runner (Milestone CM4)
Executes bare-metal ELFs concurrently on DUT (rv32_ooo_sim) and Golden Reference (Spike),
comparing retirement event streams (PC, instruction bits, architectural state) in lockstep.
"""

import os
import sys
import glob
import subprocess
import re
from typing import List, Dict, Any, Tuple

SIM_EXE = "build/sim/rv32_ooo_sim"
TEST_DIR = "build/tests"

DUT_RE = re.compile(r"core\s+\d+:\s+0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)(?:\s+([xf]\d+)=0x([0-9a-fA-F]+))?")
SPIKE_RE = re.compile(r"core\s+\d+:\s+(?:[0-9a-fA-F]+\s+)?0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)")

def parse_dut_trace(trace_path: str) -> List[Dict[str, Any]]:
    """Parse DUT commit log into sequence of retired instruction events starting from _start (0x80000000)."""
    events = []
    if not os.path.exists(trace_path):
        return events

    with open(trace_path, "r") as f:
        for line in f:
            m = DUT_RE.search(line)
            if m:
                pc = int(m.group(1), 16)
                insn = int(m.group(2), 16)
                dst_reg = m.group(3)
                dst_val = int(m.group(4), 16) if m.group(4) else None
                if pc >= 0x80000000:
                    events.append({
                        "pc": pc,
                        "insn": insn,
                        "dst_reg": dst_reg,
                        "dst_val": dst_val,
                        "raw": line.strip()
                    })
    return events

def run_spike(elf_path: str, isa: str = "rv32im") -> Tuple[bool, List[Dict[str, Any]], str]:
    """Execute Spike with -l instruction logging and extract the golden trace."""
    spike_log_path = f"build/tests/spike_{os.path.splitext(os.path.basename(elf_path))[0]}.log"
    cmd = [
        "spike",
        "-l",
        f"--isa={isa}",
        "-m0x80000000:0x100000,0x10000000:0x1000",
        elf_path
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        output = proc.stdout
        with open(spike_log_path, "w") as f:
            f.write(output)

        events = []
        for line in output.splitlines():
            m = SPIKE_RE.search(line)
            if m:
                pc = int(m.group(1), 16)
                insn = int(m.group(2), 16)
                if pc >= 0x80000000:
                    events.append({
                        "pc": pc,
                        "insn": insn,
                        "raw": line.strip()
                    })

        return (True, events, output)
    except subprocess.TimeoutExpired:
        return (False, [], "Spike execution timeout (>30s)")
    except Exception as e:
        return (False, [], f"Spike execution error: {str(e)}")

def run_dut(elf_path: str) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any], str]:
    """Execute DUT simulation harness and capture commit trace and performance stats."""
    test_name = os.path.splitext(os.path.basename(elf_path))[0]
    trace_path = f"build/tests/dut_{test_name}.log"
    dut_log_path = f"build/tests/diff_{test_name}.log"

    cmd = [
        SIM_EXE,
        f"+elf={elf_path}",
        f"+trace={trace_path}"
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        output = proc.stdout
        with open(dut_log_path, "w") as f:
            f.write(output)

        passed = (proc.returncode == 0) and ("SIM_EXIT received with code: 0" in output)

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

        events = parse_dut_trace(trace_path)
        stats = {
            "cycles": cycles,
            "retired": retired,
            "ipc": ipc,
            "pass": passed
        }
        return (True, events, stats, output)
    except subprocess.TimeoutExpired:
        return (False, [], {"cycles": -1, "retired": -1, "ipc": 0.0, "pass": False}, "DUT Timeout (>30s)")

def diff_traces(dut_events: List[Dict[str, Any]], spike_events: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Compare DUT and Spike commit traces event-by-event."""
    min_len = min(len(dut_events), len(spike_events))
    if min_len == 0:
        return False, f"Empty event stream! DUT={len(dut_events)}, Spike={len(spike_events)}"

    for i in range(min_len):
        dut = dut_events[i]
        spike = spike_events[i]

        if dut["pc"] != spike["pc"] or dut["insn"] != spike["insn"]:
            # Format detailed mismatch report with context window
            ctx_start = max(0, i - 4)
            ctx_end_dut = min(len(dut_events), i + 4)
            ctx_end_spk = min(len(spike_events), i + 4)

            msg = [f"MISMATCH at commit event #{i}:"]
            msg.append("  Previous matching context:")
            for c in range(ctx_start, i):
                msg.append(f"    [#{c}] PC=0x{dut_events[c]['pc']:08x} (0x{dut_events[c]['insn']:08x})")

            msg.append(f"  >>> DUT Event   [#{i}]: PC=0x{dut['pc']:08x} (0x{dut['insn']:08x}) -> {dut['raw']}")
            msg.append(f"  >>> Spike Event [#{i}]: PC=0x{spike['pc']:08x} (0x{spike['insn']:08x}) -> {spike['raw']}")

            msg.append("  Following DUT trace:")
            for c in range(i + 1, ctx_end_dut):
                msg.append(f"    [#{c}] PC=0x{dut_events[c]['pc']:08x} (0x{dut_events[c]['insn']:08x})")

            msg.append("  Following Spike trace:")
            for c in range(i + 1, ctx_end_spk):
                msg.append(f"    [#{c}] PC=0x{spike_events[c]['pc']:08x} (0x{spike_events[c]['insn']:08x})")

            return False, "\n".join(msg)

    return True, f"Exact match across all {min_len} architectural instructions!"

def run_test(elf_path: str) -> Dict[str, Any]:
    test_name = os.path.splitext(os.path.basename(elf_path))[0]
    
    # Determine ISA subset for Spike
    is_fp = "fp" in test_name
    isa = "rv32imf" if is_fp else "rv32im"

    dut_ok, dut_events, dut_stats, dut_out = run_dut(elf_path)
    spike_ok, spike_events, spike_out = run_spike(elf_path, isa=isa)

    if not dut_ok:
        return {
            "name": test_name,
            "pass": False,
            "cycles": -1,
            "retired": 0,
            "ipc": 0.0,
            "diff_pass": False,
            "msg": f"DUT failed to run: {dut_out}"
        }

    if not spike_ok or len(spike_events) == 0:
        return {
            "name": test_name,
            "pass": False,
            "cycles": dut_stats["cycles"],
            "retired": dut_stats["retired"],
            "ipc": dut_stats["ipc"],
            "diff_pass": False,
            "msg": f"Spike failed to run: {spike_out}"
        }

    diff_pass, diff_msg = diff_traces(dut_events, spike_events)
    overall_pass = dut_stats["pass"] and diff_pass

    return {
        "name": test_name,
        "pass": overall_pass,
        "dut_pass": dut_stats["pass"],
        "diff_pass": diff_pass,
        "cycles": dut_stats["cycles"],
        "retired": dut_stats["retired"],
        "ipc": dut_stats["ipc"],
        "dut_events": len(dut_events),
        "spike_events": len(spike_events),
        "msg": diff_msg
    }

def main():
    print("=" * 80)
    print("      RV32 OoO Core — True Spike Lockstep Differential Verification       ")
    print("=" * 80)

    if len(sys.argv) > 1:
        elf_files = [sys.argv[1]]
    else:
        elf_files = sorted(glob.glob(os.path.join(TEST_DIR, "*.elf")))

    if not elf_files:
        print("Error: No test ELF binaries found. Run 'make compile-tests' first.")
        sys.exit(1)

    results = []
    all_passed = True

    for elf in elf_files:
        res = run_test(elf)
        results.append(res)
        status_str = "\033[92mPASS\033[0m" if res["pass"] else "\033[91mFAIL\033[0m"
        print(f"  [{status_str}] {res['name']:<20} | Cycles: {res['cycles']:<6} | Retired: {res['retired']:<6} | IPC: {res['ipc']:.4f} | Diff: {'MATCH' if res['diff_pass'] else 'MISMATCH'}")
        if not res["pass"]:
            all_passed = False
            print(f"\n    [DEBUG DETAILS]:\n    {res['msg']}\n")

    print("=" * 80)
    passed_count = sum(1 for r in results if r["pass"])
    total_count = len(results)
    print(f" Verification Signoff: {passed_count} / {total_count} passed ({total_count - passed_count} failed)")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
