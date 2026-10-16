# ASAP7 physical-design research flow

Updated 2026-10-16. This directory contains the existing OpenROAD Flow Scripts
(ORFS) / ASAP7 7.5T research setup, scripts and historical results for
`rv32_ooo_core`. ASAP7 is a predictive PDK. The project does not target tape-out.

## Current status

- Tool/image/PDK references are in [toolchain.lock](toolchain.lock).
- [config.mk](config.mk) requests 50% core utilization, placement density 0.55
  and `SKIP_DETAILED_ROUTE=1`. Several timing/placement repair options are disabled.
- [constraint.sdc](constraint.sdc) currently specifies `5500.0` time units,
  interpreted by this ASAP7 setup as 5500 ps / 5.5 ns. This is a checked-in
  exploration constraint, not an achieved frequency or a newly agreed target.
- [run_physical_build.py](scripts/run_physical_build.py) and related scripts still
  contain host-specific `/home/a/ooo` and ORFS paths. They need porting before a
  reproducible AP5B run on the current host.
- [sta_analyzer.py](scripts/sta_analyzer.py) loads RVT **FF** libraries and uses
  `estimate_parasitics -global_routing`. Its output is a fast-corner/global-route
  estimate, not completed detailed-route extraction or multi-corner closure.
- The STA helper calls `report_power` without loading workload VCD/SAIF activity.
  Historical power values must retain that measurement limitation.
- No AP5B physical implementation has been reproduced in this session.

The earlier 1 GHz / CoreMark-per-MHz 0.8 target is retired. The former README's
`run_asap7_flow.sh`, `parse_asap7_sta.py` and `run_fmax_sweep.py` commands did not
match the checked-in scripts and are no longer presented as runnable setup.

## Files and evidence

| Path | Role |
| --- | --- |
| [config.mk](config.mk) | Existing ORFS configuration |
| [constraint.sdc](constraint.sdc) / [constraint_notes.md](constraint_notes.md) | Current clock/I/O settings and assumptions |
| [pin_order.cfg](pin_order.cfg) | Port placement configuration |
| [scripts](scripts) | Build/STA helpers and historical sensitivity experiments |
| [baseline_manifest.json](baseline_manifest.json) | Historical AP0 source/configuration record |
| [results](results) | Historical implementation artifacts |
| [Report index](../../reports/README.md) | Provenance and limits of phase summaries |

The `rv32ooo-syn:g1` image runs generic Yosys synthesis. It does not contain the
pinned ORFS/ASAP7 environment; generic cells are not mapped standard-cell area.

## Required work before the next physical baseline

1. Provision the pinned image/platform on the available host and replace legacy
   absolute paths with explicit project/output paths.
2. Record source SHA, lowered netlist, tool/image/PDK identifiers, SDC and all
   resolved flow settings. Audit library time/capacitance units.
3. Review the measured boundary: core storage, clock/reset, memory interfaces and
   commit/debug ports. The C++ RAM/loader is outside RTL; do not assume all debug
   logic has been excluded from the physical core without checking the netlist.
4. Freeze corner coverage, setup/hold uncertainty, input/output budgets, output
   loads and implementation/parasitic stage. Separate internal and interface paths.
5. Establish setup/hold closure for every valid path group under the chosen
   contract, and record unconstrained paths and reviewed exceptions. A frequency
   inferred from one slack number is not a rerun at that frequency.
6. Record routing/DRC/connectivity status and power activity coverage explicitly.
   Run baseline and candidate under the same conditions; retain raw logs.

Absolute frequency and energy targets remain open under [PLAN.md](../../PLAN.md).
When frequency changes, audit whether I/O budgets and the memory model also change;
an apparent speedup must not hide a different external timing assumption.
