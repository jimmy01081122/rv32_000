"""Pack reproducible local measurements and their reference inputs for C."""
import argparse
import gzip
import json
from pathlib import Path
import tarfile
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "scripts/baseline_contract.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
from baseline_contract import load, sha

BASE = ROOT / "build/experiments/lsu-c-head-v1"


def package(out):
    review = json.loads((out / "review.json").read_text())
    if not review["passed"] or not json.loads((BASE / "unit/summary.json").read_text())["passed"]:
        raise ValueError("complete reviewed measurement and pin controls required")
    paths = set()
    for stage in ("qualification-v1", "measurement-10000ps-v1", "build-v1", "unit", "lowering"):
        for p in (BASE / stage).rglob("*"):
            if not p.is_file():
                continue
            if stage in ("build-v1", "unit") and p.suffix not in (".log", ".json", ".dat") and p.name != "rv32_ooo_sim":
                continue
            paths.add(p)
    paths.update(BASE / f for f in ("contract.log", "provenance.log", "score-controls.log", "lowering-driver.log"))
    cache = ROOT / "build/tool-cache"
    paths.update(cache / name for name in (
        "check-switch.py", "switch.json", "park_physical.py", "park-physical.log", "orfs-8359fde.json",
        "load-orfs.log", "platform-check.log", "load-fp.log", "load-sim.log", "activate-syn.log",
        "temporary-ab-files.json", "replay-ab.log"))
    paths.add(BASE / "tools/activate_project_image.py")
    paths.add(BASE / "tools/structural.ys")
    paths.update((ROOT / "build/tests").glob("*.elf"))
    parent = ROOT / "build/experiments/lsu-rob-room-v1/measurement-10000ps-v1"
    paths.add(parent / "summary.json")
    for row in load()["workloads"]:
        paths.add(parent / row["family"] / row["name"] / "profile.json")
        paths.add(ROOT / row["source_elf"])
    records = []
    archive = out / "functional.tar.gz"
    with archive.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w|") as tar:
            for p in sorted(paths):
                if p.is_symlink() or not p.is_file():
                    raise ValueError("unexpected raw input " + str(p))
                name = str(p.relative_to(ROOT))
                records.append(dict(path=name, bytes=p.stat().st_size, sha256=sha(p)))
                info = tar.gettarinfo(str(p), arcname=name)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                with p.open("rb") as src:
                    tar.addfile(info, src)
    inventory = dict(passed=True, source_commit=review["source_commit"], archive=archive.name,
                     archive_bytes=archive.stat().st_size, archive_sha256=sha(archive), records=records)
    with (out / "inventory.json").open("x") as manifest:
        json.dump(inventory, manifest, indent=2)
        manifest.write("\n")
    with (out / "SHA256SUMS").open("x") as sums:
        for p in sorted(out.iterdir()):
            if p.name != "SHA256SUMS":
                sums.write(sha(p) + "  " + p.name + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    package(parser.parse_args().directory.resolve())
