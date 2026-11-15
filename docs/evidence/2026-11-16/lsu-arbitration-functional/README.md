# LSU arbitration: complete functional and cycle experiment

Published 2026-11-16 (Asia/Taipei); runs completed 2026-11-13. This bundle
qualifies the first bounded-load arbitration implementation functionally and
measures all frozen workloads. **Candidate timing and area are unmeasured.**
The original baseline is unchanged and the candidate is not promoted.

[Full report](../../../LSU_ARBITRATION_REVIEW.md) · [Critical-path inventory](../../../CRITICAL_PATHS.md)

## Complete comparison

All values below use nominal 10,000 ps CPU cycles and fixed 10,000 ps I response,
I initiation interval and D response. Original ELF bytes and per-PC retired work
match. Candidate ASIC system-time qualification still requires fresh physical work.

| Version | Embench19 / original baseline | Balanced FP32 / original baseline |
| --- | ---: | ---: |
| Qualified A+B parent | 1.073943× | 1.088248× |
| Bounded arbitration | 1.070636× | 1.101087× |
| Candidate / A+B | 0.996920× | 1.011798× |

Ten cases improve, fourteen regress, three tie. PID cycles fall 8,256 → 7,238
(−12.3304%), but FFT rises 3.5506% and statemate 7.3252%. DSP / matrix-ML
subgroups relative to A+B are 1.024551× / 0.999204×, with equal subgroup weights.
Both 1.20× goals remain unmet. No subset score substitutes for a complete family.

The 140-case parent and candidate unit suites pass, as do three actual RTL
negative controls. Clean normal/assertion models pass 18 directed, 18 Spike,
48 interface, 58 memory and 3,400 finite FMA checks. All27 workloads pass with
3,629 numerical values, fixed-memory audits, matching retired work and source
provenance. All four pipeline stages record actual exit 0. These are targeted
checks, not full ISA/IEEE-754 conformance.

The first development unit controller expected an SVA failure message, but the
pin-driven check rejected the unbounded mutant earlier. Its failed receipt and
exact checker are preserved. A fresh full run admits the intended early failure
message; no RTL or acceptance condition was bypassed.

## Timing boundary

The included parent reports contain 240 sampled setup/hold paths: TT/SS/FF,
9,400/10,000 ps, four path groups. Their bytes match the published parent archive
and original independent collector; minima match admitted closure.
SS 9,400 ps worst setup is INT EX0 → data-memory address **+8.20 ps**, followed
by FPU arithmetic **+59.46 ps**. Minimum FF hold is **+17.58 ps** on ROB event
counter → commit trace. These are **A+B measurements**, not the modified candidate.

## Contents and identities

- Archive: `arbitration-functional.tar.gz`, **10,700,349 bytes**.
- SHA-256: `fec938fdc6f86a43417b4c0fe007c185b5e732782625a57eca52337056c7d485`.
- **1,611 payloads**, **129,178,094 decoded bytes**.
- Clean CPU/build/qualification/measurement source: `669c8ee5a6f6eecbb71e30094bf18fd97cadf8df`.
- Report/tool archive parent: `3daf816422c85a079a0ff9a948f8b8e4c320dcd4`.
- Qualified A+B parent: `49122fb9b37292c9a2c2dc4b4b70226909304293`.

The archive contains both unit attempts and RTL mutants, new normal/assertion
executables and generated models, full regression and workload records, parent
build/qualification/measurement evidence, frozen baseline measurement/fixtures,
source contracts/reviewers, and raw parent timing reports. Exact log and profile
identities are recorded. The unchanged
[A+B physical completion](../../2026-11-13/lsu-ab-complete/README.md) remains the
physical reference; its full native checkpoints are not duplicated here.

`parent-comparison.json` rechecks both entire measurements and reconciles 54
profiles. Exclusive wait-position deltas sum to each cycle difference; they are
not independently removable stalls or complete dependency-chain explanations.

## Verify

From the repository root, Python 3 standard library is sufficient to validate
the public file set, hashes and every decoded payload without extracting:

```sh
python3 experiments/lsu-load-arb-v1/verify_archive.py docs/evidence/2026-11-16/lsu-arbitration-functional
```

Full functional reanalysis additionally needs the repository history and the
recorded input paths; execution reruns need the pinned toolchain. The verifier
checks archive integrity, while the embedded review records functional admission.
No new CPU optimization beyond this arbitration rule is selected by this archive.
