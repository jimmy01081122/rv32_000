# A+B complete research qualification

2026-11-13 (Asia/Taipei). All functional, common-flow physical and full-workload
operating-point reviews pass. The original frozen baseline remains unchanged;
both independent 1.20× performance goals remain unmet. See the
[complete report](../../../LSU_AB_REVIEW.md) and [architecture map](../../../ARCHITECTURE_MAP.md).

## Qualified results

| A+B point | Embench19 time speedup | Balanced FP32 time speedup | Workloads / numerical values |
| --- | ---: | ---: | --- |
| 10,000 ps / 100 MHz | 1.073943× | 1.088248× | 27/27, 3,629 |
| 9,400 ps / 106.38 MHz | 0.775970× | 0.740353× | 27/27, 3,629 |

The 10,000 ps memory service policy is identical at both points: I response,
I initiation interval and D response. At 9,400 ps the observed response is
sampled after 18,800 ps. Scores use cycles × period; per-PC retired work and
original ELF bytes match the baseline. These are two measured operating points,
not an exhaustive frequency search.

ASAP7 TT construction, the same proven shared FPU, hold40 and one ready guard
pass independent TT/SS/FF global-route review. Cell area is
**21,663.036900 µm²**, **0.981066× original** and **1.005456× same-flow baseline**.
The original-area ratio includes flow changes. All tested 9,400–10,000 ps points
pass; actual adjacent 9,300 ps fails SS setup at −91.798569 ps. At 9,400 ps,
SS setup is +8.201440 ps and minimum FF hold +17.579993 ps. Overflow and antenna
violations are zero. This is global-route research qualification, not detailed
routing or tape-out signoff.

Functional qualification includes 332 pin-driven cases across baseline/A/B/AB,
three negative controls, 18 directed, 18 Spike, 48 assertion-enabled interface,
58 fixed-time controls and 3,400 finite FMA cases. The shared-FPU implementation
proof is two-state equivalence after reset; full ISA/IEEE-754 coverage remains
separate. The earlier functional archive is retained unchanged within this bundle.

PID waveforms reproduce original output, profiles and memory audits. All ROI
cycles are represented in selected raw signals. Across 512 retired iterations,
510 steady intervals grow from 14 to 16 cycles because early store eligibility
makes the existing store priority delay the next load. All 2,048 retired loop
arithmetic operations per variant retain one-cycle heavy-unit latency. The
+1,020 steady-cycle difference is offset by six boundary cycles, exactly
reconciling the +1,014 total. No new arbitration or divider RTL is included.

## Archive and provenance

- **15 ordered parts**, each at most 32 MiB.
- Joined archive: **487,440,823 bytes**.
- SHA-256: `90f912b84c74000bd5f7bbd352abd022f95681cdb90d6b1cfecd0cb31d6537a6`.
- **1,121 outer payloads**, **1,210,572,431 decoded bytes**; nested
  checkpoint and prior-functional archives retain their own inventories.
- Archive parent: `08a59bf218746b48070a9dd58ef7bb7497ba3e9b`.
- CPU, functional qualification and 100 MHz: `3f079c1c3d7b53c50beb13bc2d8bf366ac42999f`.
- Native synthesis: `52675e2364b78f0443951ff57267bea77223ac2e`.
- Native physical stages: `f66e12baf034113070c298006595d7292aa911bd`.
- Fresh 9,400 ps measurement: `f1d58d319d3b82171f79bd85987df485e6cba52f`;
  both recorded start and end trees are clean.
- Complete-review recovery: `1f9acf4603e946e53a609c7d919553030b69f5de`.

The bundle retains native stage checkpoints, mapping/lowering/link evidence,
independent corner reports, both full measurements, source contracts/reviewers,
PID captures' logs/audits/profiles, every selected ROI signal and the exact A/AB
normal executables/generated models. Full-program VCD files remain optional local
artifacts; the captured models and waveform scripts permit reproduction. They
are not required to reanalyze the archived ROI evidence.

The existing full FPU proof is referenced through the unchanged
[B completion archive](../../2026-10-29/lsu-b-complete-validation/README.md),
whose inventory SHA-256 is
`4a67509515d6c320b633c9f0d2e063c9e85b5697d8ac739637759253ef5e1920`.
The separately admitted [functional milestone](../../2026-11-09/lsu-ab-functional/README.md)
is embedded with its inventory and raw data, not relabeled retroactively.

Successful environment restoration records the three exact original image IDs,
smoke checks, eight restored historical files, full checkout restoration and
removal of the disposable native container. Runtime/storage failures remain
separate records. Tool-image backup tarballs are local operational artifacts,
not embedded here; pinned tool/platform identities remain in the evidence.

The initial completion controller records an actual review failure: Python's
integer histogram keys were directly compared to JSON's string keys. The
unchanged numerical data and full raw-signal replay agree after comparison in
the same JSON representation. `fastest-review-recovery.json` records the fresh
successful exit; its controls admit original data and reject changed histogram
counts or total cycles. The old failed controller/log remain unchanged.
`complete-review.json` records the final admission.

## Verify without extraction

From the repository root, Python 3 and its standard library are sufficient:

```sh
python3 experiments/lsu-ab-v1/verify_completion_archive.py docs/evidence/2026-11-13/lsu-ab-complete
```

This checks the complete public file set, every part, joined hash/size and every
decoded outer member, including safe paths and duplicate rejection. Individual
native checkpoints were independently decoded and checked by the physical
review. `SHA256SUMS` also covers this README and the directly readable reviews.
Archive integrity is distinct from functional/physical admission.

For inspection in a fresh directory:

```sh
mkdir ab-evidence-unpack
cat docs/evidence/2026-11-13/lsu-ab-complete/AB-completion.tar.gz.part-* | tar -xz -C ab-evidence-unpack
```

Full reruns additionally require the pinned simulation/physical tools, original
fixture paths and referenced historical archives. The review scripts preserve
source/model/ELF identities and fail if those inputs differ. Do not combine
results from different variants or change the frozen memory policy.
