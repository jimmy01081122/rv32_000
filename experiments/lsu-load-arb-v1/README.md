# Bounded LSU load arbitration experiment

Authorized 2026-11-13 (Asia/Taipei). Parent is completed A+B at `49122fb`;
the original AP5B baseline remains unchanged. Only LSU RTL may change.

The first hypothesis gives an already-safe external load one opportunity when
a full-tag, exception-free head store is first marked. Existing SQ marking
restores store priority on following cycles. An offered load remains selected
under backpressure until acceptance or recovery. No combinational request-valid
dependency on ready is introduced. Busy memory can consume the first opportunity
without a bypass; this is deliberately narrower than round-robin arbitration.

Existing unresolved/partial-overlap checks, forwarding, misalignment, registered
response handoff, one external outstanding transaction, successful-store-response
retirement and fault/flush ownership remain in force. No new LQ, cache, C head
lookahead, FPU or divider change is included. Memory service stays at 10,000 ps.

Gates 1–3 completed at clean `669c8ee`; all four pipeline stages exited 0.
At the nominal 100 MHz simulation point, Embench/FP32 are 1.070636×/1.101087×
original baseline, or 0.996920×/1.011798× A+B. Ten cases improve, fourteen
regress, three tie. Physical gate 4 is unmeasured; this candidate has not been
selected for promotion. See the [complete functional review](../../docs/LSU_ARBITRATION_REVIEW.md).

Validation gates:

1. Actual parent and candidate: 140 pin-driven cases each (66 unchanged AB
   safety cases plus 74 arbitration cases), parent negative timing control,
   actual unbounded-priority and missing-hold RTL mutants.
2. Clean normal/assert models; 18 directed, 18 Spike, 48 interface, 58 memory
   and 3,400 finite FMA checks with unchanged numerical requirements.
3. All frozen Embench19 and balanced FP32 eight at 10,000 ps, identical ELF and
   per-PC retired work; compare to both original baseline and A+B. PID is a
   diagnostic case, never a replacement for either full denominator.
4. A retained candidate needs fresh shared-flow physical qualification. The
   [current critical-path inventory](../../docs/CRITICAL_PATHS.md) is the measured
   A+B parent, not the new arbitration RTL. No new timing/area claim is made yet.

Both independent speed goals remain ≥1.20× and area ≤1.10× original baseline.
Do not promote the candidate or change operating/memory policy to hide regressions.
Development failures and checker repairs are retained separately.

Verify the published evidence without extraction:

```sh
python3 experiments/lsu-load-arb-v1/verify_archive.py docs/evidence/2026-11-16/lsu-arbitration-functional
```
