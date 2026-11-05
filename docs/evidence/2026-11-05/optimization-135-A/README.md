# Isolated A common-flow completion — 2026-11-05 UTC

A completes the shared-FPU/GRT/hold40/ready-guard research comparison. Both fresh
27-workload measurements pass 3,629 FP32 numerical checks and unchanged per-PC
retired work. This is global-route PPA research; the original frozen baseline
and current B RTL remain unchanged. Neither 1.20× performance goal is reached.

| A operating point | Embench19 time GM | Balanced FP32 time GM |
| --- | ---: | ---: |
| 10,000 ps / 100 MHz | 1.045829648× | 1.078255061× |
| 9,400 ps / 106.38 MHz | 0.765250431× | 0.737524030× |

Fixed 10 ns memory is observed after 18.8 ns at 9,400 ps. Area is
21,602.442420 µm², 1.002643220× same-flow baseline and 0.978321932× original.
Independent TT/SS/FF passes at 9,400/10,000 ps; actual 9,300 ps SS setup is
−52.245319 ps. Final FF hold is +16.905560 ps.

[Physical admission](physical-review.json), [common-clock admission](common-clock-review.json)
and [fastest-clock admission](fastest-clock-review.json) are readable copies of
identical archived reports. Full interpretation and next candidates are in the
[study report](../../../OPTIMIZATION_135_STUDY.md).

## Identity and contents

- Native source: `8a1c5820b32fed3c647e298f24bc4f0bde768dd4`.
- Frozen A workload source: `bf6702c6f4238aaf5f290356f3d0e0279f688f1e`.
- Archive-parent commit: `8a1c5820b32fed3c647e298f24bc4f0bde768dd4`; uncommitted packaging/review/documentation paths are explicitly recorded in the inventory. The native build ran earlier on its clean pinned source.
- Joined archive: **439,033,268 bytes**, **14 parts**, **810 file members**.
- Joined SHA256: `82e55623e293aa1b6dbde78be07706686a510863ada99714e68005f1a7ee9821`.

`copy-inventory.json` maps every archived file to its original repository working
path, bytes and SHA256. Part files are at most 32 MiB. The native subtree contains
three exact completed-stage checkpoint tarballs and their decoded-member receipts;
later independent corner trials are separate. The measurements subtree contains
all 54 new workload records, ELFs, logs, profiles and memory audits. Sources,
source-link/measurement/publication/archive controls, prior-reference verification,
environment receipts and failed recovery attempts are retained.

Original A functional qualification and shared-FPU implementation proof are reused
with fresh provenance checks; this is not a fresh full Spike run or full ISA/IEEE-754
conformance claim. The unchanged B/reference archive is at
[2026-10-29/lsu-b-complete-validation](../../2026-10-29/lsu-b-complete-validation/README.md),
whose inventory SHA256 is
`4a67509515d6c320b633c9f0d2e063c9e85b5697d8ac739637759253ef5e1920`.
All 1,327 stored and decoded reference entries were rechecked. The first 1/3/5
observer study remains in its separate October 30 archive.

## Verification and recovery

From the repository root:

```bash
python3 experiments/optimization-135-v1/verify_completion_archive.py docs/evidence/2026-11-05/optimization-135-A
```

The verifier checks all public checksums, the joined archive identity, the exact
member set and every decoded member without extraction. It passes a multipart
fixture and rejects corrupted/missing parts, wrong decoded hashes and duplicate
members. Archive integrity is separate from functional and physical admission.

To inspect the raw evidence, create a new extraction directory and concatenate
parts in filename order:

```bash
mkdir -p /tmp/rv32-A-completion
cat docs/evidence/2026-11-05/optimization-135-A/A-completion.tar.gz.part-* | tar -xz -C /tmp/rv32-A-completion
```

For native checkpoint inspection, extract each `native/physical-A-v*.tar.gz` into
a fresh directory; its matching checkpoint JSON records every original file/link.
Re-executing semantic reviewers requires restoring their original `build/` inputs
from this and the retained qualification/reference archives using the inventory
source paths, plus the pinned tools. The integrity command alone needs only Python.
Historical working gzip caches must be decompressed for old reviewers that open raw
paths directly. The original evidence archives have not been changed.

`review-environment/environment-final.json` is the final tool state: all four
original SIM/SYN/FP/ORFS image IDs restored, SIM/SYN/FP checks passed, main sparse
checkout disabled, no active container. Earlier cold-cache records describe
intermediate states. Only redundant image-save copies were deleted after exact
image restoration; native evidence remains. The initially paused completion
supervisor disappeared during restart after the 27-case measurement finished.
Its unobserved wrapper exit status is not invented; all per-case exits and raw
results were independently re-admitted after restart.
