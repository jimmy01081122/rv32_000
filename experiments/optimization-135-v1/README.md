# Directions 1, 3 and 5 — controlled first study

The user selected architecture-map directions 1, 3 and 5 on 2026-10-30.
This stage completes the already-defined first comparisons: isolated A in the
new common physical flow, read-only FP scheduling/arbiter observations, and
FPU path/latency/throughput analysis. Keep the original frozen workloads,
fixed 10 ns memory and independent performance/area targets. There is no A+B
candidate or automatic baseline promotion.

Direction 1 uses the previously verified linked A netlist, shared FPU and
original A functional provenance. `run_A_physical.py` calls the unchanged B
GRT and hold40 stage functions under separate A identity contracts. The exact
accepted Tcl/config/tool inputs remain pinned. Its final guard contract binds
the actual completed A predecessor before `guard_A.py` applies the same single
BUFx2 input guard, original-connectivity proof and full route. Independent
TT/SS/FF processes and strict final review remain necessary.

Directions 3 and 5 first use all retained baseline/A/B profiles, then augment
read-only observation where the existing counters cannot resolve the hypothesis.
Observer off/on and original-model outputs, cycles and per-PC counts must match.
Test fixtures must exercise nonzero contention/blocking and reject wrong signal
interpretation. Overlapping counts are not saved-cycle estimates; a head opcode
is not the functional unit's own latency. No partial workload result replaces
the frozen full-suite score. Candidate implementation choices follow the evidence
and the user's joint architecture review.

Original frozen archives remain unchanged. Completed working checkpoints were
losslessly compacted with hash-checked receipts; raw OpenDB inputs must be restored
before a tool that requires them is rerun. Image/PDK identities and final acceptance
limits do not change.

## First study status

See [the measured review](../../docs/OPTIMIZATION_135_STUDY.md). All 81 retained
profiles and 27 observer off/on pairs pass. Six real instruction controls exercise
nonzero completion contention and preserve the full ordered retirement trace.
The A policy/input preflight passes; the native A run has **not started**.
Workspace disk exhaustion and unavailable Docker socket access block it.

Actual diagnostic output is at `/tmp/rv32-opt135`; the full archive is also saved
as [a portable repository bundle](../../docs/evidence/optimization-135-study-2026-10-30.tar.gz).
The temporary extracted copy is `/tmp/rv32-opt135/archive`. These are source-hash-bound host observations,
not a new clean-commit full architectural qualification or a partial-suite score.
The v1 observer controller accepted B; baseline/A stopped on differing ELF path
labels. The v2 controller validates that path label and requires every other log
byte to match. Failed v1 data is retained, and completed B observations are reused
without changing their source or model bytes.

```bash
python3 experiments/optimization-135-v1/preflight_A.py
python3 experiments/optimization-135-v1/analyze_retained.py --repo "$PWD" --output /tmp/new-retained-study
python3 experiments/optimization-135-v1/run_observer.py --repo "$PWD" --output /tmp/new-observer-study
g++ -std=c++14 -O2 -Isim/tb experiments/optimization-135-v1/test_observer_adapter.cpp -o /tmp/fp-observer-adapter-test
/tmp/fp-observer-adapter-test
python3 experiments/optimization-135-v1/verify_study_archive.py /tmp/rv32-opt135/archive
```

The new harness uses the retained model archive and Verilator runtime objects,
the local v4.038 headers and host g++. Build commands and every input hash are
saved. The adapter reads const signals only; its diagnostics exclude flush
cycles. Issue/first-valid/grant observations include speculative work and are
not retirement latency measurements. Inputs with completions outside the ROI
are excluded from pair histograms; outstanding work is dropped on flush.

Before native A construction, recover storage, commit the source, verify the
fixed image/tool/PDK manifest, and use a fresh native runtime mounted at
`/workspace` and `/orfs-source`. `run_A_physical.py` then uses the unchanged
accepted native construction functions. Independent corner checks and actual
adjacent-period failures remain required after construction. A preflight PASS
does not qualify timing, area or system speed.
