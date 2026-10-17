#!/usr/bin/env python3
"""Turn the complete FP-profile Embench diagnostic into an auditable gate report.

This checks all 19 expected workloads, retains failures, and emits no score.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/qualification/embench-fp-full"
PROFILE = "rv32imf-zicsr-ilp32f"
METRICS = {
    "roi_cycles": r"\[Embench\] Benchmark executed in cycles: (\d+)",
    "total_cycles": r"^  Cycles\s+: (\d+)$",
    "retired_insns": r"^  Retired insns\s+: (\d+)$",
}


def metric(pattern: str, content: str) -> int | None:
    found = re.search(pattern, content, re.MULTILINE)
    return int(found.group(1)) if found else None


def main() -> int:
    source_path = BASE / "summary.json"
    if not source_path.is_file():
        raise SystemExit(f"missing {source_path}; run make qualify-embench-fp-dut")
    original = json.loads(source_path.read_text())
    grouped: dict[str, dict] = {}
    for record in original["records"]:
        grouped.setdefault(record["benchmark"], {})[record["profile"]] = record
    expected = sorted(path.name for path in
                      (ROOT / "software/embench/embench-iot/src").iterdir()
                      if path.is_dir() and list(path.glob("*.c")))
    problems: list[str] = []
    if original.get("selected_count") != 19 or len(expected) != 19:
        problems.append("expected exactly 19 selected workloads")
    if set(grouped) != set(expected):
        problems.append("recorded workload names differ from pinned Embench source")
    if not original.get("run_spike") or not original.get("run_dut"):
        problems.append("both Spike and DUT execution must be requested")
    for name, record in original.get("metadata", {}).items():
        if record.get("returncode") != 0:
            problems.append(f"metadata probe failed: {name}")
    results = []
    for name in expected:
        pair = grouped.get(name, {})
        native, target = pair.get("native"), pair.get(PROFILE)
        if native is None or target is None:
            problems.append(f"{name}: native or RV32 record missing")
            continue
        checks = {"native_build": native["build"]["returncode"] == 0,
                  "native_self_check": native.get("native", {}).get("returncode") == 0}
        for step in ("build", "strip", "attributes", "size", "disassembly", "spike", "dut"):
            checks[step] = target.get(step, {}).get("returncode") == 0
        checks["dut_self_check"] = target.get("dut", {}).get("self_check_pass") is True
        log_path = ROOT / target.get("dut", {}).get("log", "")
        dut_log = log_path.read_text() if log_path.is_file() else ""
        numbers = {key: metric(pattern, dut_log) for key, pattern in METRICS.items()}
        checks["metrics_present"] = all(value is not None for value in numbers.values())
        if not all(checks.values()):
            problems.append(f"{name}: failed {', '.join(k for k, ok in checks.items() if not ok)}")
        results.append({"workload": name, "checks": checks,
                        "elf_sha256": target.get("elf_sha256"),
                        "metrics": numbers,
                        "dut_log": target.get("dut", {}).get("log")})
    simulator = ROOT / "build/sim/rv32_ooo_sim"
    output = {"scope": "full-set functional diagnostic; no performance score",
              "all_passed": not problems,
              "selected_count": len(expected),
              "passed_count": sum(all(item["checks"].values()) for item in results),
              "source_summary_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
              "probe_sha256": original.get("probe_sha256"),
              "simulator_sha256": hashlib.sha256(simulator.read_bytes()).hexdigest()
              if simulator.is_file() else None,
              "problems": problems, "results": results}
    report_path = BASE / "dut-gate-report.json"
    report_path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Embench FP-profile DUT: {output['passed_count']}/{len(expected)} "
          f"functional checks passed; report: {report_path.relative_to(ROOT)}")
    for problem in problems:
        print("  " + problem)
    return 0 if output["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
