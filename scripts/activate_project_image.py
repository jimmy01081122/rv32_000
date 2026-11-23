"""Restore one pinned project image from this host's verified cold cache."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCKER = ["env", *[arg for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS",
          "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH") for arg in ("-u", key)],
          "docker", "--host=unix:///var/run/docker.sock"]
IMAGES = {
    "fp": ("rv32ooo-fp:p1", "2140263677b3a378d5cab75a3d0d4fd285ddb38a1a5a1f81f5cf97db024a02d5"),
    "sim": ("rv32ooo-sim:g1", "0d80d39df2f24dc60a77387242f781edc1cc67f53865719981e01b5b5a989d26"),
    "syn": ("rv32ooo-syn:g1", "b56c1e8635d9baabe4d64ecdd9c63d0685da9aa11075b69bc6bd665ca52bea2b"),
    "orfs": ("rv32ooo-orfs:8359fde-flat", "92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33"),
}


def image_id(tag):
    result = subprocess.run(DOCKER + ["image", "inspect", "--format", "{{.Id}}", tag],
                            text=True, capture_output=True)
    if result.returncode and "No such" not in result.stderr:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def load_one(archive, tag, digest):
    with tarfile.open(archive, "r|gz") as stream:
        manifest = next(json.load(stream.extractfile(m)) for m in stream if m.name == "manifest.json")
    row, = [r for r in manifest if tag in (r.get("RepoTags") or [])]
    if row["Config"].split("/")[-1] != digest:
        raise ValueError("archive config differs from pinned image")
    wanted = {row["Config"], *row["Layers"]}
    with tempfile.TemporaryFile(dir="/tmp") as selected:
        with tarfile.open(fileobj=selected, mode="w|") as out, tarfile.open(archive, "r|gz") as stream:
            for member in stream:
                if member.name in wanted:
                    if not member.isfile():
                        raise ValueError("unexpected non-file archive member")
                    out.addfile(member, stream.extractfile(member))
                    wanted.remove(member.name)
            if wanted:
                raise ValueError("missing image layers")
            data = json.dumps([dict(row, RepoTags=[tag])]).encode()
            member = tarfile.TarInfo("manifest.json")
            member.size = len(data)
            out.addfile(member, io.BytesIO(data))
        selected.seek(0)
        subprocess.run(DOCKER + ["load"], stdin=selected, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", choices=IMAGES)
    key = parser.parse_args().image
    tag, digest = IMAGES[key]
    expected = "sha256:" + digest
    existing = image_id(tag)
    if existing and existing != expected:
        raise ValueError("existing tag points to another image")
    if not existing:
        if key == "orfs":
            archive = ROOT / "build/tool-cache/orfs-8359fde.tar.gz"
            receipt = json.loads(archive.with_suffix("").with_suffix(".json").read_text())
            if receipt["image_id"] != expected:
                raise ValueError("ORFS receipt differs from pinned image")
            checksum = receipt["archive_sha256"]
        else:
            archive = ROOT / "build/experiments/lsu-ab-v1/image-cache-v2/rv32-inactive-images.tar.gz"
            checksum = "4ff27f145499c096165164968d12580c9799895f03f6cdd6cdc063beb4614139"
        with archive.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != checksum:
                raise ValueError("archive checksum mismatch")
        if key == "orfs":
            subprocess.run(DOCKER + ["load", "--input", str(archive)], check=True)
        else:
            load_one(archive, tag, digest)
        if image_id(tag) != expected:
            raise ValueError("restored image ID mismatch")
    print(tag, expected)


if __name__ == "__main__":
    main()
