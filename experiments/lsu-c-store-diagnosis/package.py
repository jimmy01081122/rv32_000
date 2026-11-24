"""Package the store edge evidence for an independent review in an empty build tree."""
import argparse
import gzip
import json
from pathlib import Path
import tarfile
from run import C, MODEL, REF, ROOT, sha


def package(capture, dest):
    review = json.loads((dest/"review.json").read_text())
    if not review["passed"] or review["verified_workloads"] != 27:
        raise ValueError("complete review required")
    files = {REF/"summary.json", *(capture/n for n in ("control","observer","sim_main.cpp","compiler.log","build.json"))}
    files.update(ROOT/p for p in json.loads((capture/"build.json").read_text())["inputs"] if p.startswith("build/"))
    files.add(MODEL/"rv32_ooo_sim")
    for case in review["workload"]:
        directory = capture/case["family"]/case["name"]
        files.update(directory/n for n in ("dut.log","profile.json","memory.json","examples.csv","counts.csv"))
    files.update(p for p in (capture/"controls").rglob("*") if p.is_file() and p.suffix != ".vcd")
    files.update([ROOT/"build/tests/store_forwarding.elf", C/"qualification-v1/interface/sw.elf", C/"qualification-v1/interface/fsw.elf"])
    archive = dest/"store-edges.tar.gz"
    records = []
    with archive.open("xb") as base, gzip.GzipFile(fileobj=base,mode="wb",filename="",mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode="w|") as tar:
            for path in sorted(files):
                if path.is_symlink() or not path.is_file():
                    raise ValueError("missing regular capture artifact "+str(path))
                name = str(path.relative_to(ROOT))
                records.append(dict(path=name,bytes=path.stat().st_size,sha256=sha(path)))
                info = tar.gettarinfo(str(path),arcname=name)
                info.mtime=info.uid=info.gid=0
                info.uname=info.gname=""
                with path.open("rb") as f: tar.addfile(info,f)
    inventory = dict(passed=True,archive=archive.name,archive_bytes=archive.stat().st_size,
                     archive_sha256=sha(archive),records=records)
    (dest/"inventory.json").write_text(json.dumps(inventory,indent=2)+"\n")
    with (dest/"SHA256SUMS").open("x") as out:
        for p in sorted(dest.iterdir()):
            if p.name!="SHA256SUMS": out.write(sha(p)+"  "+p.name+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("capture",type=Path)
    p.add_argument("dest",type=Path)
    args=p.parse_args()
    package(args.capture.resolve(),args.dest.resolve())
