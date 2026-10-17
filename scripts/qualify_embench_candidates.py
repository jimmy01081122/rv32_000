#!/usr/bin/env python3
"""Probe Embench build and execution with G1 or RV32IMF toolchains.

The FP profile uses a pinned RV32IMF toolchain and can check Spike and the DUT.
This diagnostic does not set a performance score or change the acceptance gate.
Exit 1 means at least one selected probe failed; inspect summary.json for scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
VENDOR = Path("software/embench/embench-iot")
CANDIDATES = ("cubic", "minver", "nbody", "st", "wikisort")
G1_PROFILES = {
    "legacy-im": ("rv32im_zicsr", "ilp32", ["-lgcc"]),
    "imf-ilp32f": ("rv32imf_zicsr", "ilp32f", ["-lgcc"]),
    "imf-ilp32f-libm": (
        "rv32imf_zicsr", "ilp32f",
        ["-Wl,--start-group", "-lm", "-lc", "-lgcc", "-Wl,--end-group"],
    ),
}
FP_PROFILE = ("rv32imf_zicsr", "ilp32f",
              ["-Wl,--start-group", "-lm", "-lc", "-lgcc", "-Wl,--end-group"])


def run(command: list[str], log: Path, timeout: int = 60) -> dict:
    try:
        result = subprocess.run(
            command, cwd=ROOT, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=timeout,
        )
        output = result.stdout
        code = result.returncode
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or b""
        output = partial.decode(errors="replace") if isinstance(partial, bytes) else partial
        output += f"\nTIMEOUT after {timeout}s\n"
        code = 124
    except OSError as exc:
        output, code = str(exc), 127
    log.write_text(output)
    displayed_log = log.relative_to(ROOT) if log.is_relative_to(ROOT) else log
    return {"command": command, "returncode": code, "log": str(displayed_log)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain", choices=("g1", "fp"), default="g1")
    parser.add_argument("--suite", choices=("missing", "full"), default="missing",
                        help="Probe the five missing workloads or all 19 upstream programs")
    parser.add_argument("--run-spike", action="store_true",
                        help="Run linked ELFs on the Spike reference simulator")
    parser.add_argument("--run-dut", action="store_true",
                        help="Run linked ELFs on the current DUT simulator")
    parser.add_argument("--bench", default="all", help="One upstream workload, or all")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    default_name = "embench-fp" if args.toolchain == "fp" else "embench"
    if args.suite == "full":
        default_name += "-full"
    if args.bench != "all":
        default_name += "-" + args.bench
    out = (args.out_dir or ROOT / "build/qualification" / default_name).resolve()
    out.mkdir(parents=True, exist_ok=True)
    target_prefix = "riscv-none-elf-" if args.toolchain == "fp" else "riscv32-unknown-elf-"
    profiles = {"rv32imf-zicsr-ilp32f": FP_PROFILE} if args.toolchain == "fp" else G1_PROFILES
    metadata = {}
    for name, command in {
        "repository": ["git", "rev-parse", "HEAD"],
        "embench": ["git", "-C", str(VENDOR), "rev-parse", "HEAD"],
        "native-gcc": ["gcc", "--version"],
        "riscv-gcc": [target_prefix + "gcc", "--version"],
        "multilib": [target_prefix + "gcc", "-print-multi-lib"],
        "defaults": [target_prefix + "gcc", "-Q", "--help=target"],
    }.items():
        metadata[name] = run(command, out / f"{name}.log")

    records = []
    if args.suite == "full":
        candidates = tuple(sorted(path.name for path in (ROOT / VENDOR / "src").iterdir()
                                  if path.is_dir() and list(path.glob("*.c"))))
        if len(candidates) != 19:
            parser.error(f"expected 19 pinned Embench workloads, found {len(candidates)}")
    else:
        candidates = CANDIDATES
    if args.bench != "all":
        if args.bench not in candidates:
            parser.error(f"{args.bench!r} is not in the selected suite")
        candidates = (args.bench,)
    for bench in candidates:
        src = VENDOR / "src" / bench
        sources = [str(path.relative_to(ROOT)) for path in sorted((ROOT / src).glob("*.c"))]
        common = ["-O3", "-DWARMUP_HEAT=1", "-DCPU_MHZ=1",
                  f"-I{VENDOR / 'support'}", f"-I{src}"]
        support = [str(VENDOR / "support/beebsc.c"), str(VENDOR / "support/main.c")]
        for profile in ("native", *profiles):
            prefix = out / f"{bench}-{profile}"
            elf = prefix.with_suffix(".elf")
            # A failed probe must never execute an ELF from an earlier attempt.
            elf.unlink(missing_ok=True)
            if profile == "native":
                board = VENDOR / "config/native/boards/default"
                chip = VENDOR / "config/native/chips/speed-test-gcc"
                native_std = ["-std=gnu11"] if args.toolchain == "fp" else []
                command = ["gcc", *native_std, *common, f"-I{board}", f"-I{chip}",
                           str(board / "boardsupport.c"), str(chip / "chipsupport.c"),
                           *support, *sources, "-o", str(elf), "-lm"]
            else:
                isa, abi, libs = profiles[profile]
                target_std = ["-std=gnu11"] if args.toolchain == "fp" else []
                port_sources = (["software/embench/fail_syscalls.c"]
                                if args.toolchain == "fp" else [])
                command = [target_prefix + "gcc", f"-march={isa}", f"-mabi={abi}",
                           *target_std,
                           *common, "-ffreestanding", "-nostartfiles", "-nostdlib",
                           "-Isoftware/embench", "-Isoftware/include",
                           "-Tsoftware/linker/link.ld", "software/crt0/crt0.S",
                           "software/embench/libc.c", *port_sources,
                           "software/embench/boardsupport.c",
                           *support, *sources, "-o", str(elf), *libs]
            record = {"benchmark": bench, "profile": profile,
                      "build": run(command, prefix.with_suffix(".build.log"))}
            if record["build"]["returncode"] == 0:
                if profile != "native" and args.toolchain == "fp":
                    # GCC's one-shot compile/link emits a random cc*.o FILE symbol.
                    # Remove unused local symbols so identical loadable programs
                    # have identical ELF hashes; retain HTIF symbols for Spike
                    # and the simulator's tohost exit detection.
                    record["strip"] = run(
                        [target_prefix + "strip", "--strip-unneeded",
                         "--keep-symbol=tohost", "--keep-symbol=fromhost", str(elf)],
                        prefix.with_suffix(".strip.log"))
                    if record["strip"]["returncode"] != 0:
                        records.append(record)
                        print(f"{bench:8s} {profile:18s} strip failed", flush=True)
                        continue
                record["elf_sha256"] = hashlib.sha256(elf.read_bytes()).hexdigest()
                if profile == "native":
                    record["native"] = run([str(elf)], prefix.with_suffix(".native.log"))
                else:
                    record["attributes"] = run(
                        [target_prefix + "readelf", "-h", "-A", str(elf)],
                        prefix.with_suffix(".attributes.log"))
                    record["size"] = run([target_prefix + "size", str(elf)],
                                         prefix.with_suffix(".size.log"))
                    record["disassembly"] = run(
                        [target_prefix + "objdump", "-d", str(elf)],
                        prefix.with_suffix(".dis.log"))
                    if args.run_spike:
                        record["spike"] = run(
                            ["spike", f"--isa={isa}",
                             "-m0x80000000:0x100000,0x10000000:0x1000", str(elf)],
                            prefix.with_suffix(".spike.log"), 120)
                    if args.run_dut:
                        record["dut"] = run(
                            [str(ROOT / "build/sim/rv32_ooo_sim"), f"+elf={elf}",
                             "+max-cycles=25000000"], prefix.with_suffix(".dut.log"), 180)
                        dut_output = prefix.with_suffix(".dut.log").read_text()
                        record["dut"]["self_check_pass"] = (
                            record["dut"]["returncode"] == 0
                            and ("Exit code: 0 (PASS)" in dut_output
                                 or "SIM_EXIT received with code: 0" in dut_output))
            records.append(record)
            states = {key: value["returncode"] for key, value in record.items()
                      if isinstance(value, dict) and "returncode" in value}
            print(f"{bench:8s} {profile:18s} {states}", flush=True)
    report = {"scope": "candidate diagnostics; no performance score or acceptance decision",
              "toolchain": args.toolchain,
              "suite": args.suite, "selected_count": len(candidates),
              "run_spike": args.run_spike, "run_dut": args.run_dut,
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "metadata": metadata, "records": records}
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    failed = any(item["returncode"] != 0 for item in metadata.values())
    failed |= any(value["returncode"] != 0 or value.get("self_check_pass") is False
                  for record in records for value in record.values()
                  if isinstance(value, dict) and "returncode" in value)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
