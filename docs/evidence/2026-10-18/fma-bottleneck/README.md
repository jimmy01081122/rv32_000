# Approved fast policy and FIR/BiCG instruction/wait diagnosis

Measured source: `5065e7f32f4201a7c4e7af77c1b7eb6cdda0b1c7`; working tree clean at start and end.
Asia/Taipei: 2026-10-18T09:40:40.339278+08:00 to 2026-10-18T09:45:37.082414+08:00.
UTC timestamps, image IDs, complete commands and exit codes are in `run-context.json`.
All RTL is unchanged from `581ee86f1bd55bc6eff7cc123c660ab94446eb6f`.
The user approved `-ffp-contract=fast -fno-fast-math` as the FP32 main policy;
the qualifier now defaults to fast, with explicit off retained for sensitivity checks.

| Kernel | Instructions removed | Extra no-retire cycles | Cycles saved | off/fast |
| --- | ---: | ---: | ---: | ---: |
| FIR | 8,192 | 7,177 | 1,015 | 1.013659x |
| BiCG | 3,192 | 3,066 | 126 | 1.005266x |

The instruction reduction is entirely FMUL+FADD to FMA contraction. Architectural
load/store, branch and other instruction counts are unchanged. FIR exposes load
response-buffer waits; BiCG exposes store-retirement ack waits while the existing
data path is occupied. All four runs have zero heavy-FP/FP-EX0/completion backpressure.
[Full explanation and cycle tables](../../../FMA_BOTTLENECK_REVIEW.md).

Cycles are partitioned without overlap: body retire, one closing marker, and
no-retire categories. The observed commit-window length equals the CSR ROI cycle
difference in all four cases. Overlapping queue, source-wait and bus events are
reported separately and must not be added to the cycle partition. The observations
locate current waits; they do not establish gains from an unimplemented CPU change.

## Validation

- Complete paired off/fast qualification: **8/8 native, Spike and DUT per mode**.
- Approved implicit-default fast entry: **8/8 native, Spike and DUT**. Fixtures,
  executed ELF hashes, numerical results and ROI cycles match explicit fast.
- All **16 executed ELFs and complete DUT stdout files** match the prior
  [contraction qualification](../fma-contraction/README.md) byte-for-byte.
- Four core-observed cases each replay with observers disabled and with the
  pre-observer simulator: all stdout values, checksums and timing match. Observer
  output only adds the existing `FP ROI` line; core-observed stdout matches the
  standard paired qualification exactly.
- All pre-edge head PC/instruction/retirement checks against registered commit,
  and FP IQ valid/ready/ROB ownership checks: **zero mismatches**.
- All observed PCs/words match executed `.text`; symbol and executed `.text`
  sections are byte-identical for all four cases.
- **18 Python controls**, two C++ profile assertion programs, **3,400 finite FMA**
  exact result/flags cases, lint/build, directed **18/18**, Spike diff **18/18** pass.

No RTL optimization or new PPA result is included. The complete Embench suite was
not rerun this time; its previous 19/19 evidence retains its original source and
coverage scope. Formal AP5B baseline and 1.20x/1.10x targets remain unassessed.

## Files and provenance

- `summary.json`: four profiles, checks, commands, output hashes, exact instruction
  deltas, and the identity `removed = saved cycles + extra no-retire cycles`.
- `cases/<kernel>/<mode>/core-profile.json`: raw profile, mutually exclusive cycle
  categories, overlapping event counts, and per-PC retirement/head-wait counts.
- `cases/<kernel>/<mode>/kernel-disassembly.txt`: named kernel instruction listings.
- `assembly-audit.json`: symbol/executed text hashes and every observed PC/word check.
- `default-fast-audit.json`, `prior-qualification-audit.json`: identity checks for
  the approved default and the pre-observer qualification.
- `paired/*-summary.json`, `comparison.json`, `default-fast/summary.json`,
  `finite/summary.json`: complete current qualifications with source identities.
- `log-index.json`: original command log path, exact SHA-256/size and archive path.
  Identical bytes are shared with immutable older archives; `shared` identifies
  those external references. All locally copied stdout is under `raw/`.
- `input-references.json`: identical prior fixtures/headers and finite FMA vectors.
  Upstream SVM data remains covered by the prior archive's Apache-2.0 license.
- `regenerable-artifacts.json`: binary, stack-report and full-disassembly identities;
  these remain in ignored build output. Unstripped metadata is not promised
  byte-identical on rebuild.

The post-run read-only audit helper is checked in as
[`audit_fp_bottleneck_artifacts.py`](../../../../scripts/audit_fp_bottleneck_artifacts.py).
`assembly-audit.json` identifies it by content hash separately from the measured
source commit. It reads existing artifacts and does not rerun or alter the CPU.

Reproduce with pinned images/sources from the repository root:

```bash
make fetch-fp-sources
python3 -m unittest discover -s scripts -p 'test_fp*.py'
make profile-fp-bottlenecks JOBS=4
make qualify-fp-balanced-dut JOBS=4
make test diff-test JOBS=4
python3 scripts/audit_fp_bottleneck_artifacts.py
```

The optional `--baseline-simulator` argument to `profile_fp_bottlenecks.py` adds
pre-observer model replay; its binary hash is retained here. Model on/off replay
is always performed. Both C++ profile assertion programs can be built with
`g++ -std=c++17 -Wall -Wextra -Werror -Isim/tb` and executed in the pinned image;
complete invocations are recorded in the run context.

From this directory: `sha256sum -c SHA256SUMS`. The manifest includes every local
archive file plus all referenced shared inputs/logs, so missing external evidence
fails verification.
