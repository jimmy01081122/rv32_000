#!/usr/bin/env python3
"""
scripts/test_spike_diff_negative.py — Differential Verification Comparator Negative Self-Test
Validates that the Spike differential comparator reliably catches:
  1. Truncated DUT trace (length mismatch)
  2. Mutated PC
  3. Mutated instruction bits
  4. Empty DUT trace
  5. Extra stray DUT event
"""

import sys
import copy
from run_spike_diff import diff_traces

def test_negative_cases():
    # Construct a baseline synthetic trace
    base_spike = [
        {"pc": 0x80000000, "insn": 0x00100117, "raw": "core 0: 0x80000000 (0x00100117) auipc sp, 0x100"},
        {"pc": 0x80000004, "insn": 0x00010113, "raw": "core 0: 0x80000004 (0x00010113) mv sp, sp"},
        {"pc": 0x80000008, "insn": 0x000062b7, "raw": "core 0: 0x80000008 (0x000062b7) lui t0, 0x6"},
        {"pc": 0x8000000c, "insn": 0x3002a073, "raw": "core 0: 0x8000000c (0x3002a073) csrs mstatus, t0"},
        {"pc": 0x80000010, "insn": 0x00000093, "raw": "core 0: 0x80000010 (0x00000093) li ra, 0"},
        {"pc": 0x80000014, "insn": 0x00000193, "raw": "core 0: 0x80000014 (0x00000193) li gp, 0"},
        {"pc": 0x80000018, "insn": 0x00000213, "raw": "core 0: 0x80000018 (0x00000213) li tp, 0"},
        {"pc": 0x8000001c, "insn": 0x00000293, "raw": "core 0: 0x8000001c (0x00000293) li t0, 0"},
        {"pc": 0x80000020, "insn": 0x00000313, "raw": "core 0: 0x80000020 (0x00000313) li t1, 0"},
        {"pc": 0x80000024, "insn": 0x00000393, "raw": "core 0: 0x80000024 (0x00000393) li t2, 0"}
    ]

    base_dut = [
        {"pc": 0x80000000, "insn": 0x00100117, "gpr_dst": 2, "gpr_val": 0x80000100, "raw": "core 0: 0x80000000 (0x00100117) x2=0x80000100"},
        {"pc": 0x80000004, "insn": 0x00010113, "gpr_dst": 2, "gpr_val": 0x80000100, "raw": "core 0: 0x80000004 (0x00010113) x2=0x80000100"},
        {"pc": 0x80000008, "insn": 0x000062b7, "gpr_dst": 5, "gpr_val": 0x00006000, "raw": "core 0: 0x80000008 (0x000062b7) x5=0x00006000"},
        {"pc": 0x8000000c, "insn": 0x3002a073, "gpr_dst": 0, "gpr_val": 0x00000000, "raw": "core 0: 0x8000000c (0x3002a073)"},
        {"pc": 0x80000010, "insn": 0x00000093, "gpr_dst": 1, "gpr_val": 0x00000000, "raw": "core 0: 0x80000010 (0x00000093) x1=0x00000000"},
        {"pc": 0x80000014, "insn": 0x00000193, "gpr_dst": 3, "gpr_val": 0x00000000, "raw": "core 0: 0x80000014 (0x00000193) x3=0x00000000"},
        {"pc": 0x80000018, "insn": 0x00000213, "gpr_dst": 4, "gpr_val": 0x00000000, "raw": "core 0: 0x80000018 (0x00000213) x4=0x00000000"},
        {"pc": 0x8000001c, "insn": 0x00000293, "gpr_dst": 5, "gpr_val": 0x00000000, "raw": "core 0: 0x8000001c (0x00000293) x5=0x00000000"},
        {"pc": 0x80000020, "insn": 0x00000313, "gpr_dst": 6, "gpr_val": 0x00000000, "raw": "core 0: 0x80000020 (0x00000313) x6=0x00000000"},
        {"pc": 0x80000024, "insn": 0x00000393, "gpr_dst": 7, "gpr_val": 0x00000000, "raw": "core 0: 0x80000024 (0x00000393) x7=0x00000000"}
    ]

    # Baseline match check
    ok, msg = diff_traces(base_dut, base_spike)
    assert ok, f"Baseline match unexpectedly failed: {msg}"
    print("  [PASS] Positive baseline: Valid identical traces match successfully.")

    # Negative Test 1: Truncated DUT trace (delete last event)
    trunc_dut = base_dut[:-1]
    ok, msg = diff_traces(trunc_dut, base_spike)
    assert not ok and "LENGTH MISMATCH" in msg, f"Negative Test 1 failed to catch truncated trace: ok={ok}, msg={msg}"
    print("  [PASS] Negative Test 1: Truncated DUT trace correctly rejected (LENGTH MISMATCH detected).")

    # Negative Test 2: Extra DUT event (Spike shorter)
    extra_dut = base_dut + [{"pc": 0x80000028, "insn": 0x00000413, "gpr_dst": 8, "gpr_val": 0, "raw": "core 0: 0x80000028 (0x00000413) x8=0"}]
    ok, msg = diff_traces(extra_dut, base_spike)
    assert not ok and "LENGTH MISMATCH" in msg, f"Negative Test 2 failed to catch extra event: ok={ok}, msg={msg}"
    print("  [PASS] Negative Test 2: Extra trailing DUT event correctly rejected (LENGTH MISMATCH detected).")

    # Negative Test 3: Mutated PC in DUT event #5
    mut_pc_dut = copy.deepcopy(base_dut)
    mut_pc_dut[5]["pc"] = 0x80000018 # should be 0x80000014
    ok, msg = diff_traces(mut_pc_dut, base_spike)
    assert not ok and "PC mismatch" in msg, f"Negative Test 3 failed to catch mutated PC: ok={ok}, msg={msg}"
    print("  [PASS] Negative Test 3: Corrupted PC correctly rejected (PC MISMATCH detected).")

    # Negative Test 4: Mutated instruction word in DUT event #3
    mut_insn_dut = copy.deepcopy(base_dut)
    mut_insn_dut[3]["insn"] = 0x3002a077 # bit flip in CSR instruction
    ok, msg = diff_traces(mut_insn_dut, base_spike)
    assert not ok and "Instruction word mismatch" in msg, f"Negative Test 4 failed to catch instruction bit corruption: ok={ok}, msg={msg}"
    print("  [PASS] Negative Test 4: Corrupted instruction word correctly rejected (INSN MISMATCH detected).")

    # Negative Test 5: Empty DUT trace
    ok, msg = diff_traces([], base_spike)
    assert not ok and "Empty event stream" in msg, f"Negative Test 5 failed to catch empty trace: ok={ok}, msg={msg}"
    print("  [PASS] Negative Test 5: Empty trace correctly rejected (EMPTY STREAM detected).")

    print("\n" + "=" * 80)
    print(" All 5 Negative Comparator Self-Tests PASSED Successfully!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_negative_cases()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Negative Self-Test Assertion Failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error in negative self-test: {e}", file=sys.stderr)
        sys.exit(1)
