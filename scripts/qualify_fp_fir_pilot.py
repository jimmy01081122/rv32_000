#!/usr/bin/env python3
"""Build and numerically probe one provisional FIR case on host, Spike and DUT.

This is a qualification pilot, not a frozen input/tolerance or FP32 score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CMSIS = ROOT / "build/qualification/fp-balanced/CMSIS-DSP"
SOURCE = ROOT / "software/fp_bench/fir_pilot.c"
FIR = CMSIS / "Source/FilteringFunctions/arm_fir_f32.c"
INIT = CMSIS / "Source/FilteringFunctions/arm_fir_init_f32.c"
CHECKSUM = re.compile(r"FP FIR PILOT PASS checksum=([0-9a-f]{8})")


def run(command: list[str], log: Path, timeout: int = 120) -> dict:
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                text=True, timeout=timeout)
        output, code = result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or b""
        output = partial.decode(errors="replace") if isinstance(partial, bytes) else partial
        output += f"\nTIMEOUT after {timeout}s\n"
        code = 124
    except OSError as exc:
        output, code = str(exc), 127
    log.write_text(output)
    return {"command": command, "returncode": code,
            "log": str(log.relative_to(ROOT))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dut", action="store_true")
    args = parser.parse_args()
    out = ROOT / "build/qualification/fp-balanced/fir-pilot"
    out.mkdir(parents=True, exist_ok=True)
    source_check = run(["python3", "scripts/prepare_fp_sources.py"], out / "sources.log")
    if source_check["returncode"]:
        parser.exit(1, f"FP source check failed; see {source_check['log']}\n")

    native = out / "fir-native"
    target = out / "fir-rv32.elf"
    native.unlink(missing_ok=True)
    target.unlink(missing_ok=True)
    common = ["-std=gnu11", "-O3", "-ffp-contract=off", "-D__GNUC_PYTHON__",
              f"-I{CMSIS / 'Include'}", f"-I{CMSIS / 'PrivateInclude'}"]
    sources = [str(SOURCE), str(FIR), str(INIT)]
    native_build = run(["gcc", *common, "-DFP_BENCH_HOST", *sources,
                        "-o", str(native)], out / "native-build.log")
    target_build = run([
        "riscv-none-elf-gcc", *common, "-march=rv32imf_zicsr", "-mabi=ilp32f",
        "-ffreestanding", "-nostartfiles", "-nostdlib", "-Isoftware/include",
        "-Tsoftware/linker/link.ld", "software/crt0/crt0.S",
        "software/embench/fail_syscalls.c", *sources, "-o", str(target),
        "-Wl,--start-group", "-lm", "-lc", "-lgcc", "-Wl,--end-group",
    ], out / "rv32-build.log")
    report = {"scope": "provisional FIR diagnostic; no suite score",
              "fixture": "32 taps, 256 samples, deterministic modular fractions",
              "reference": "double direct convolution plus terminal FIR state",
              "absolute_tolerance": 0.00001,
              "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "source_check": source_check,
              "native_build": native_build, "target_build": target_build,
              "run_dut": args.run_dut}
    if native_build["returncode"] == 0 and target_build["returncode"] == 0:
        report["strip"] = run([
            "riscv-none-elf-strip", "--strip-unneeded", "--keep-symbol=tohost",
            "--keep-symbol=fromhost", str(target)], out / "strip.log")
        if report["strip"]["returncode"] == 0:
            report["elf_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            report["attributes"] = run([
                "riscv-none-elf-readelf", "-h", "-A", str(target)],
                out / "attributes.log")
            report["native"] = run([str(native)], out / "native.log")
            report["spike"] = run([
                "spike", "--isa=rv32imf_zicsr",
                "-m0x80000000:0x100000,0x10000000:0x1000", str(target)],
                out / "spike.log")
            if args.run_dut:
                simulator = ROOT / "build/sim/rv32_ooo_sim"
                if not simulator.is_file():
                    parser.error("missing simulator; run make sim-build")
                report["simulator_sha256"] = hashlib.sha256(simulator.read_bytes()).hexdigest()
                report["dut"] = run([str(simulator), f"+elf={target}",
                                     "+max-cycles=25000000"], out / "dut.log", 180)

    checksums = {}
    # Spike does not forward this project's MMIO console. Its exit status still
    # checks every output against the independent double reference in the ELF.
    for name in ("native", "dut"):
        if name not in report:
            continue
        output = (out / f"{name}.log").read_text()
        match = CHECKSUM.search(output)
        checksums[name] = match.group(1) if match else None
    report["checksums"] = checksums
    report["passed"] = bool(checksums) and all(
        result["returncode"] == 0 for result in report.values()
        if isinstance(result, dict) and "returncode" in result
    ) and all(value is not None for value in checksums.values()) \
        and len(set(checksums.values())) == 1 \
        and (not args.run_dut or "Exit status    : PASS (0)" in (out / "dut.log").read_text())
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FIR pilot", "PASS" if report["passed"] else "FAIL", checksums,
          report.get("elf_sha256"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
