# A+B LSU composition experiment

Authorized 2026-11-08 after the bottleneck review. This branch combines A's
successful registered-response handoff with B's full-tag, exception-free
ROB-head store marking. Only `rtl/lsu/rv32_ooo_lsu.sv` changes in the CPU.
The frozen baseline and independent A/B references remain unchanged.

All four gates pass. Functional source is clean `3f079c1`, native physical source
`f66e12b`, and the new fastest-point measurement uses `f1d58d3`.
[Results and limits](../../docs/LSU_AB_REVIEW.md): 100 MHz Embench/FP32
1.073943×/1.088248×, 21,663.036900 µm², actual 9.4 ns qualification and
adjacent 9.3 ns SS failure. Both full 27-case operating points pass numerical
and per-PC checks. Performance goals remain unmet; no baseline promotion.

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

PID read-only waveform diagnosis now identifies a store/load arbitration interaction:
510 steady loop intervals expand from 14 to 16 cycles, while all 2,048 retired
heavy arithmetic operations per variant retain one-cycle unit latency.
The next arbitration, C or divider optimization remains a joint decision.

Recheck published evidence with:

```bash
python3 experiments/lsu-ab-v1/verify_completion_archive.py docs/evidence/2026-11-13/lsu-ab-complete
```
