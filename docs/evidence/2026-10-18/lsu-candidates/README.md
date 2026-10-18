# Representative LSU study and separate interface failures

Measured source: `3513c0cc8528796e0900e8040fee6a6c4bbf05dc`; source/tree and image identities in
`run-context.json`. Clean working tree at start/end, unchanged RTL/sim source and
unchanged simulator executable SHA-256.
Asia/Taipei: 2026-10-18T10:02:20.833170+08:00 to 2026-10-18T10:15:13.593263+08:00.
The normal-response study was preregistered in `protocol-at-measurement.md`.
Current decisions and tradeoffs: [LSU review](../../../LSU_OPTIMIZATION_REVIEW.md).

## Normal-response study: 18/18 PASS

Fixed crc32, matmult-int, wikisort, minver, FIR and BiCG at configured data-response
delays 1/2/4 cycles, 1 MiB RAM, no random delay. The same previously qualified ELFs
and inputs are used at every delay. FP32 remains fast/no-fast-math; Embench keeps
its original compiler policy, precision, scaling and warmup. Every case passes its
program self-check; FP32 additionally passes unchanged independent numerical checks.
All six nominal observer-off replays match the qualified output, and all profile
trace/layout checks have zero mismatches. Architectural instruction mixes are
unchanged across delays. 18 existing + 7 new Python controls pass.

| Case | delay 1 cycles | delay 2 cycles | delay 4 cycles | delay 4/1 slowdown |
| --- | ---: | ---: | ---: | ---: |
| crc32 | 5,402,220 | 5,576,480 | 6,098,416 | 1.128872x |
| matmult-int | 4,193,163 | 4,651,344 | 5,647,095 | 1.346739x |
| wikisort | 2,173,042 | 2,325,955 | 2,662,195 | 1.225101x |
| minver | 878,777 | 947,093 | 1,143,155 | 1.300848x |
| fir | 74,311 | 83,810 | 109,737 | 1.476726x |
| bicg | 23,927 | 28,880 | 39,075 | 1.633092x |

These are per-case sensitivity ratios of unchanged RTL, not CPU candidate speedups.
No subset score is generated; the full Embench19 / FP32 eight-case denominators
and the 1.20x/1.10x planning targets are unchanged. No new PPA result is present.
Host/Spike qualification is reused through matching ELF identity; those full
qualifications were not rerun during this study.

## Independent environment probes: contract FAIL

The fault-ready probes use a separate C++ executable linked to the same unchanged
Verilated RTL model. Normal control output is byte-identical to the standard
simulator on both `store_forwarding` and `rv32i_basic`.

- Independent request-ready is allowed only one cycle in four, even when no
  request is outstanding: **both programs watchdog**. Logs show a blocked load
  with `lsu_ready=1 ex0_advance=1`; the CPU consumes it without bus acceptance.
- One RAM store response returns error, preserving the standard request-time
  RAM write behavior: the error is delivered in **both programs**, but both
  finish normally with no cause-7 store-access trap.

`diagnostics/results.json` records `environment_contract_passed=false`, raw
return codes, emitted errors, watchdogs and absent traps. The collector itself
returns **1**. These failures remain failures and are separate from the normal
18/18 denominator. They are not repaired or excluded by these measurements.
The probes are focused examples, not full interface/fault conformance coverage;
request-time RAM write semantics are unchanged, so store atomicity is not tested.

## Evidence layout

- `summary.json`: all 18 profiles/commands/statuses, completeness gate, constant
  instruction-mix checks and sensitivity rows. Partial/failed cases invalidate
  `complete_fixed_study`; no smaller denominator is silently scored.
- `cases/<case>/latency-<n>.json`: raw per-cycle aggregates, disjoint retirement
  partition, nested load/store waits, overlapping events and per-PC counts.
- `run-context.json`: clean source/tree, unchanged model, image IDs, phases,
  actual commands/timestamps/log hashes and successful normal-study exit codes.
- `protocol-at-measurement.md`: exact premeasurement protocol from measured SHA.
- `log-index.json`: runtime paths to exact archived/shared bytes with sizes/hashes.
  Reused old logs are referenced rather than duplicated.
- `input-references.json`: immutable complete prior qualification and fixture paths.
- `regenerable-artifacts.json`: ignored model/ELF binary identities.
- `diagnostics/diagnostic-main.cpp`: exact environment-only C++ source compiled
  against the baseline model; never replaces the standard simulator.
- `diagnostics/harness-context.json`, `build-command.json`: parent/source hashes,
  injected environment semantics, compiler argv, model object/header hashes,
  collector script hash, red exit status and completion timestamp.
- `diagnostics/run-probes.py`, `results.json`, `raw/diagnostics/*`: executable
  reproducer, failure classifications, normal controls and all negative stdout.

The standard simulator source, RTL and compiled model stay unchanged throughout
both studies. The diagnostic main changes only the environment's ready/error
behavior and adds observations; normal-mode byte equivalence is explicitly checked.

Reproduce the normal study after preparing the same qualified ELF outputs:

```bash
python3 -m unittest discover -s scripts -p 'test_fp*.py'
python3 scripts/test_lsu_candidates.py
make profile-lsu-candidates JOBS=4
```

To reproduce the independent red probes, first build the normal simulator and
directed ELFs (`make sim-build compile-tests JOBS=4`) at the recorded source.
Copy the three archived files `diagnostic-main.cpp`, `run-probes.py`, and
`build-command.json` into `build/qualification/lsu-review/diagnostics/`.
Inside the pinned `rv32ooo-fp:p1` container with repository working directory:

```bash
python3 -c "import json,subprocess; subprocess.run(json.load(open('build/qualification/lsu-review/diagnostics/build-command.json'))['command'], check=True)"
python3 build/qualification/lsu-review/diagnostics/run-probes.py
# Recorded baseline exits 1 because environment contracts fail.
```

The eight diagnostic run commands and exact firmware hashes are in results.json.
Rebuilt unstripped firmware/model metadata is not promised byte-identical; record
new hashes instead of silently substituting them for the archived execution.

From this directory: `sha256sum -c SHA256SUMS`. It verifies every local artifact
and every shared immutable input/log reference. Normal study success and interface
failure are independent reported outcomes; neither establishes physical signoff.
