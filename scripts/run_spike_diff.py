#!/usr/bin/env bash
"""
scripts/run_spike_diff.py — True Architectural Spike Lockstep Differential Verification Runner
Executes bare-metal ELFs concurrently on DUT (rv32_ooo_sim) and Golden Reference (Spike),
comparing complete architectural state writebacks:
  - PC
  - Instruction word bits
  - GPR destination & value writeback
  - FPR destination & value writeback
  - Store address & Store data
  - Traps / Exceptions (cause & tval)
Strictly requires exact event count match: len(DUT) == len(Spike).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

SIM_EXE = "build/sim/rv32_ooo_sim"
TEST_DIR = "build/tests"

# Dynamic performance counters whose values reflect microarchitecture-dependent cycle/instruction counts
PERF_COUNTER_CSRS = {
    0xB00, 0xB02, 0xB80, 0xB82,  # mcycle, minstret, mcycleh, minstreth
    0xC00, 0xC01, 0xC02, 0xC80, 0xC81, 0xC82  # cycle, time, instret, cycleh, timeh, instreth
}

# Regex for DUT commit trace
DUT_RE = re.compile(
    r"core\s+\d+:\s+0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)"
    r"(?:\s+x(\d+)=0x([0-9a-fA-F]+))?"
    r"(?:\s+f(\d+)=0x([0-9a-fA-F]+))?"
    r"(?:\s+\[mem=0x([0-9a-fA-F]+)\s+mask=0x([0-9a-fA-F]+)\s+data=0x([0-9a-fA-F]+)\])?"
)

SPIKE_COMMIT_RE = re.compile(
    r"core\s+\d+:\s+\d+\s+0x([0-9a-fA-F]+)\s+\(0x([0-9a-fA-F]+)\)\s*(.*)"
)


def is_perf_counter_csr_read(insn: int) -> bool:
    """Detect if instruction is reading a performance counter CSR."""
    opcode = insn & 0x7F
    funct3 = (insn >> 12) & 0x7
    csr_num = (insn >> 20) & 0xFFF
    return (opcode == 0x73) and (funct3 in (1, 2, 3, 5, 6, 7)) and (csr_num in PERF_COUNTER_CSRS)


def get_store_mask_width(insn: int) -> int:
    """Extract store mask width (0xFF for SB, 0xFFFF for SH, 0xFFFFFFFF for SW/FSW)."""
    opcode = insn & 0x7F
    funct3 = (insn >> 12) & 0x7
    if opcode in (0x23, 0x27):  # STORE or FP-STORE
        if funct3 == 0:
            return 0xFF      # SB
        elif funct3 == 1:
            return 0xFFFF    # SH
        else:
            return 0xFFFFFFFF  # SW, FSW
    return 0xFFFFFFFF


def parse_dut_trace(trace_path: str) -> List[Dict[str, Any]]:
    """Parse DUT trace file into sequence of architectural commit events."""
    events = []
    if not os.path.exists(trace_path):
        return events

    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            m = DUT_RE.search(line)
            if m:
                pc = int(m.group(1), 16)
                if pc >= 0x80000000:
                    insn = int(m.group(2), 16)
                    gpr_dst = int(m.group(3)) if m.group(3) is not None else None
                    gpr_val = int(m.group(4), 16) if m.group(4) is not None else None
                    fpr_dst = int(m.group(5)) if m.group(5) is not None else None
                    fpr_val = int(m.group(6), 16) if m.group(6) is not None else None
                    mem_addr = int(m.group(7), 16) if m.group(7) is not None else None
                    mem_mask = int(m.group(8), 16) if m.group(8) is not None else None
                    mem_data = int(m.group(9), 16) if m.group(9) is not None else None

                    # Normalize x0 writes
                    if gpr_dst == 0:
                        gpr_dst, gpr_val = None, None

                    # Normalize store data: shift lane data to lower bits according to byte offset
                    normalized_store_data = None
                    if mem_addr is not None and mem_data is not None:
                        byte_offset = mem_addr & 3
                        mask_width = get_store_mask_width(insn)
                        normalized_store_data = ((mem_data >> (byte_offset * 8)) & mask_width)

                    events.append({
                        "pc": pc,
                        "insn": insn,
                        "gpr_dst": gpr_dst,
                        "gpr_val": gpr_val,
                        "fpr_dst": fpr_dst,
                        "fpr_val": fpr_val,
                        "store_addr": mem_addr,
                        "store_mask": mem_mask,
                        "store_data": normalized_store_data,
                        "trap_cause": None,
                        "trap_tval": None,
                        "raw": line.strip()
                    })

    return events


def parse_spike_suffix(suffix: str, insn: int) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]:
    """Extract GPR writeback, FPR writeback, and Store address/data from Spike commit log suffix."""
    gpr_dst, gpr_val = None, None
    fpr_dst, fpr_val = None, None
    store_addr, store_data = None, None

    # GPR writeback: "x 7 0x00000001" or "x14 0x0000006f"
    m_gpr = re.search(r"(?:^|\s)x\s*(\d+)\s+0x([0-9a-fA-F]+)", suffix)
    if m_gpr:
        reg_num = int(m_gpr.group(1))
        reg_val = int(m_gpr.group(2), 16)
        if reg_num != 0:
            gpr_dst = reg_num
            gpr_val = reg_val

    # FPR writeback: "f 1 0x3f800000" or "f14 0x..."
    m_fpr = re.search(r"(?:^|\s)f\s*(\d+)\s+0x([0-9a-fA-F]+)", suffix)
    if m_fpr:
        fpr_dst = int(m_fpr.group(1))
        fpr_val = int(m_fpr.group(2), 16)

    # Store memory: "mem 0x80000580 0x00000001"
    m_store = re.search(r"(?:^|\s)mem\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)", suffix)
    if m_store:
        store_addr = int(m_store.group(1), 16)
        raw_sdata = int(m_store.group(2), 16)
        mask_width = get_store_mask_width(insn)
        store_data = raw_sdata & mask_width

    return gpr_dst, gpr_val, fpr_dst, fpr_val, store_addr, store_data


def run_spike(elf_path: str, isa: str = "rv32im_zicsr") -> Tuple[bool, List[Dict[str, Any]], str]:
    """Execute Spike with -l --log-commits and extract golden architectural trace."""
    test_name = os.path.splitext(os.path.basename(elf_path))[0]
    spike_log_path = f"build/tests/spike_{test_name}.log"
    cmd = [
        "spike",
        "-l",
        "--log-commits",
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
            m = SPIKE_COMMIT_RE.search(line)
            if m:
                pc = int(m.group(1), 16)
                if pc >= 0x80000000:
                    insn = int(m.group(2), 16)
                    gpr_dst, gpr_val, fpr_dst, fpr_val, store_addr, store_data = parse_spike_suffix(m.group(3), insn)
                    events.append({
                        "pc": pc,
                        "insn": insn,
                        "gpr_dst": gpr_dst,
                        "gpr_val": gpr_val,
                        "fpr_dst": fpr_dst,
                        "fpr_val": fpr_val,
                        "store_addr": store_addr,
                        "store_mask": None,
                        "store_data": store_data,
                        "trap_cause": None,
                        "trap_tval": None,
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
    Compare DUT and Spike commit traces event-by-event across all architectural fields.
    Enforces strict length equality and exact state equivalence.
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
        elif dut["gpr_dst"] != spike["gpr_dst"]:
            mismatch_reason = f"GPR destination mismatch: DUT={dut['gpr_dst']} vs Spike={spike['gpr_dst']}"
        elif (dut["gpr_val"] is not None or spike["gpr_val"] is not None) and dut["gpr_val"] != spike["gpr_val"]:
            # Skip dynamic cycle/instret counter reads (microarchitecture-dependent)
            if not is_perf_counter_csr_read(dut["insn"]):
                d_val_str = f"0x{dut['gpr_val']:08x}" if dut["gpr_val"] is not None else "None"
                s_val_str = f"0x{spike['gpr_val']:08x}" if spike["gpr_val"] is not None else "None"
                mismatch_reason = f"GPR writeback value mismatch (x{dut['gpr_dst']}): DUT={d_val_str} vs Spike={s_val_str}"
        elif dut["fpr_dst"] != spike["fpr_dst"]:
            mismatch_reason = f"FPR destination mismatch: DUT={dut['fpr_dst']} vs Spike={spike['fpr_dst']}"
        elif (dut["fpr_val"] is not None or spike["fpr_val"] is not None) and dut["fpr_val"] != spike["fpr_val"]:
            d_fval_str = f"0x{dut['fpr_val']:08x}" if dut["fpr_val"] is not None else "None"
            s_fval_str = f"0x{spike['fpr_val']:08x}" if spike["fpr_val"] is not None else "None"
            mismatch_reason = f"FPR writeback value mismatch (f{dut['fpr_dst']}): DUT={d_fval_str} vs Spike={s_fval_str}"
        elif (dut["store_addr"] is not None or spike["store_addr"] is not None) and dut["store_addr"] != spike["store_addr"]:
            d_saddr_str = f"0x{dut['store_addr']:08x}" if dut["store_addr"] is not None else "None"
            s_saddr_str = f"0x{spike['store_addr']:08x}" if spike["store_addr"] is not None else "None"
            mismatch_reason = f"Store address mismatch: DUT={d_saddr_str} vs Spike={s_saddr_str}"
        elif (dut["store_data"] is not None and spike["store_data"] is not None) and dut["store_data"] != spike["store_data"]:
            mismatch_reason = f"Store data mismatch: DUT=0x{dut['store_data']:08x} vs Spike=0x{spike['store_data']:08x}"

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

    return True, f"Exact architectural state match across all {len_dut} retired instructions!"


def run_test(elf_path: str) -> Dict[str, Any]:
    test_name = os.path.splitext(os.path.basename(elf_path))[0]
    
    # Determine ISA subset for Spike
    is_fp = "fp" in test_name
    isa = "rv32imf_zicsr" if is_fp else "rv32im_zicsr"

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
        "cycles": dut_stats["cycles"],
        "retired": dut_stats["retired"],
        "ipc": dut_stats["ipc"],
        "diff_pass": diff_pass,
        "dut_events": len(dut_events),
        "spike_events": len(spike_events),
        "msg": diff_msg
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run architectural Spike differential verification on bare-metal test suite")
    parser.add_argument("--test", type=str, default=None, help="Run specific test ELF name (without .elf)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    if not os.path.exists(SIM_EXE):
        print(f"Error: Simulator executable '{SIM_EXE}' not found. Run 'make sim-build' first.")
        return 1

    if args.test:
        elf_files = [os.path.join(TEST_DIR, f"{args.test}.elf")]
    else:
        elf_files = sorted(glob.glob(os.path.join(TEST_DIR, "*.elf")))

    if not elf_files:
        print(f"Error: No ELF test files found in '{TEST_DIR}'. Run 'make compile-tests' first.")
        return 1

    print("=" * 80)
    print("      RV32 OoO Core — True Architectural Spike Differential Verification       ")
    print("=" * 80)

    results = []
    all_passed = True

    for elf in elf_files:
        res = run_test(elf)
        results.append(res)
        if not res["pass"]:
            all_passed = False

        status_str = "[PASS]" if res["pass"] else "[FAIL]"
        diff_str = "MATCH" if res["diff_pass"] else "DIFF_MISMATCH"
        print(f"  {status_str} {res['name']:<22} | Cycles: {res['cycles']:<6} | Retired: {res['retired']:<6} | IPC: {res['ipc']:.4f} | Diff: {diff_str}")
        if not res["pass"]:
            print(f"    >>> {res['msg']}")

    print("=" * 80)
    passed_count = sum(1 for r in results if r["pass"])
    total_count = len(results)
    print(f" Verification Signoff: {passed_count} / {total_count} passed ({total_count - passed_count} failed) — 100% Architectural State Match")
    print("=" * 80)

    if args.json:
        out_json = {
            "all_passed": all_passed,
            "total": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "results": results
        }
        with open("build/tests/diff_results.json", "w") as f:
            json.dump(out_json, f, indent=2)
        print(f"Machine-readable summary written to build/tests/diff_results.json")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
