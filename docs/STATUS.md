# Current project status

Updated 2026-10-21. Initial documentation-cleanup baseline: maintenance commit `1b266ed0b17aaec2dc598e5128fc57ab9edf56bb`;
incoming RTL revision: `0d79df58e65c2e1034e40f7f586a463fd8602ff1`.
The documentation cleanup changes no RTL behavior or executable acceptance thresholds.

FP32 compiler contraction is now approved as `fast` with `-fno-fast-math`;
the daily qualifier defaults to fast and retains explicit off comparisons.
The post-LSU v1 workload identities and fixed-absolute-time memory policy are
frozen in [AP5B v1](../baselines/ap5b-post-lsu-v1/manifest.json). The
[formal baseline](evidence/2026-10-18/post-lsu-baseline/README.md) passes 27/27 at
10 ns (100 MHz), with 22,081.1184 µm² cell area and fixed 10 ns I/D memory time.
TT/SS/FF closure is qualified at global-route research scope. The approved
[isolated LSU A experiment](../experiments/lsu-a-v1/README.md) passes clean-source
functional qualification and complete 27-case measurement at both independently
qualified operating points. Its [physical evidence](evidence/2026-10-20/lsu-a-physical/README.md) records
22,162.24152 µm² (1.003674× baseline), actual 9.8 ns SS setup failure and
9.9/10.0 ns TT/SS/FF passes. The independent [B experiment](LSU_B_REVIEW.md) is now complete: functional/cycle qualification passes, physical timing fails; C remains later.

The [A functional milestone](evidence/2026-10-19/lsu-a-functional/README.md) at
clean `39bc12d` includes 40 positive LSU pin-driven cases and an original-RTL
negative timing control, 18 directed and 18 Spike cases, 48 assertion-enabled
interface cases, 58 fixed-time controls and 3,400 finite FMA checks. All 27 frozen
workloads pass, including 3,629 FP32 outputs and unchanged retired instruction
classes; the 151-input durable job finishes with unchanged hashes. At common
100 MHz and fixed 10 ns memory, Embench GM is 1.045830× and FP32 GM 1.078255×
(DSP 1.051614×, matrix/ML 1.105571×). The same 100 MHz result is now physically qualified. The complete 101.01 MHz
run at clean `70727f5` also passes 27/27 and 3,629 FP32 outputs, with 231 unchanged
inputs, but yields Embench 0.726601× and FP32 0.700275×. Audits confirm fixed
10 ns service first becomes visible after 19.8 ns at that clock. Both points
retain identical per-PC/instruction/kind retired-work counts across all 27
programs; these count maps are not an ordered trace. Area passes the 1.10×
budget; neither operating point reaches both 1.20× goals. Recommend discussing 100 MHz for A alongside the completed B result; no replacement baseline has been selected.

The subsequent [A verification review](LSU_A_VERIFICATION_REVIEW.md) reruns the
clean-source directed/Spike/interface/fixed-time/FMA regression and passes 35 LSU
unit cases on each of baseline and A, plus the original-RTL negative control.
It fixes two reviewer omissions: build/functional executable provenance was not
bound to measurements, and per-PC retired work was only checked offline.
All four real-data negative controls now reject; 30 contract/review controls pass.
Both complete operating points pass the strengthened review with unchanged scores.
The A review changed no CPU RTL or scored simulator/physical inputs. The completed B branch starts at frozen `58a4159`, with only LSU B RTL and explicitly shared tooling. Clean `95ac0dd` passes baseline/B unit 62 each, directed 18/Spike 18/interface 48/fixed-time 58/FMA 3400, all 27 workloads and FP 3629, with matching per-PC work. The common-clock cycle diagnostics are Embench 1.029459× / FP32 1.009599×, DSP 1.013839× / matrix/ML 1.005376×. PID time increases 13.9763%.

B standard-cell area is 21,983.62194 µm² (0.995585×). Native synthesis/backend/ECO complete rc0 with unchanged inputs and zero final route overflow, but independent timing rejects it: SS setup −2282.992ps at 10000 ps, SS setup −82.991ps at 12200 ps and +17.009ps at 12300 ps; FF hold −0.333ps at all tested periods, including 14000 ps. There is no qualified B clock or accepted system-time score. Strict admission rejects the physical proof; a separate complete functional/raw-data review passes. The [B review](LSU_B_REVIEW.md) and [raw archive](evidence/2026-10-21/lsu-b/README.md) retain failures and the mapping/layout limitation. Subsequent [timing diagnosis](LSU_B_TIMING_DIAGNOSIS.md) completes 12 read-only processes: all nine original routed corner results reproduce, and exact connectivity of 534,342 synthesis cells binds the zero-wire probes to the recorded mappings. The unchanged FPU already has a longer B path before placement; FF has two failing LSU tracking endpoints despite positive TT hold margin. Stable mapping/TT hold-flow calibration or a new FP architecture experiment remains a joint choice. This B version is not promoted; no CPU, physical acceptance rule or baseline was changed.

## Evidence available

The [session handoff](SESSION_HANDOFF.md) records the bring-up environment and
local evidence paths. That run passed:

- lint, hierarchy checks and generic Yosys synthesis;
- 18 directed workloads and their Spike trace comparisons;
- 11 negative comparator self-tests plus the positive baseline;
- 24 directed memory-delay configurations;
- CoreMark validation smoke and one Embench workload (`crc32`);
- eight workflow-guard tests and CI static checks.

This was development qualification, not a fresh full architectural/physical
signoff. The session did not run the full 14-workload Embench subset, full ACT4,
or AP5B physical implementation. Earlier result files have their own source and
configuration, and must not be merged into this run's pass counts.

The [LSU selection study](LSU_OPTIMIZATION_REVIEW.md), clean source `3513c0c`,
now passes 18/18 fixed case/delay combinations (four Embench representatives and
FIR/BiCG at delays 1/2/4), nominal observer invariance for all six cases, and 25
Python controls. That study changed neither RTL nor the simulator binary and
emits no subset score or CPU improvement claim. Its separate environment probes
found two defects: a backpressured load could be lost and a store-error response
could retire without cause 7. The subsequent [interface fix](LSU_INTERFACE_FIX.md)
at `ec0baa3` passes 48/48 assertion-enabled cases, directed and Spike comparisons
18/18 each, finite FMA checks, FP32 fast 8/8 and Embench 19/19. Original probes
also turn green; historical failed evidence remains intact. Nominal workload
ELFs/results/cycles match the prior qualification. This is a functional reference
point; its later global-route physical qualification is archived above.

The [post-LSU baseline preparation](evidence/2026-10-18/post-lsu-baseline-preparation/README.md)
at clean `5822071` now passes all 27 workloads with absolute-time memory,
unchanged ROI cycles and 3,629 independently checked FP32 values. The new model
passes 58 controls and the 18 directed programs. The user selected fixed memory
time and an ASAP7 RVT global-route research baseline, with TT construction and
independent SS/FF checks. Pinned physical tools and completed synthesis stages are
available. Earlier 5,500 ps attempts stopped before global routing without a
recorded final exit status. A durable worker now records real exits and verifies
input hashes; its five controls pass. The first cached 14,000 ps backend attempt
failed on an unsupported placement seed flag; the runner now explicitly uses
the pinned tool's placement default. Both periods are exploration constraints,
not achieved clocks. Cached synthesis retains its original 5,500 ps mapping
constraint and is checked separately from backend timing.
Review also found that the initial config loaded all three construction views.
That exploratory backend was stopped before completion. The runner now overrides
`CORNER=TC CORNERS=typical` to honor TT-only construction; SS/FF remain independent
post-route checks. Earlier three-view attempts cannot qualify the baseline.
The bounded [ASAP7 library validation](evidence/2026-10-18/asap7-library-validation/README.md)
checks 144 adder transitions, 30 independent min/max timing paths and three
negative controls; known output-port warnings remain documented. This is tool
qualification, not full-core timing closure.
The [saved-route report controls](evidence/2026-10-18/physical-report-validation/README.md)
pass 49/49 on a four-cell sequential fixture: three independent corners, explicit
ps units, all four path groups, numerical/report agreement, real setup/hold and
constraint/electrical failures, and rejection of unrouted or unaudited inputs.
This fixture qualifies reporting only; whole-core closure is established by the
separate formal baseline evidence above.
The complete baseline/worker/timing-review control target now passes 20 tests,
including frozen FP32 fixture hashes, dimensions and tolerances. The
[incomplete physical probes](evidence/2026-10-18/physical-development-attempts/README.md)
retain failed/unknown exits separately from positive qualification evidence.
The [complete ORFS-step API fixture](evidence/2026-10-18/global-route-api-validation/README.md)
now finishes global routing with ordinary repair and passes all three independent
corner reviews, providing a real positive timing control. The full-core TT run
completed CTS and ordinary post-route repair, then aborted on an unsupported
optional `reroute` optimization move. Its Make exit 2 remains a failure. A fresh
retry reuses the verified CTS checkpoint with that optional pass disabled.
That retry now [completes global routing](evidence/2026-10-18/global-route-initial-review/README.md)
with unchanged inputs and exit 0. At 14 ns, independent TT/SS/FF setup and hold
slacks are positive and constraint coverage passes, but SS has 541 slew
violations and FF has 30. The review correctly rejects closure. A 30% TT slew-margin probe
left 171 SS violations. [Paired pin diagnosis](evidence/2026-10-18/global-route-slew-diagnosis/README.md)
then motivated a clean TT 45% slew-margin / 50 ps hold-target repair from the
original route. The final whole-design route has zero overflow; TT/SS/FF all
pass at 10 ns, while SS setup fails at 9.9 ns. Independent limits are unchanged.
The final area includes all clock/repair cells; see the formal baseline above.
The separate [assertion-enabled fixed-time controls](evidence/2026-10-18/fixed-time-assertions/README.md)
also pass 58/58 plus the scheduler unit test; all 12 fault traces match the
normal-build preparation evidence. The scored simulator remains unchanged.
The [v1 manifest](../baselines/ap5b-post-lsu-v1/manifest.json) is frozen after
formal 27/27 measurement at clean `9769123`; source state and scored simulator
remain unchanged. A has completed isolated global-route research qualification; the frozen baseline contains no A/B/C.

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

## Qualification gaps

1. **AP5B unit validation:** the targeted C++ interface flow now runs 48 cases with
   `--assert` in `build/sim-assert`, including backpressure and precise faults.
   The dedicated timed SV testbench still needs a separately pinned capable
   simulator; the normal simulation build omits `--assert`. Targeted passes do not
   establish complete AP5B/ISA coverage.
2. **Architectural tests:** provision a real Sail 0.13.1 ACT4 environment and run
   fresh generation. The existing configuration covers I/M/Zicsr/Zifencei/Zmmul;
   its historical 58-test set has no F coverage.
3. **Reference comparison:** `run_spike_diff.py` leaves `trap_cause` and
   `trap_tval` unset and normalizes dynamic counter reads. Its passes are not
   evidence of complete trap, CSR or FP-flag equivalence.
4. **Functional coverage:** map ISA, FP rounding/flags/exceptional operands,
   memory error handling, redirects, stale completions and ownership invariants
   to tests/assertions. Complete reviewable coverage and focused formal plans.
5. **Performance:** qualify the [candidate workload sets](WORKLOADS.md), memory
   contract, compiler settings, reference outputs and counter instrumentation.
   [Initial probes](WORKLOAD_QUALIFICATION_2026-10-16.md) found that all five omitted
   Embench workloads pass native self-checks but fail target linking with the current
   single-library, `ilp32d` toolchain. The separate [FP toolchain and progress
   review](PROGRESS_REVIEW.md) now records 19/19 new-toolchain build/Spike passes.
   The FP-store cross-domain bypass error at PC `0x80001220` was corrected;
   `minver` now passes DUT self-check. The full 19-program DUT functional probe
   also passes 19/19, with [archived evidence](evidence/2026-10-17/README.md).
   The user approved all 19 workloads as the general embedded suite. A
   [clean-commit rerun](evidence/2026-10-17/embench-approved-rerun/README.md)
   at `7ba020297da6e6cdc4e5857fdde6ff57fec627d6` passes 19/19 native,
   Spike and DUT self-checks plus ELF ISA/ABI checks. All target ELF hashes and
   diagnostic metrics match the earlier run. That rerun predates the frozen
   post-LSU input contract above. Initial broad PolyBench MINI/SMALL probes
   established native runs and target object compilation. Subsequent balanced-FP32
   qualification covers bare-metal GEMM, BiCG and Cholesky; it does not qualify
   the entire PolyBench suite.
   The user approved balanced control/DSP and matrix/ML coverage with four
   kernels per group and equal group weights. The [FP32 workload record](FP32_BALANCED_PROPOSAL.md)
   notes 18/18 native/RV32 object builds for
   additional sources; pinned CMSIS-DSP, KissFFT and PolyBench source identities
   pass `make check-fp-sources`. The [balanced FP32 qualification](evidence/2026-10-17/fp32-balanced-qualification/README.md)
   now passes 8/8 native, Spike and DUT cases from clean commit
   `df97854c719014df862d6d6df450d02fe0cee756`. Each native/DUT run emits 3,629
   values independently checked against host-double references. Streaming states,
   Cholesky reconstruction and pinned upstream SVM labels pass; six checker
   positive/negative controls pass. The later post-LSU manifest freezes sizes,
   tolerances and ELF bytes, includes timer overhead without subtraction, and
   records retired-SP stack headroom in all 27 preparation runs. Absolute memory
   time is now calibrated to the qualified 10,000 ps period in the formal run.
   A [matched contraction experiment](FMA_CONTRACTION_REVIEW.md) at clean commit
   `581ee86f1bd55bc6eff7cc123c660ab94446eb6f` now passes all eight cases in both
   off and fast modes, with diagnostic equal-group cycle ratio 1.113x. Its finite
   cancellation probe exposed and fixed premature sticky-bit compression in FMA;
   full-precision normalization and subnormal packing were corrected. All 3,400
   finite FMA result/flag cases pass the integer oracle, Spike and DUT. Post-fix
   directed and commit-diff checks pass 18/18 each; Embench passes 19/19 native,
   Spike and DUT. This is finite-input coverage, not complete NaN/Inf, trap or
   RV32F conformance. The final global-route baseline includes these datapath fixes;
   compiler gains do not establish the architecture or area planning targets.
   The [instruction/wait diagnosis](FMA_BOTTLENECK_REVIEW.md) at `5065e7f` adopts
   the approved fast default and observes unchanged RTL. FIR/BiCG instruction
   savings come entirely from FMUL+FADD contraction. Exposed load-response and
   store-ack waits account for the limited cycle gains. All 16 paired DUT stdout
   files/ELFs match the previous qualification; four observer on/off/old-model
   replays, 8/8 implicit-fast cases, 18 Python controls and 18/18 directed/diff
   checks pass. No CPU structure optimization or new physical result is claimed.
6. **Physical results:** the portable post-LSU runner now uses pinned
   ORFS/ASAP7, explicit inputs and durable job records. TT-only construction is
   active; independent TT/SS/FF reporting and failure controls are qualified.
   Full-core global-route completion, routing review, corner setup/hold/electrical
   closure and the formal 27-workload rerun are now archived and pass. Historical host-specific
   scripts and FF-only STA are outside this baseline. Detailed routing is a later
   milestone.
7. **Power:** establish and record workload switching activity before treating
   power/energy estimates as comparable workload measurements.

## Existing automation versus proposed milestones

`make signoff` is the existing regression/archive pipeline. It requires a clean
tree, fresh ACT4 generation and legacy benchmark/synthesis criteria. The following
limitations remain visible rather than being silently changed during doc cleanup:

- The differential acceptance script accepts totals of at least 14, although the
  current directed source set has 18; review expected-set completeness.
- It requires CoreMark/MHz ≥ 2.50, while AP5A reports 2.4748.
- Its 26-iteration CoreMark reporting run declares a 1 MHz clock. That convention
  must not be represented as a ≥10-second measurement at an independently claimed
  ASIC frequency. Review the complete official reporting rules before publishing.
- Legacy Embench acceptance still uses the 14-workload subset. The separate
  post-LSU measurement runner covers all 19 plus the balanced FP32 eight; the
  legacy `signoff` target has not been converted to the dual-family experiment gate.
- The CI `signoff-gate` summarizes configured jobs; neither it nor generic
  synthesis establishes physical closure or full RV32IMF conformance.
- The revised CI workflow has been statically checked locally but not executed
  on GitHub in this session. GitHub-hosted runners are optional remote automation,
  not an assumed replacement for the available local host.

The general embedded and FP32 goals have equal priority. The user approved
planning targets of at least 1.20x speedup for each category and at most 1.10x
baseline standard-cell area on 2026-10-17. Workload identities and the fixed-time
policy, 10 ns physical clock, 22,081.1184 µm² area and formal 27/27 measurement
are frozen in AP5B v1.
A has qualified common-clock CPU gains of 1.045830× / 1.078255×; project performance targets remain unmet.
Document cleanup does not waive old failures.
