#!/usr/bin/env python3
"""Check or fetch the pinned source files for the selected FP32 kernels.

Sources stay under the ignored build/ tree. This command never changes a pin
to follow a tag: a moved tag or modified local checkout fails qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/qualification/fp-balanced"
POLY_ARCHIVE = ROOT / "build/qualification/polybench-c-4.2.1-beta.tar.gz"
POLY_ROOT = ROOT / "build/qualification/polybench-c-4.2.1-beta"
POLY_URL = "https://sourceforge.net/projects/polybench/files/polybench-c-4.2.1-beta.tar.gz/download"
POLY_SHA256 = "426519ee8443a5f2175de6a3e9328cda8917a5e33053d0e8f59855ab56d689a4"

GIT_SOURCES = {
    "CMSIS-DSP": {
        "url": "https://github.com/ARM-software/CMSIS-DSP.git",
        "tag": "v1.18.0",
        "commit": "4b6f26593e9d3b24a9bc93b3646a3a859238eae2",
        "files": (
            "LICENSE", "Include/arm_math.h", "PrivateInclude/arm_compiler_specific.h",
            "Include/dsp/controller_functions.h", "Include/dsp/filtering_functions.h",
            "Include/dsp/svm_functions.h",
            "Source/FilteringFunctions/arm_fir_f32.c",
            "Source/FilteringFunctions/arm_fir_init_f32.c",
            "Source/FilteringFunctions/arm_biquad_cascade_df2T_f32.c",
            "Source/FilteringFunctions/arm_biquad_cascade_df2T_init_f32.c",
            "Source/ControllerFunctions/arm_pid_init_f32.c",
            "Source/SVMFunctions/arm_svm_linear_predict_f32.c",
            "Source/SVMFunctions/arm_svm_linear_init_f32.c",
            "Testing/Source/Tests/SVMF32.cpp",
            "Testing/Patterns/DSP/SVM/SVMF32/Dims1_s16.txt",
            "Testing/Patterns/DSP/SVM/SVMF32/Params1_f32.txt",
            "Testing/Patterns/DSP/SVM/SVMF32/Samples1_f32.txt",
            "Testing/Patterns/DSP/SVM/SVMF32/Reference1_s32.txt",
        ),
    },
    "kissfft": {
        "url": "https://github.com/mborgerding/kissfft.git",
        "tag": "131.2.0",
        "commit": "7bce4153c6bc8aba2db0e889e576f9d00505cbe1",
        "files": ("COPYING", "kiss_fft.c", "kiss_fft.h", "_kiss_fft_guts.h", "kiss_fft_log.h"),
    },
}

POLY_FILES = (
    "LICENSE.txt", "utilities/polybench.c", "utilities/polybench.h",
    "linear-algebra/blas/gemm/gemm.c", "linear-algebra/blas/gemm/gemm.h",
    "linear-algebra/kernels/bicg/bicg.c", "linear-algebra/kernels/bicg/bicg.h",
    "linear-algebra/solvers/cholesky/cholesky.c",
    "linear-algebra/solvers/cholesky/cholesky.h",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(*args: str) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def check_git(name: str, pin: dict, fetch: bool) -> dict:
    path = BASE / name
    if not path.exists():
        if not fetch:
            raise ValueError(f"missing {path.relative_to(ROOT)}; use --fetch")
        command("git", "clone", "--depth", "1", "--branch", pin["tag"],
                pin["url"], str(path))
    head = command("git", "-C", str(path), "rev-parse", "HEAD")
    if head != pin["commit"]:
        raise ValueError(f"{name}: HEAD {head} differs from pinned {pin['commit']}")
    if command("git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"):
        raise ValueError(f"{name}: tracked source files were modified")
    for relative in pin["files"]:
        target = path / relative
        if not target.is_file() and fetch:
            data = subprocess.check_output(["git", "-C", str(path), "show",
                                            f"{pin['commit']}:{relative}"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            mode = command("git", "-C", str(path), "ls-tree", pin["commit"], "--", relative).split()[0]
            target.chmod(0o755 if mode == "100755" else 0o644)
        if not target.is_file():
            raise ValueError(f"{name}: missing {relative}; use --fetch")
        expected = command("git", "-C", str(path), "rev-parse", f"{pin['commit']}:{relative}")
        if command("git", "hash-object", str(target)) != expected:
            raise ValueError(f"{name}: source content differs from pin: {relative}")
    return {"commit": head, "path": str(path.relative_to(ROOT)),
            "files_checked": len(pin["files"])}


def check_polybench(fetch: bool) -> dict:
    if not POLY_ARCHIVE.is_file():
        if not fetch:
            raise ValueError(f"missing {POLY_ARCHIVE.relative_to(ROOT)}; use --fetch")
        POLY_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(POLY_URL, timeout=120) as response:
            POLY_ARCHIVE.write_bytes(response.read())
    archive_hash = sha256(POLY_ARCHIVE.read_bytes())
    if archive_hash != POLY_SHA256:
        raise ValueError(f"PolyBench archive SHA-256 mismatch: {archive_hash}")
    with tarfile.open(POLY_ARCHIVE, "r:gz") as archive:
        for relative in POLY_FILES:
            member = archive.getmember(f"polybench-c-4.2.1-beta/{relative}")
            if not member.isfile():
                raise ValueError(f"PolyBench file is not regular: {relative}")
            stream = archive.extractfile(member)
            assert stream is not None
            expected = stream.read()
            target = POLY_ROOT / relative
            if not target.exists() and fetch:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
            if not target.is_file() or target.read_bytes() != expected:
                raise ValueError(f"PolyBench source missing or modified: {relative}")
    return {"archive_sha256": archive_hash,
            "path": str(POLY_ROOT.relative_to(ROOT)), "files_checked": len(POLY_FILES)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch missing sources at their pinned versions")
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    try:
        results = {name: check_git(name, pin, args.fetch)
                   for name, pin in GIT_SOURCES.items()}
        results["PolyBench-C"] = check_polybench(args.fetch)
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        parser.exit(1, f"FP source qualification failed: {exc}\n")
    report = {"scope": "source identity only; no functional or numerical pass",
              "sources": results}
    (BASE / "source-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, result in results.items():
        print(f"{name}: pinned source OK ({result['files_checked']} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
