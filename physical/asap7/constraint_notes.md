# Current ASAP7 constraint notes

Updated 2026-10-16. This describes [constraint.sdc](constraint.sdc) as checked in;
it does not establish timing closure or freeze the next experiment's contract.

| Setting | Current value |
| --- | --- |
| Clock / port | `core_clk` / `clk` |
| Period | `5500.0` (5.5 ns with the flow's assumed ps unit) |
| Waveform | `0.0`, `2750.0` |
| Setup / hold uncertainty | `50.0` / `25.0` time units |
| Clock and non-clock input transition | `20.0` time units |
| Input / output delay | `0.20 × period` = `1100.0` time units |
| Output load | `2.0` library capacitance units; verify units when provisioning |
| Path groups | `in2reg`, `reg2out`, `reg2reg`, `in2out` |

These are research constraints, not characterized SRAM, package or SoC timing.
The 20% I/O budget is an existing assumption; it has not been validated against
an external memory design. All non-clock inputs receive the same delay/transition,
and all outputs receive the same delay/load, including the commit-trace interface.
The SDC does not explicitly distinguish debug pins or reset paths.

The current [top-level ports](../../rtl/core/rv32_ooo_core.sv) use
`imem_rsp_rdata`, `dmem_req_wen` and `dmem_req_byte_en`. Use the elaborated port list
for constraint coverage instead of the old proposal's signal names.

## Qualification checklist

- Confirm time/capacitance units from the loaded libraries; do not assume a unit
  conversion solely from numeric values or report filenames.
- Review clock propagation, reset treatment, setup/hold coverage and unconstrained
  endpoints. Timing exceptions require an explicit design rationale.
- Review internal and all interface path groups before calling a period closed.
- State whether parasitics come from placement, global routing or detailed-route
  extraction, and whether reports use TT, SS, FF or a reviewed multi-corner set.
- If period is swept, record the absolute I/O delay at every point. Existing
  scripts scale I/O delays with the clock, so results use changing I/O budgets.
- Preserve both the actual passed clock constraint and any slack-derived frequency
  estimate, clearly labeled as different quantities.

The helper [sta_analyzer.py](scripts/sta_analyzer.py) regenerates constraints for
its period argument and loads FF libraries/global-route estimates. The values in
the checked-in SDC alone therefore do not identify every historical experiment.
