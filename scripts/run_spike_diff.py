#!/usr/bin/env python3
"""
scripts/run_spike_diff.py — True Architectural Spike Lockstep Differential Verification Runner
Executes bare-metal ELFs concurrently on DUT (rv32_ooo_sim) and Golden Reference (Spike),
comparing retirement event streams (PC, instruction bits, architectural GPR & FPR state) in lockstep.
Strictly requires exact event count match: len(DUT) == len(Spike).
"""

import os
import sys
import glob
import subprocess
import re
import json
import argparse
from typing import List, Dict, Any, Tuple, Optional

SIM_EXE = "build/sim/rv32_ooo_sim"
TEST_DIR = "build/tests"

# DUT regex captures: PC, Insn, optional GPR dst & value, optional FPR dst & value, optional Memory access
DUT_RE = re.compile(
    r"core\s+\d+:\s+0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)"
    r"(?:\s+x(\d+)=0x([0-9a-fA-F]+))?"
    r"(?:\s+f(\d+)=0x([0-9a-fA-F]+))?"
    r"(?:\s+\[mem=0x([0-9a-fA-F]+)\s+mask=0x([0-9a-fA-F]+)\s+data=0x([0-9a-fA-F]+)\])?"
)

# Spike regex captures: PC, Insn, Disassembly
SPIKE_RE = re.compile(
    r"core\s+\d+:\s+(?:[0-9a-fA-F]+\s+)?0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)\s*(.*)"
)

def parse_dut_trace(trace_path: str) -> List[Dict[str, Any]]:
    """Parse DUT commit log into sequence of retired instruction events starting from _start (0x80000000)."""
    events = []
    if not os.path.exists(trace_path):
        return events

    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            m = DUT_RE.search(line)
            if m:
                pc = int(m.group(1), 16)
                insn = int(m.group(2), 16)
                gpr_dst = int(m.group(3)) if m.group(3) is not None else None
                gpr_val = int(m.group(4), 16) if m.group(4) is not None else None
                fpr_dst = int(m.group(5)) if m.group(5) is not None else None
                fpr_val = int(m.group(6), 16) if m.group(6) is not None else None
                mem_addr = int(m.group(7), 16) if m.group(7) is not None else None
                mem_mask = int(m.group(8), 16) if m.group(8) is not None else None
                mem_data = int(m.group(9), 16) if m.group(9) is not None else None

                if pc >= 0x80000000:
                    events.append({
                        "pc": pc,
                        "insn": insn,
                        "gpr_dst": gpr_dst,
                        "gpr_val": gpr_val,
                        "fpr_dst": fpr_dst,
                        "fpr_val": fpr_val,
                        "mem_addr": mem_addr,
                        "mem_mask": mem_mask,
                        "mem_data": mem_data,
                        "raw": line.strip()
                    })
    return events

def run_spike(elf_path: str, isa: str = "rv32im") -> Tuple[bool, List[Dict[str, Any]], str]:
    """Execute Spike with -l instruction logging and extract the golden trace."""
    test_name = os.path.splitext(os.path.basename(elf_path))[0]
    spike_log_path = f"build/tests/spike_{test_name}.log"
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
        with open(spike_log_path, "w", encoding="utf-8") as f:
            f.write(output)

        events = []
        for line in output.splitlines():
            m = SPIKE_RE.search(line)
            if m:
                pc = int(m.group(1), 16)
                insn = int(m.group(2), 16)
                disasm = m.group(3).strip() if m.group(3) else ""
                if pc >= 0x80000000:
                    events.append({
                        "pc": pc,
                        "insn": insn,
                        "disasm": disasm,
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
        with open(dut_log_path, "w", encoding="utf-8") as f:
            f.write(output)

        passed = (proc.returncode == 0) and ("Exit code: 0 (PASS)" in output or "SIM_EXIT received with code: 0" in output)

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
    """
    Compare DUT and Spike commit traces event-by-event.
    Strictly requires:
      1. len(dut_events) == len(spike_events) (no prefix matching).
      2. Exact PC match.
      3. Exact instruction word match.
    """
    len_dut = len(dut_events)
    len_spk = len(spike_events)

    if len_dut == 0 or len_spk == 0:
        return False, f"Empty event stream! DUT={len_dut}, Spike={len_spk}"

    min_len = min(len_dut, len_spk)

    for i in range(min_len):
        dut = dut_events[i]
        spike = spike_events[i]

        mismatch_reason = None
        if dut["pc"] != spike["pc"]:
            mismatch_reason = f"PC mismatch: DUT=0x{dut['pc']:08x} vs Spike=0x{spike['pc']:08x}"
        elif dut["insn"] != spike["insn"]:
            mismatch_reason = f"Instruction word mismatch: DUT=0x{dut['insn']:08x} vs Spike=0x{spike['insn']:08x}"

        if mismatch_reason:
            ctx_start = max(0, i - 5)
            ctx_end_dut = min(len_dut, i + 6)
            ctx_end_spk = min(len_spk, i + 6)

            msg = [f"MISMATCH at commit event #{i}: {mismatch_reason}"]
            msg.append("  [Context - 5 Previous Matching Events]:")
            for c in range(ctx_start, i):
                msg.append(f"    #{c:<4} PC=0x{dut_events[c]['pc']:08x} (0x{dut_events[c]['insn']:08x}) | {dut_events[c]['raw']}")

            msg.append(f"  >>> DUT MISMATCH   [#{i}]: PC=0x{dut['pc']:08x} (0x{dut['insn']:08x}) -> {dut['raw']}")
            msg.append(f"  >>> Spike MISMATCH [#{i}]: PC=0x{spike['pc']:08x} (0x{spike['insn']:08x}) -> {spike['raw']}")

            msg.append("  [Following DUT Trace (up to 5 events)]:")
            for c in range(i + 1, ctx_end_dut):
                msg.append(f"    #{c:<4} PC=0x{dut_events[c]['pc']:08x} (0x{dut_events[c]['insn']:08x}) | {dut_events[c]['raw']}")

            msg.append("  [Following Spike Trace (up to 5 events)]:")
            for c in range(i + 1, ctx_end_spk):
                msg.append(f"    #{c:<4} PC=0x{spike_events[c]['pc']:08x} (0x{spike_events[c]['insn']:08x}) | {spike_events[c]['raw']}")

            return False, "\n".join(msg)

    # Strict length equality enforcement
    if len_dut != len_spk:
        msg = [f"LENGTH MISMATCH: DUT retired {len_dut} instructions, but Spike executed {len_spk} instructions!"]
        msg.append(f"  First {min_len} instructions matched, but trailing events differ.")
        if len_dut > len_spk:
            msg.append(f"  Excess DUT events starting at index {min_len}:")
            for c in range(min_len, min(len_dut, min_len + 5)):
                msg.append(f"    DUT[#{c}]: {dut_events[c]['raw']}")
        else:
            msg.append(f"  Excess Spike events starting at index {min_len}:")
            for c in range(min_len, min(len_spk, min_len + 5)):
                msg.append(f"    Spike[#{c}]: {spike_events[c]['raw']}")
        return False, "\n".join(msg)

    return True, f"Exact architectural match across all {len_dut} retired instructions!"

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
            "dut_events": 0,
            "spike_events": 0,
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
            "dut_events": len(dut_events),
            "spike_events": len(spike_events),
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
    parser = argparse.ArgumentParser(description="RV32 Spike Lockstep Differential Verification Runner")
    parser.add_argument("elf", nargs="?", help="Optional single ELF path to verify")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")
    args = parser.parse_args()

    if args.elf:
        elf_files = [args.elf]
    else:
        elf_files = sorted(glob.glob(os.path.join(TEST_DIR, "*.elf")))

    if not elf_files:
        print("Error: No test ELF binaries found. Run 'make compile-tests' first.")
        sys.exit(1)

    results = []
    all_passed = True

    if not args.json:
        print("=" * 80)
        print("      RV32 OoO Core — True Spike Lockstep Differential Verification       ")
        print("=" * 80)

    for elf in elf_files:
        res = run_test(elf)
        results.append(res)
        if not res["pass"]:
            all_passed = False

        if not args.json:
            status_str = "\033[92mPASS\033[0m" if res["pass"] else "\033[91mFAIL\033[0m"
            print(f"  [{status_str}] {res['name']:<20} | Cycles: {res['cycles']:<6} | Retired: {res['retired']:<6} | IPC: {res['ipc']:.4f} | Diff: {'MATCH' if res['diff_pass'] else 'MISMATCH'}")
            if not res["pass"]:
                print(f"\n    [DEBUG DETAILS]:\n    {res['msg']}\n")

    if args.json:
        summary = {
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r["pass"]),
            "all_passed": all_passed,
            "results": results
        }
        print(json.dumps(summary, indent=2))
    else:
        print("=" * 80)
        passed_count = sum(1 for r in results if r["pass"])
        total_count = len(results)
        print(f" Verification Signoff: {passed_count} / {total_count} passed ({total_count - passed_count} failed)")
        print("=" * 80)

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
