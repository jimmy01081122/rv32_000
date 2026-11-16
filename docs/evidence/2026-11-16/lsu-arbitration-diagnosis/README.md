# Arbitration diagnosis evidence — 2026-11-16

Read-only PID / FFT / statemate comparison between frozen A+B and arbitration v1.
Six observer on/off pairs, all 5,504,081 raw ROI cycles, per-PC/ordered retirement,
load lifecycles, paired store delays, independent VCD calibration and two actual-data
negative controls pass. This is not a new CPU candidate, full-family score or PPA.

See [findings and next proposal](../../../LSU_ARBITRATION_DIAGNOSIS.md).
`capture-summary.json`, `review-summary.json` and `schedule-comparison.json` are
convenience copies; inventory hashes bind the original controller outputs too.
All part files are at most 40 MiB. Verify from the repository root:

```sh
python3 experiments/lsu-arbitration-diagnosis-v1/archive.py --verify \
  --output docs/evidence/2026-11-16/lsu-arbitration-diagnosis
```

Only extract into a fresh review checkout after verification:

```sh
cat docs/evidence/2026-11-16/lsu-arbitration-diagnosis/arbitration-diagnosis.tar.gz.part* | tar -xz
```

The archive includes every compressed raw stream, unchanged off/on logs/profiles/
memory audits, relinked observer binaries/objects/sources, disassembly with tool
identity, selected frozen reference ELFs/results, the independent PID VCD extraction,
reviewers and schema. No raw stream is downsampled. Original generated RTL models
and runtime objects are reused from the preceding
[functional evidence](../lsu-arbitration-functional/README.md); full original VCD
provenance remains in [A+B evidence](../../2026-11-13/lsu-ab-complete/README.md) (dated November 13).
Restore those referenced inputs before rebuilding an observer. Review receipts use
absolute original build paths; source hashes and archive member paths are portable.
