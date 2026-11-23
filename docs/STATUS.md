# Current project status

Updated 2026-11-23 (Asia/Taipei). Current branch: `codex/lsu-rob-room`.
The original AP5B baseline remains frozen; the candidate has not been promoted.

## Active ROB-space arbitration experiment

The user selected the recommended [ROB-space guard](../experiments/lsu-rob-room-v1/README.md)
on November 16. The new candidate allows first-head load bypass only at registered
ROB occupancy ≤14/16; offered loads remain held regardless of later pressure.
ROB exports one Boolean through core wiring; no extra state or memory transaction
is added. Parent and candidate each pass 344 pin cases, with six actual RTL
negative controls. Clean full-core qualification and all27 pass at `3c87e71`:
18 directed, 18 Spike, 48 interface, 58 memory, 3,400 finite FMA, 3,629 workload
numerical values and unchanged per-PC retired work. All five pipeline stages
completed; the complete comparison independently revalidates after environment resume.

At nominal 100 MHz, Embench/FP32 are **1.076286× / 1.109010×** original baseline,
or **1.002181× / 1.019078×** A+B. Against A+B, 13 cases improve, 11 regress and
three tie. PID retains 7,238 cycles; FFT improves to 33,029; statemate falls to
2,628,051 but remains 0.526% slower than A+B. UD/GEMM/QRduino regress against
arbitration v1 while remaining faster than A+B. The [full result](LSU_ROB_ROOM_REVIEW.md)
preserves all cases. The common global-route flow qualifies 9.8 ns and 10 ns at TT/SS/FF. Standard-cell area is 21,498.75 µm² (0.973626× original). The full 27-workload replay favors 100 MHz at fixed 10 ns memory. Both 1.20× performance targets remain open. [Physical results and critical paths](LSU_ROB_ROOM_PHYSICAL.md).

## Previous arbitration v1 experiment

The user authorized [LSU arbitration](../experiments/lsu-load-arb-v1/README.md) on
2026-11-13. The first candidate allows one safe external load at initial head-store
marking, holds offered loads through backpressure, then restores store priority.
Parent/candidate each pass 140 pin-driven cases and three actual RTL negative
controls pass. Clean full-core qualification and all27 measurement now pass:
18 directed, 18 Spike, 48 interface, 58 memory, 3,400 finite FMA and 3,629
workload numerical outputs. All source stages retain clean `669c8ee`.

Nominal 100 MHz simulation ratios are Embench **1.070636×**, FP32 **1.101087×**
original baseline. Relative to A+B this is **0.996920× / 1.011798×**: ten cases
improve, fourteen regress, three tie. PID time falls 12.33%, but FFT increases
3.55% and statemate 7.33%. The [complete result](LSU_ARBITRATION_REVIEW.md)
retains all cases and exact wait-position deltas.

The [read-only regression diagnosis](LSU_ARBITRATION_DIAGNOSIS.md) now passes all
six observer on/off pairs, 5,504,081 raw cycles and identical ordered retired
instruction streams. Every bypassed head store changes from one to three cycles
mark-to-retirement; the extra FFT/statemate external reads are all accounted for
by increased cancelled reads. Most bypasses in those two cases occur at ROB 15/16.
The ROB-space experiment has now been selected and is tracked above; observational
guard coverage does not predict its final performance.

New timing/area qualification is unmeasured. For arbitration v1, only the A+B parent had physical results. The later ROB-space variant now has [its own critical paths](CRITICAL_PATHS.md). The candidate is
not promoted and the original baseline remains frozen.

## Completed A+B experiment

The user authorized the recommended independent [A+B experiment](../experiments/lsu-ab-v1/README.md)
on November 8. This branch implements response handoff plus head-store marking;
[functional qualification and all 27 common-clock workloads pass](LSU_AB_REVIEW.md).
At 100 MHz / 10 ns memory, Embench is 1.073943× and FP32 is 1.088248×;
3,629 numerical outputs and per-PC retired work match the baseline. A+B beats
B in all 27 cases, but five regress against A, including PID time +14.00%.
Independent AB physical qualification and both full operating points now pass.
Area is 21,663.036900 µm² (0.981066× original, 1.005456× same-flow baseline).
Actual 9,400 ps trials pass TT/SS/FF; adjacent 9,300 ps fails SS setup at −91.798569 ps.
At 9,400 ps, SS setup is +8.201440 ps and minimum FF hold is +17.579993 ps.
The full 9,400 ps replay yields 0.775970× / 0.740353× with fixed memory
sampled at 18.8 ns. Both sets remain below 1.20×; 100 MHz is the better tested point.

Read-only PID waveforms reproduce unchanged program output, memory and profiles.
Across 512 retired loop iterations, 510 steady intervals grow from 14 to 16 cycles:
earlier store eligibility wins the single data port over an otherwise eligible
next-iteration load. This adds 1,020 cycles, offset by six boundary cycles;
2,048 retired arithmetic operations per variant retain one-cycle heavy latency.
Selected raw signals for every ROI cycle and independent reanalysis are archived.

The separate read-only
integer DIV/REM diagnosis passes six on/off pairs and 48 instruction controls:
ordinary accepted-request-to-result latency is 33 cycles, without completion
arbitration waits. Early-result operands concentrate in ud, cubic and nettle-aes.
Neither a new baseline nor a divider RTL optimization has been selected.

The complete result, provenance, limitations and proposed next experiments are in
[the A+B review](LSU_AB_REVIEW.md); see the [current architecture map](ARCHITECTURE_MAP.md).
Bounded load/store arbitration has now been selected and is tracked above. C's
registered-load head lookahead and integer-divider RTL remain unselected.

## Comparison contract and verification

- General embedded: all Embench 19 programs, independently scored GM ≥1.20×.
- FP32: eight programs, four DSP/control and four matrix/ML, equal subgroup
  weights, independently scored GM ≥1.20×; `-ffp-contract=fast -fno-fast-math`.
- Cell area: ≤1.10× original baseline. Report the identical-flow baseline
  comparison separately because shared FPU mapping and hold repair changed the flow.
- Frozen baseline: 10,000 ps, 22,081.1184 µm², unchanged ELF bytes and fixed
  10,000 ps I response / I initiation interval / D response at every CPU clock.
- A+B functional qualification: 332 pin-driven passes across baseline/A/B/AB,
  three negative controls, 18 directed, 18 Spike, 48 asserted interface,
  58 memory controls and 3,400 finite FMA cases. Both full 27-case operating
  points independently check 3,629 numerical values and per-PC retired work.
- Shared FPU: reused complete two-state implementation equivalence after reset,
  with freshly checked module body, ABI, graph and lowering identities. This is
  separate from ISA/IEEE-754 conformance.
- Physical: ASAP7 TT construction, shared FPU, hold40, uniform ready guard,
  independent TT/SS/FF and actual adjacent-period failure, at global-route scope.

The restored FP, simulation and synthesis images match their original image IDs
and pass smoke checks. Eight historical cache files and the full checkout have
been restored; the disposable native container was removed after verified host
publication. The completion archive retains successful and failed environment
receipts separately. These operational failures are not counted as CPU results.

## Prior milestones

| Evidence | Scope and relationship to the current result |
| --- | --- |
| [Frozen post-LSU baseline](evidence/2026-10-18/post-lsu-baseline/README.md) | Original functional, physical and scoring reference; no A/B/C |
| [A common-flow completion](evidence/2026-11-05/optimization-135-A/README.md) | 1.045830× / 1.078255× at 100 MHz, 21,602.442420 µm², shortest tested qualified 9.4 ns |
| [B complete validation](LSU_B_COMPLETE_VALIDATION.md) | 1.029459× / 1.009599× at 100 MHz, 21,309.821820 µm², shortest tested qualified 9.6 ns |
| [Directions 1/3/5 study](OPTIMIZATION_135_STUDY.md) | Read-only FP scheduling/timing observations and isolated A common-flow completion |
| [November 6 bottleneck analysis](BOTTLENECK_ANALYSIS.md) | Historical B-based proposal; its A+B and read-only divider work were subsequently authorized and completed |
| [A+B functional and divider archive](evidence/2026-11-09/lsu-ab-functional/README.md) | Earlier functional milestone; not retroactively relabeled as physical completion |
| [A+B completion archive](evidence/2026-11-13/lsu-ab-complete/README.md) | Native checkpoints, independent corner/workload reviews, PID raw ROI signals and environment restoration |
| [Initial session handoff](SESSION_HANDOFF.md) | Historical environment bring-up and development checks, not the current qualification state |

Older A physical results used a different flow; compare candidates using the
common-flow records above. Failed experiments and historical archive contents
remain preserved. Both performance goals remain unmet.

## Current implementation drift

| Topic | Current finding | Follow-up |
| --- | --- | --- |
| LQ | Parameter/type declarations exist; no allocated LQ array | Review actual load tracking before queue/outstanding-request changes |
| Store queue | 16 local `sq_slot_t` entries; package proposal differs | Document and test allocation, forwarding, retirement and flush identities |
| PRF ports | Integer 4R/3W, FP 4R/2W; some constants still describe G0 | Reconcile configuration semantics in a separately reviewed code change |
| Frontend | Dynamic BTB/BHT, four tracked fetches, no RAS storage | Measure predictor/recovery behavior before optimization |
| Recovery | Branch redirect originates at retirement; ROB clears speculative entries | Validate current recovery instead of assuming the G0 reverse-walk proposal |
| ROB/trace | ROB stores result data; store-only memory payload; per-entry FP flags | Audit trace fidelity and verification boundaries |
| ISA/CSR profile | FENCE.I exists; implemented CSR list differs from G0 | Reconcile advertised extensions, machine subset, access legality and FP state |

## Open qualification work

1. **Architectural coverage:** provision fresh Sail 0.13.1 ACT4 generation. The
   existing configuration covers I/M/Zicsr/Zifencei/Zmmul; the historical 58-test
   set has no F coverage. Targeted regression passes do not establish full ISA
   or machine-mode conformance.
2. **Reference comparison:** the Spike comparison leaves `trap_cause` and
   `trap_tval` unset and normalizes dynamic counter reads. Full trap/CSR/FP-flag
   equivalence is not established by its current passes.
3. **Coverage plan:** complete reviewable ISA, rounding/flags/exceptional-FP,
   redirects, stale completions and ownership coverage, with focused formal
   obligations. The finite FMA suite does not cover all NaN/Inf behavior.
4. **AP5B verification infrastructure:** the C++ interface suite runs with
   assertions; the normal benchmark model does not. The timed SV testbench
   still needs a separately pinned capable simulator.
5. **Physical and power:** detailed routing and workload-switching-based
   power/energy comparisons remain separate milestones. Current results are
   global-route research estimates, with no tape-out claim.

## Legacy automation boundaries

`make signoff` remains a legacy regression/archive target; it is not the
completed dual-family experiment review:

- It requires fresh ACT4 generation and legacy benchmark/synthesis thresholds.
- Its differential acceptance allows at least 14 cases although 18 directed
  sources exist; its Embench path still uses a 14-workload subset.
- Its CoreMark/MHz ≥2.50 threshold is separate from the agreed planning goals.
  The fixed 26-iteration, declared-1-MHz reporting convention does not establish
  a ≥10-second run at an independently claimed ASIC frequency.
- Generic synthesis or a CI job summary does not establish physical closure.
  GitHub-hosted CI is optional remote automation; its current configuration was
  checked locally, not freshly executed as part of this completion.

These limitations remain explicit; no thresholds were relaxed to qualify A+B.
