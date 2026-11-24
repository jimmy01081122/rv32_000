"""Materialize the 34 large A+B construction files retained in the local checkpoints."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "scripts/baseline_contract.py").exists())
AB = ROOT / "build/experiments/lsu-ab-v1"
INVENTORY = ROOT / "docs/evidence/2026-11-13/lsu-ab-complete/copy-inventory.json"


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def restore(destination):
    destination = destination.resolve()
    pins = {r["source"]: r["sha256"] for r in json.loads(INVENTORY.read_text())["records"]}
    count = total = 0
    for stage in ("v1", "v2", "v4"):
        receipt = AB / "checkpoints" / ("physical-AB-" + stage + "-checkpoint.json")
        if sha(receipt) != pins[str(receipt.relative_to(ROOT))]:
            raise ValueError("changed checkpoint receipt")
        metadata = json.loads(receipt.read_text())
        archive = receipt.parent / metadata["archive"]
        if sha(archive) != pins[str(archive.relative_to(ROOT))] or not metadata["passed"]:
            raise ValueError("changed checkpoint archive")
        wanted = {r["path"]: r for r in metadata["records"] if r["kind"] == "file" and r["bytes"] > 2**20}
        with tarfile.open(archive, "r|gz") as stream:
            for member in stream:
                row = wanted.pop(member.name, None)
                if row is None:
                    continue
                target = destination / member.name
                if (not member.isfile() or member.size != row["bytes"] or not target.is_relative_to(destination)
                        or target.resolve() != target):
                    raise ValueError("unexpected file type or path " + member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
                        temporary = Path(out.name)
                        try:
                            shutil.copyfileobj(stream.extractfile(member), out)
                            out.flush()
                            if sha(temporary) != row["sha256"]:
                                raise ValueError("archive content differs " + member.name)
                            temporary.chmod(member.mode & 0o777)
                            os.link(temporary, target)
                        finally:
                            temporary.unlink()
                if not target.is_file() or sha(target) != row["sha256"]:
                    raise ValueError("existing target differs " + str(target))
                count += 1
                total += member.size
        if wanted:
            raise ValueError("checkpoint is missing files")
    if count != 34 or total != 1304115494:
        raise ValueError("unexpected A+B cache inventory")
    print(f"Verified {count} files, {total} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=AB / "native")
    restore(parser.parse_args().destination)
