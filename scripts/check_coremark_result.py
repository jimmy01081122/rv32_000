#!/usr/bin/env python3
"""
scripts/check_coremark_result.py — Independent CoreMark Verifier and Parser
Independently verifies raw simulation log, checks CRC consistency,
and recomputes cycle-accurate CoreMark/MHz equivalent score.
"""

import sys
import re
import json
import argparse
from typing import Dict, Any, Optional

KNOWN_CRCS = {
    # 2K Performance Run (seed1=0, seed2=0, seed3=0x66, size 666)
    "PERFORMANCE_RUN": {
        "seedcrc": 0xe9f5,
        "crclist": 0xe714,
        "crcmatrix": 0x1fd7,
        "crcstate": 0x8e3a,
        "crcfinal": 0xfcaf
    },
    # 2K Validation Run (seed1=0x3415, seed2=0x3415, seed3=0x66, size 666)
    "VALIDATION_RUN": {
        "seedcrc": 0x18f2,
        "crclist": 0xe3c1,
        "crcmatrix": 0x0747,
        "crcstate": 0x8d84,
        "crcfinal": 0xe3c1
    }
}

def parse_coremark_output(log_text: str) -> Dict[str, Any]:
    """Parse raw CoreMark simulator console log."""
    data: Dict[str, Any] = {
        "run_type": "UNKNOWN",
        "iterations": 0,
        "total_ticks": 0,
        "total_time_secs": 0,
        "compiler_version": "",
        "compiler_flags": "",
        "memory_location": "",
        "seedcrc": None,
        "crclist": None,
        "crcmatrix": None,
        "crcstate": None,
        "crcfinal": None,
        "validated": False,
        "benchmark_finished": False,
        "sim_exit_code": None,
        "sim_cycles": 0,
        "sim_retired": 0,
        "sim_ipc": 0.0,
        "recomputed_score": 0.0,
        "crc_match": False,
        "overall_pass": False,
        "errors": []
    }

    if "2K performance run" in log_text:
        data["run_type"] = "PERFORMANCE_RUN"
    elif "2K validation run" in log_text:
        data["run_type"] = "VALIDATION_RUN"

    # Regex extractions
    m_ticks = re.search(r"Total ticks\s*:\s*(\d+)", log_text)
    if m_ticks:
        data["total_ticks"] = int(m_ticks.group(1))

    m_time = re.search(r"Total time \(secs\)\s*:\s*(\d+)", log_text)
    if m_time:
        data["total_time_secs"] = int(m_time.group(1))

    m_iter = re.search(r"Iterations\s*:\s*(\d+)", log_text)
    if m_iter:
        data["iterations"] = int(m_iter.group(1))

    m_cver = re.search(r"Compiler version\s*:\s*(.+)", log_text)
    if m_cver:
        data["compiler_version"] = m_cver.group(1).strip()

    m_cflags = re.search(r"Compiler flags\s*:\s*(.+)", log_text)
    if m_cflags:
        data["compiler_flags"] = m_cflags.group(1).strip()

    m_mem = re.search(r"Memory location\s*:\s*(.+)", log_text)
    if m_mem:
        data["memory_location"] = m_mem.group(1).strip()

    m_seed = re.search(r"seedcrc\s*:\s*0x([0-9a-fA-F]+)", log_text)
    if m_seed:
        data["seedcrc"] = int(m_seed.group(1), 16)

    m_crclist = re.search(r"\[0\]crclist\s*:\s*0x([0-9a-fA-F]+)", log_text)
    if m_crclist:
        data["crclist"] = int(m_crclist.group(1), 16)

    m_crcmat = re.search(r"\[0\]crcmatrix\s*:\s*0x([0-9a-fA-F]+)", log_text)
    if m_crcmat:
        data["crcmatrix"] = int(m_crcmat.group(1), 16)

    m_crcstate = re.search(r"\[0\]crcstate\s*:\s*0x([0-9a-fA-F]+)", log_text)
    if m_crcstate:
        data["crcstate"] = int(m_crcstate.group(1), 16)

    m_crcfinal = re.search(r"\[0\]crcfinal\s*:\s*0x([0-9a-fA-F]+)", log_text)
    if m_crcfinal:
        data["crcfinal"] = int(m_crcfinal.group(1), 16)

    if "Correct operation validated" in log_text:
        data["validated"] = True

    if "[CoreMark] Benchmark finished cleanly." in log_text:
        data["benchmark_finished"] = True

    m_exit = re.search(r"SIM_EXIT received with code:\s*(\d+)", log_text)
    if m_exit:
        data["sim_exit_code"] = int(m_exit.group(1))

    m_cyc = re.search(r"Cycles\s*:\s*(\d+)", log_text)
    if m_cyc:
        data["sim_cycles"] = int(m_cyc.group(1))

    m_ret = re.search(r"Retired insns\s*:\s*(\d+)", log_text)
    if m_ret:
        data["sim_retired"] = int(m_ret.group(1))

    m_ipc = re.search(r"IPC\s*:\s*([0-9.]+)", log_text)
    if m_ipc:
        data["sim_ipc"] = float(m_ipc.group(1))

    # Extract declared target CPU frequency if present
    m_freq = re.search(r"Configured Target CPU Frequency:\s*(\d+)\s*MHz", log_text)
    data["target_freq_mhz"] = int(m_freq.group(1)) if m_freq else 1

    # Independent CRC Check on per-algorithm verified seeds
    if data["run_type"] in KNOWN_CRCS:
        exp = KNOWN_CRCS[data["run_type"]]
        crc_ok = (
            data["seedcrc"] == exp["seedcrc"] and
            data["crclist"] == exp["crclist"] and
            data["crcmatrix"] == exp["crcmatrix"] and
            data["crcstate"] == exp["crcstate"]
        )
        data["crc_match"] = crc_ok
        if not crc_ok:
            data["errors"].append(
                f"CRC mismatch! Expected {exp}, got "
                f"{{seed: {hex(data['seedcrc'] or 0)}, list: {hex(data['crclist'] or 0)}, "
                f"matrix: {hex(data['crcmatrix'] or 0)}, state: {hex(data['crcstate'] or 0)}}}"
            )
    else:
        data["errors"].append(f"Unrecognized run type: {data['run_type']}")

    # Independent CoreMark/MHz calculation
    if data["total_ticks"] > 0 and data["iterations"] > 0:
        data["recomputed_score"] = round((data["iterations"] * 1000000.0) / data["total_ticks"], 4)
    else:
        data["errors"].append("Invalid total_ticks or iterations for score calculation")

    data["validated"] = ("Correct operation validated" in log_text) or data["crc_match"]

    # Check for non-timing errors reported by CoreMark itself
    if "ERROR!" in log_text:
        for line in log_text.splitlines():
            if "ERROR!" in line and "Must execute for at least 10 secs" not in line:
                data["errors"].append(f"CoreMark runtime error: {line.strip()}")

    # Overall verdict
    data["overall_pass"] = (
        data["validated"] and
        data["benchmark_finished"] and
        data["sim_exit_code"] == 0 and
        data["crc_match"] and
        len(data["errors"]) == 0
    )

    return data

def main():
    parser = argparse.ArgumentParser(description="Independent CoreMark Result Verifier")
    parser.add_argument("log_file", help="Path to raw simulation log file (or - for stdin)")
    parser.add_argument("--mode", choices=["development", "official"], default="development",
                        help="Verification mode: 'development' (cycle-scaled DSE) or 'official' (requires >=10s execution)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--require-score", type=float, default=None, help="Require minimum CoreMark/MHz score")
    args = parser.parse_args()

    if args.log_file == "-":
        content = sys.stdin.read()
    else:
        with open(args.log_file, "r", encoding="utf-8") as f:
            content = f.read()

    result = parse_coremark_output(content)

    if args.mode == "official":
        if result["total_time_secs"] < 10:
            result["overall_pass"] = False
            result["errors"].append(
                f"Official CoreMark reporting requires execution time >= 10s (measured: {result['total_time_secs']}s)"
            )

    if args.require_score is not None:
        if result["recomputed_score"] < args.require_score:
            result["overall_pass"] = False
            result["errors"].append(
                f"Score {result['recomputed_score']} is below required threshold {args.require_score}"
            )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("=" * 70)
        print("          INDEPENDENT COREMARK VERIFICATION REPORT")
        print("=" * 70)
        print(f"  Reporting Mode   : {args.mode.upper()}")
        print(f"  Run Type         : {result['run_type']}")
        print(f"  Iterations       : {result['iterations']}")
        print(f"  Compiler Flags   : {result['compiler_flags']}")
        print(f"  Target Frequency : {result['target_freq_mhz']} MHz")
        print(f"  Measured Ticks   : {result['total_ticks']} cycles")
        print(f"  Elapsed Time     : {result['total_time_secs']} seconds")
        print(f"  Simulation Total : {result['sim_cycles']} cycles")
        print(f"  Retired Insns    : {result['sim_retired']}")
        print(f"  Simulation IPC   : {result['sim_ipc']:.4f}")
        print(f"  CoreMark/MHz     : {result['recomputed_score']:.4f}")
        print(f"  CRC Verification : {'MATCH (PASS)' if result['crc_match'] else 'MISMATCH (FAIL)'}")
        print(f"  Exit Code        : {result['sim_exit_code']}")
        print(f"  Overall Status   : {'PASS' if result['overall_pass'] else 'FAIL'}")
        if result["errors"]:
            print("\nErrors / Warnings:")
            for err in result["errors"]:
                print(f"  - {err}")
        print("=" * 70)

    sys.exit(0 if result["overall_pass"] else 1)

if __name__ == "__main__":
    main()
