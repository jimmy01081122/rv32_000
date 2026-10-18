# Current project status

Updated 2026-10-18. Initial documentation-cleanup baseline: maintenance commit `1b266ed0b17aaec2dc598e5128fc57ab9edf56bb`;
incoming RTL revision: `0d79df58e65c2e1034e40f7f586a463fd8602ff1`.
The documentation cleanup changes no RTL behavior or executable acceptance thresholds.

FP32 compiler contraction is now approved as `fast` with `-fno-fast-math`;
the daily qualifier defaults to fast and retains explicit off comparisons.
Formal data/timing/memory and physical contracts remain open.

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
Python controls. RTL and simulator binary are unchanged. It emits no subset
score or CPU improvement claim. Separate environment probes reproduce two open
failures on both `store_forwarding` and `rv32i_basic`: independent request-ready
throttling causes a watchdog, while one store-error response produces no cause-7
trap. Normal diagnostic controls match the baseline byte-for-byte. These negative
cases remain failed and must be addressed before candidate acceptance/new baseline;
the normal 18/18 count does not establish interface conformance.

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

1. **AP5B unit validation:** the dedicated SV testbench uses timing constructs
   outside the pinned Verilator 4.038 C++ flow. Select a separately pinned capable
   simulator or a C++ harness. The normal build also omits `--assert`.
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
   diagnostic metrics match the earlier run. The measurement contract remains open.
   PolyBench MINI/SMALL native runs and
   target object compilation succeeded; bare-metal execution and numerical checking
   remain open.
   The user approved balanced control/DSP and matrix/ML coverage with four
   kernels per group and equal group weights. The [FP32 workload record](FP32_BALANCED_PROPOSAL.md)
   notes 18/18 native/RV32 object builds for
   additional sources; pinned CMSIS-DSP, KissFFT and PolyBench source identities
   pass `make check-fp-sources`. The [balanced FP32 qualification](evidence/2026-10-17/fp32-balanced-qualification/README.md)
   now passes 8/8 native, Spike and DUT cases from clean commit
   `df97854c719014df862d6d6df450d02fe0cee756`. Each native/DUT run emits 3,629
   values independently checked against host-double references. Streaming states,
   Cholesky reconstruction and pinned upstream SVM labels pass; six checker
   positive/negative controls pass. Formal sizes and tolerances,
   timer overhead, stack high-water and memory/physical contracts remain open.
   A [matched contraction experiment](FMA_CONTRACTION_REVIEW.md) at clean commit
   `581ee86f1bd55bc6eff7cc123c660ab94446eb6f` now passes all eight cases in both
   off and fast modes, with diagnostic equal-group cycle ratio 1.113x. Its finite
   cancellation probe exposed and fixed premature sticky-bit compression in FMA;
   full-precision normalization and subnormal packing were corrected. All 3,400
   finite FMA result/flag cases pass the integer oracle, Spike and DUT. Post-fix
   directed and commit-diff checks pass 18/18 each; Embench passes 19/19 native,
   Spike and DUT. This is finite-input coverage, not complete NaN/Inf, trap or
   RV32F conformance. Physical results must be refreshed for the changed datapath;
   compiler gains do not establish the architecture or area planning targets.
   The [instruction/wait diagnosis](FMA_BOTTLENECK_REVIEW.md) at `5065e7f` adopts
   the approved fast default and observes unchanged RTL. FIR/BiCG instruction
   savings come entirely from FMUL+FADD contraction. Exposed load-response and
   store-ack waits account for the limited cycle gains. All 16 paired DUT stdout
   files/ELFs match the previous qualification; four observer on/off/old-model
   replays, 8/8 implicit-fast cases, 18 Python controls and 18/18 directed/diff
   checks pass. No CPU structure optimization or new physical result is claimed.
6. **Physical results:** port hardcoded host paths, provision pinned ORFS/ASAP7,
   audit measurement units, synthesis boundary, constraints, corners and parasitic
   stage, then reproduce AP5B results. Current config skips detailed routing;
   the STA helper uses FF libraries and global-route parasitic estimates.
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
- Embench acceptance still uses the 14-workload subset; no PolyBench runner or
  independent FP32 performance gate has been added.
- The CI `signoff-gate` summarizes configured jobs; neither it nor generic
  synthesis establishes physical closure or full RV32IMF conformance.
- The revised CI workflow has been statically checked locally but not executed
  on GitHub in this session. GitHub-hosted runners are optional remote automation,
  not an assumed replacement for the available local host.

The general embedded and FP32 goals have equal priority. The user approved
planning targets of at least 1.20x speedup for each category and at most 1.10x
baseline standard-cell area on 2026-10-17. Baseline and measurement contracts
remain open; no measured improvement or new performance gate is claimed.
Document cleanup does not waive old failures.
