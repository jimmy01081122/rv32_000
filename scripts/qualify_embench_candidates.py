#!/usr/bin/env python3
"""Probe the five Embench candidates omitted by the legacy runner.

This diagnostic does not change the benchmark set, ABI or acceptance gate.
It records commands, logs and ELF hashes; native runs use upstream self-checks.
Exit 1 means at least one probe failed, not an RTL regression verdict.
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
PROFILES = {
    "legacy-im": ("rv32im_zicsr", "ilp32", ["-lgcc"]),
    "imf-ilp32f": ("rv32imf_zicsr", "ilp32f", ["-lgcc"]),
    "imf-ilp32f-libm": (
        "rv32imf_zicsr", "ilp32f",
        ["-Wl,--start-group", "-lm", "-lc", "-lgcc", "-Wl,--end-group"],
    ),
}


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
    return {"command": command, "returncode": code, "log": str(log)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "build/qualification/embench")
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for name, command in {
        "repository": ["git", "rev-parse", "HEAD"],
        "embench": ["git", "-C", str(VENDOR), "rev-parse", "HEAD"],
        "native-gcc": ["gcc", "--version"],
        "riscv-gcc": ["riscv32-unknown-elf-gcc", "--version"],
        "multilib": ["riscv32-unknown-elf-gcc", "-print-multi-lib"],
        "defaults": ["riscv32-unknown-elf-gcc", "-Q", "--help=target"],
    }.items():
        metadata[name] = run(command, out / f"{name}.log")

    records = []
    for bench in CANDIDATES:
        src = VENDOR / "src" / bench
        sources = [str(path) for path in sorted(src.glob("*.c"))]
        common = ["-O3", "-DWARMUP_HEAT=1", "-DCPU_MHZ=1",
                  f"-I{VENDOR / 'support'}", f"-I{src}"]
        support = [str(VENDOR / "support/beebsc.c"), str(VENDOR / "support/main.c")]
        for profile in ("native", *PROFILES):
            prefix = out / f"{bench}-{profile}"
            elf = prefix.with_suffix(".elf")
            # A failed probe must never execute an ELF from an earlier attempt.
            elf.unlink(missing_ok=True)
            if profile == "native":
                board = VENDOR / "config/native/boards/default"
                chip = VENDOR / "config/native/chips/speed-test-gcc"
                command = ["gcc", *common, f"-I{board}", f"-I{chip}",
                           str(board / "boardsupport.c"), str(chip / "chipsupport.c"),
                           *support, *sources, "-o", str(elf), "-lm"]
            else:
                isa, abi, libs = PROFILES[profile]
                command = ["riscv32-unknown-elf-gcc", f"-march={isa}", f"-mabi={abi}",
                           *common, "-ffreestanding", "-nostartfiles", "-nostdlib",
                           "-Isoftware/embench", "-Isoftware/include",
                           "-Tsoftware/linker/link.ld", "software/crt0/crt0.S",
                           "software/embench/libc.c", "software/embench/boardsupport.c",
                           *support, *sources, "-o", str(elf), *libs]
            record = {"benchmark": bench, "profile": profile,
                      "build": run(command, prefix.with_suffix(".build.log"))}
            if record["build"]["returncode"] == 0:
                record["elf_sha256"] = hashlib.sha256(elf.read_bytes()).hexdigest()
                if profile == "native":
                    record["native"] = run([str(elf)], prefix.with_suffix(".native.log"))
                else:
                    record["attributes"] = run(
                        ["riscv32-unknown-elf-readelf", "-h", "-A", str(elf)],
                        prefix.with_suffix(".attributes.log"))
                    record["size"] = run(["riscv32-unknown-elf-size", str(elf)],
                                         prefix.with_suffix(".size.log"))
                    record["disassembly"] = run(
                        ["riscv32-unknown-elf-objdump", "-d", str(elf)],
                        prefix.with_suffix(".dis.log"))
            records.append(record)
            states = {key: value["returncode"] for key, value in record.items()
                      if isinstance(value, dict) and "returncode" in value}
            print(f"{bench:8s} {profile:18s} {states}", flush=True)
    report = {"scope": "candidate build/native diagnostics; no target execution or performance score",
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "metadata": metadata, "records": records}
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    failed = any(item["returncode"] != 0 for item in metadata.values())
    failed |= any(value["returncode"] != 0
                  for record in records for value in record.values()
                  if isinstance(value, dict) and "returncode" in value)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
