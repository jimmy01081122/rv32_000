# Current project status

Updated 2026-10-17. Documentation baseline: maintenance commit `1b266ed0b17aaec2dc598e5128fc57ab9edf56bb`;
incoming RTL revision: `0d79df58e65c2e1034e40f7f586a463fd8602ff1`.
The documentation cleanup changes no RTL behavior or executable acceptance thresholds.

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
   review](PROGRESS_REVIEW.md) now records 19/19 new-toolchain build/Spike passes;
   `minver` still fails the DUT self-check; its first parsed divergence is incorrect
   FP-store data at PC `0x80001220`. PolyBench MINI/SMALL native runs and
   target object compilation succeeded; bare-metal execution and numerical checking
   remain open.
   The user selected balanced control/DSP and matrix/ML coverage. The [4+4 FP32
   proposal](FP32_BALANCED_PROPOSAL.md) records 18/18 native/RV32 object builds for
   additional sources; no new-kernel execution or numerical pass is claimed.
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

The general embedded and FP32 goals have equal priority. Their suggested 20%
improvement targets and 10% area allowance remain proposals until baseline and
measurement review. Document cleanup does not waive old failures or activate
new performance gates.
