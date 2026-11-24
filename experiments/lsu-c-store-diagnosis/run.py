"""Build a passive store observer or replay the 27 frozen C workloads."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C = ROOT / "build/experiments/lsu-c-head-v1"
MODEL = C / "build-v1/sim-normal"
EVIDENCE = ROOT / "docs/evidence/lsu-c-head-v1"
REF = C / "measurement-10000ps-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(str(message))


def build(out):
    out.mkdir(parents=True)
    published = json.loads((EVIDENCE / "review.json").read_text())
    normal_sha = published["provenance"]["normal_simulator_sha256"]
    require(sha(MODEL / "rv32_ooo_sim") == normal_sha, "different scored executable")
    compiler = subprocess.check_output(["g++", "-dumpfullversion"], text=True).strip()
    require(compiler == "11.4.0", "pinned GCC 11.4 required")
    harness = ROOT / "sim/tb/sim_main.cpp"
    header = HERE / "store_edges.h"
    manifest = json.loads((ROOT / "experiments/lsu-c-head-v1/manifest.json").read_text())
    require(sha(harness) == manifest["simulation_inputs_sha256"]["sim/tb/sim_main.cpp"], "harness drift")
    source = harness.read_text()
    edits = {
        '#include "core_roi_profile.h"': '#include "core_roi_profile.h"\n#include "store_edges.h"',
        "    CoreRoi::Profile core_roi;": '    CoreRoi::Profile core_roi;\n    StoreEdges::Observer stores(std::getenv("STORE_EDGES_OUT"));',
        "        // Sample memory requests from core": "        stores.sample(*top, fp_roi.active, cycles);\n\n        // Sample memory requests from core",
        "        if (retire_valid) {": "        stores.finish(*top, retire_valid, trap_valid, commit_pc, commit_insn);\n        if (retire_valid) {",
        "    if (core_profile_out.is_open()) core_roi.write(core_profile_out);": "    stores.save();\n    if (core_profile_out.is_open()) core_roi.write(core_profile_out);",
    }
    for old, new in edits.items():
        require(source.count(old) == 1, "ambiguous insertion " + old)
        source = source.replace(old, new)
    injected = out / "sim_main.cpp"
    injected.write_text(source)
    objects = [MODEL / f for f in ("sim_mem.o","verilated.o","verilated_vcd_c.o","Vrv32_ooo_core__ALL.a")]
    command = ["g++", "-std=c++14", "-DVM_TRACE=1", "-O2", "-I/usr/share/verilator/include",
               "-I/usr/share/verilator/include/vltstd", "-I" + str(MODEL), "-I" + str(HERE),
               "-I" + str(ROOT / "sim/tb"), "-c", injected, "-o", out / "sim_main.o"]
    with (out / "compiler.log").open("w") as log:
        def execute(args):
            subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT)
        execute(["g++", MODEL / "sim_main.o", *objects, "-o", out / "control"])
        require(sha(out / "control") == normal_sha, "original model relink differs from scored executable")
        execute(command)
        execute(["g++", out / "sim_main.o", *objects, "-o", out / "observer"])
    receipt = dict(control_sha256=normal_sha, observer_sha256=sha(out / "observer"), gcc=compiler,
                   generated_harness_sha256=sha(injected), inputs={str(p.relative_to(ROOT)): sha(p) for p in
                   [*objects, MODEL/"sim_main.o", MODEL/"Vrv32_ooo_core.h", harness, header, Path(__file__)]})
    (out / "build.json").write_text(json.dumps(receipt,indent=2)+"\n")


def counts(path):
    with path.open() as f:
        return {r["name"]: int(r["count"]) for r in csv.DictReader(f)}


def measure(out, row):
    family, name = row["family"], row["name"]
    ref = REF / family / name
    case = out / family / name
    case.mkdir(parents=True)
    command = list(row["execution"]["command"])
    command[0] = str(out / "observer")
    for option, path in [("+profile-core-roi=", case / "profile.json"), ("+memory-audit=", case / "memory.json")]:
        idx, = [i for i, arg in enumerate(command) if arg.startswith(option)]
        command[idx] = option + str(path)
    elf, = [Path(arg[5:]) for arg in command if arg.startswith("+elf=")]
    require(sha(elf) == row["elf_sha256"] and elf == ref / "input.elf", "frozen ELF changed")
    env = os.environ.copy()
    env.pop("STORE_EDGES_WHOLE", None)
    with (case / "dut.log").open("w") as log:
        subprocess.run(command, cwd=ROOT, env=dict(env, STORE_EDGES_OUT=str(case)),
                       stdout=log, stderr=subprocess.STDOUT, timeout=1200, check=True)
    for file, digest in [("dut.log",row["execution"]["log_sha256"]),("profile.json",row["profile_sha256"]),
                         ("memory.json",row["memory_audit_sha256"])]:
        require(sha(case / file) == sha(ref / file) == digest, name+" reference changed: "+file)
    print(f"{family}/{name} PASS", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=("build","run"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    out = a.out.resolve()
    require(out.is_relative_to(ROOT / "build"), "expected output under build/")
    if a.phase == "build":
        build(out)
        return
    b = json.loads((out / "build.json").read_text())
    require(sha(out / "observer") == b["observer_sha256"] and
            all(sha(ROOT / p)==h for p,h in b["inputs"].items()), "observer inputs drifted")
    reference = json.loads((EVIDENCE / "review.json").read_text())
    require(sha(REF / "summary.json") == reference["measurement_sha256"], "C summary drift")
    rows = json.loads((REF / "summary.json").read_text())["records"]
    require(len(rows) == 27, "incomplete reference corpus")
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        list(pool.map(lambda row: measure(out, row), rows))


if __name__ == "__main__":
    main()
