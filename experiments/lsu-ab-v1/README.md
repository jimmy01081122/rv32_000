# A+B LSU composition experiment

Authorized 2026-11-08 after the bottleneck review. This branch combines A's
successful registered-response handoff with B's full-tag, exception-free
ROB-head store marking. Only `rtl/lsu/rv32_ooo_lsu.sv` changes in the CPU.
The frozen baseline and independent A/B references remain unchanged.

Functional gates 1–3 pass at clean `3f079c1`; [results and limits](../../docs/LSU_AB_REVIEW.md). Physical gate 4 remains pending.

Validation gates, in order:

1. One pin-driven 83-case suite against actual baseline, A, B and A+B RTL,
   with negative controls requiring both changes. The 21 additional cases
   exercise simultaneous response consumption/head marking, competing loads,
   backpressure, sequence wrap, INT/FP destinations, store/load faults,
   flush, recovery and full retirement tags. No forced internal state.
2. Clean-source normal/assertion models, 18 directed programs, 18 Spike
   traces, 48 interface cases, 58 memory cases and 3,400 finite FMA vectors.
3. Frozen Embench 19 and FP32 eight, identical ELFs and per-PC retired work,
   measured at 10000 ps CPU and 10000 ps memory. Compare to original baseline
   and both independently measured parents; do not multiply A/B gains.
4. Fresh shared-FPU, TT construction, hold40, uniform ready guard and independent
   TT/SS/FF global-route assessment. The legacy physical input inventory in the
   manifest remains immutable; the current physical policy requires its own
   run contract and raw evidence. No physical timing or area claim before this.

Planning targets remain two separate time-speedup geometric means >= 1.20 and
standard-cell area <= 1.10 of the original frozen baseline. Memory stays at
10000 ps at every CPU frequency. Qualification does not promote this candidate.

Integer DIV/REM operand/latency diagnosis is a separate read-only study.
No integer-divider optimization or additional outstanding memory request is
included in A+B.
