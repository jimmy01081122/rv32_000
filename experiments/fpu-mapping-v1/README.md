# FPU mapping repair experiment

Authorized 2026-10-22 after the [B timing diagnosis](../../docs/LSU_B_TIMING_DIAGNOSIS.md).
This experiment preserves the `rv32_ooo_fp_execute` synthesis boundary with the
pinned ORFS `SYNTH_KEEP_MODULES` option. The CPU RTL, latency, arithmetic,
compiler settings, memory model and frozen v1 results are unchanged.

The native ORFS synthesis passes and ABC arguments are retained. A wrapper saves
the FPU immediately before and after ABC and after final mapped cleanup. Fresh
baseline, A and B builds must demonstrate identical FPU mapping, correct module
connections and functional equivalence. Synthesis timing is diagnostic only;
physical qualification requires a fresh complete implementation and independent
TT/SS/FF checks. B's previous FF hold failure remains a separate admission gate.

Work in progress: results will be recorded after native checks complete. This
flow must not be mixed with v1 physical scores or promoted to a new baseline
without a complete same-flow comparison.
