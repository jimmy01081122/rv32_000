"""Compare real ROOM and C ROB ports at each side of the response clock edge."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "scripts/baseline_contract.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
from baseline_contract import sha
from qualify_fp_balanced import run

PARENT = "c2d7239412d44578de8c2449a7b1462f8eaa9486"
ROB = "rtl/rob/rv32_ooo_rob.sv"
TYPES = "rtl/pkg/rv32_ooo_types.sv"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "build"):
        parser.error("choose a fresh build directory")
    out.mkdir(parents=True)
    sources = Path(__file__).resolve().parent
    version = subprocess.check_output(["verilator", "--version"], text=True).strip()
    if not version.startswith("Verilator 4.038 "):
        raise ValueError("pinned Verilator required")
    report = dict(verilator=version, parent=PARENT, passed=False, records=[],
                  inputs={str(p.relative_to(ROOT)): sha(p) for p in
                          [Path(__file__).resolve(), sources / "head_load_top.sv", sources / "test_head_load.cpp",
                           ROOT / ROB, ROOT / TYPES, ROOT / "rtl/pkg/rv32_ooo_params.sv"]})
    summary = out / "summary.json"

    def step(name, args, expected_failure=False):
        log = out / (name + ".log")
        execution = run([str(a) for a in args], log, 180)
        ok = execution["returncode"] == 0
        if expected_failure:
            ok = execution["returncode"] == 1 and "FAIL head response timing" in log.read_text()
        report["records"].append(dict(name=name, passed=ok, execution=execution))
        summary.write_text(json.dumps(report, indent=2) + "\n")
        if not ok:
            raise ValueError("failed " + name)

    for variant in ("parent", "candidate"):
        directory = out / variant
        command = ["verilator", "--cc", "--exe", "--assert", "--top-module", "head_load_top",
                   "--Mdir", directory, "-Wall", "-Wno-UNUSED", "-Wno-PINCONNECTEMPTY"]
        inputs = [ROOT / path for path in (TYPES, ROB)]
        if variant == "parent":
            inputs = [out / p.name for p in inputs]
            for path, source in zip((TYPES, ROB), inputs):
                source.write_bytes(subprocess.check_output(["git", "show", PARENT + ":" + path], cwd=ROOT))
            command.append("+define+ROOM_PARENT")
        step(variant + "-generate", command + [ROOT / "rtl/pkg/rv32_ooo_params.sv", *inputs,
                                               sources / "head_load_top.sv", sources / "test_head_load.cpp"])
        step(variant + "-build", ["make", "-j2", "-C", directory, "-f", "Vhead_load_top.mk"])
        exe = directory / "Vhead_load_top"
        step(variant + "-timing", [exe, variant])
        opposite = "candidate" if variant == "parent" else "parent"
        step(variant + "-reject-" + opposite, [exe, opposite], expected_failure=True)
    report["passed"] = True
    summary.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
