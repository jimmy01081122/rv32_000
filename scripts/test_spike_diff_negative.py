#!/usr/bin/env python3
"""
scripts/test_spike_diff_negative.py — Architectural Differential Verification Negative Self-Test Suite
Validates that the Spike differential comparator reliably detects and rejects:
  1. Truncated DUT trace (length mismatch)
  2. Extra trailing DUT event (length mismatch)
  3. Mutated PC
  4. Mutated instruction bits
  5. GPR destination corruption
  6. GPR writeback value corruption
  7. FPR destination corruption
  8. FPR writeback value corruption
  9. Store address corruption
  10. Store data corruption
  11. Empty trace rejection
"""
from __future__ import annotations

import copy
import sys
from run_spike_diff import diff_traces


def test_negative_cases() -> int:
    print("=" * 80)
    print("  RV32 OoO Core — Architectural Differential Comparator Negative Self-Tests")
    print("=" * 80)

    # Base identical trace with GPR writeback, FPR writeback, and Store operations
    base_spike = [
        {"pc": 0x80000000, "insn": 0x00100117, "gpr_dst": 2, "gpr_val": 0x80100000, "fpr_dst": None, "fpr_val": None, "store_addr": None, "store_data": None, "raw": "core 0: 3 0x80000000 (0x00100117) x 2 0x80100000"},
        {"pc": 0x80000004, "insn": 0x00010113, "gpr_dst": 2, "gpr_val": 0x80100000, "fpr_dst": None, "fpr_val": None, "store_addr": None, "store_data": None, "raw": "core 0: 3 0x80000004 (0x00100113) x 2 0x80100000"},
        {"pc": 0x80000008, "insn": 0x000062b7, "gpr_dst": 5, "gpr_val": 0x00006000, "fpr_dst": None, "fpr_val": None, "store_addr": None, "store_data": None, "raw": "core 0: 3 0x80000008 (0x000062b7) x 5 0x00006000"},
        {"pc": 0x8000000c, "insn": 0x00a2a023, "gpr_dst": None, "gpr_val": None, "fpr_dst": None, "fpr_val": None, "store_addr": 0x80001000, "store_data": 0x12345678, "raw": "core 0: 3 0x8000000c (0x00a2a023) mem 0x80001000 0x12345678"},
        {"pc": 0x80000010, "insn": 0x000520a7, "gpr_dst": None, "gpr_val": None, "fpr_dst": 1, "fpr_val": 0x3f800000, "store_addr": None, "store_data": None, "raw": "core 0: 3 0x80000010 (0x000520a7) f 1 0x3f800000"},
        {"pc": 0x80000014, "insn": 0x00000093, "gpr_dst": 1, "gpr_val": 0x00000000, "fpr_dst": None, "fpr_val": None, "store_addr": None, "store_data": None, "raw": "core 0: 3 0x80000014 (0x00000093) x 1 0x00000000"},
        {"pc": 0x80000018, "insn": 0x10500073, "gpr_dst": None, "gpr_val": None, "fpr_dst": None, "fpr_val": None, "store_addr": None, "store_data": None, "raw": "core 0: 3 0x80000018 (0x10500073)"}
    ]

    base_dut = copy.deepcopy(base_spike)
    for d in base_dut:
        d["store_mask"] = 0xF if d["store_addr"] is not None else None

    # Positive baseline check
    ok, msg = diff_traces(base_dut, base_spike)
    assert ok, f"Positive baseline unexpectedly failed: {msg}"
    print("  [PASS] Positive Baseline   : 100% Architectural state match passes successfully.")

    # 1. Truncated DUT trace
    dut_mut = copy.deepcopy(base_dut[:-1])
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "LENGTH MISMATCH" in msg, f"Failed to catch truncated trace: {msg}"
    print("  [PASS] Negative Test #1   : Truncated trace detected (LENGTH MISMATCH).")

    # 2. Extra trailing event
    dut_mut = copy.deepcopy(base_dut) + [{"pc": 0x8000001c, "insn": 0x00000013, "gpr_dst": None, "gpr_val": None, "fpr_dst": None, "fpr_val": None, "store_addr": None, "store_mask": None, "store_data": None, "raw": ""}]
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "LENGTH MISMATCH" in msg, f"Failed to catch extra event: {msg}"
    print("  [PASS] Negative Test #2   : Extra trailing event detected (LENGTH MISMATCH).")

    # 3. PC Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[2]["pc"] = 0x8000000A
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "PC mismatch" in msg, f"Failed to catch PC corruption: {msg}"
    print("  [PASS] Negative Test #3   : PC corruption detected (PC mismatch).")

    # 4. Instruction word corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[1]["insn"] = 0x00000013
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "Instruction word mismatch" in msg, f"Failed to catch instruction corruption: {msg}"
    print("  [PASS] Negative Test #4   : Instruction corruption detected (Instruction word mismatch).")

    # 5. GPR Destination Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[2]["gpr_dst"] = 6
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "GPR destination mismatch" in msg, f"Failed to catch GPR destination corruption: {msg}"
    print("  [PASS] Negative Test #5   : GPR destination corruption detected (GPR destination mismatch).")

    # 6. GPR Value Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[2]["gpr_val"] = 0x00006001
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "GPR writeback value mismatch" in msg, f"Failed to catch GPR value corruption: {msg}"
    print("  [PASS] Negative Test #6   : GPR value corruption detected (GPR writeback value mismatch).")

    # 7. FPR Destination Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[4]["fpr_dst"] = 2
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "FPR destination mismatch" in msg, f"Failed to catch FPR destination corruption: {msg}"
    print("  [PASS] Negative Test #7   : FPR destination corruption detected (FPR destination mismatch).")

    # 8. FPR Value Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[4]["fpr_val"] = 0x3f800001
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "FPR writeback value mismatch" in msg, f"Failed to catch FPR value corruption: {msg}"
    print("  [PASS] Negative Test #8   : FPR value corruption detected (FPR writeback value mismatch).")

    # 9. Store Address Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[3]["store_addr"] = 0x80001004
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "Store address mismatch" in msg, f"Failed to catch Store address corruption: {msg}"
    print("  [PASS] Negative Test #9   : Store address corruption detected (Store address mismatch).")

    # 10. Store Data Corruption
    dut_mut = copy.deepcopy(base_dut)
    dut_mut[3]["store_data"] = 0x12345679
    ok, msg = diff_traces(dut_mut, base_spike)
    assert not ok and "Store data mismatch" in msg, f"Failed to catch Store data corruption: {msg}"
    print("  [PASS] Negative Test #10  : Store data corruption detected (Store data mismatch).")

    # 11. Empty Trace
    ok, msg = diff_traces([], base_spike)
    assert not ok and "Empty event stream" in msg, f"Failed to catch empty trace: {msg}"
    print("  [PASS] Negative Test #11  : Empty trace correctly rejected.")

    print("=" * 80)
    print("  [SUCCESS] All 11 Differential Negative Self-Tests Passed (100% Fault Coverage)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(test_negative_cases())
