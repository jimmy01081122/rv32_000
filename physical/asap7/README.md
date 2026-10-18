# ASAP7 physical-design research flow

Updated 2026-10-18. This directory contains the existing OpenROAD Flow Scripts
(ORFS) / ASAP7 7.5T research setup, scripts and historical results for
`rv32_ooo_core`. ASAP7 is a predictive PDK. The project does not target tape-out.

## Current status

The active post-LSU baseline uses [baseline/config.mk](baseline/config.mk),
[`scripts/run_baseline_physical.py`](../../scripts/run_baseline_physical.py) and
independent TT/SS/FF analysis via
[`scripts/analyze_baseline_physical.py`](../../scripts/analyze_baseline_physical.py).
The [manifest](../../baselines/ap5b-post-lsu-v1/manifest.json) remains preparing;
no full-core global-route closure or area baseline has been qualified.
Inside the pinned `rv32ooo-syn:g1` image, create the Verilog input with
`python3 scripts/lower_baseline_rtl.py --out build/baseline-setup/rtl_lowered.v`.
The output must not exist; `--compare` can verify a separate fresh reproduction.
The [source-to-Verilog recheck](../../docs/evidence/2026-10-18/rtl-lowering-validation/README.md)
reproduces the current physical input byte for byte with `SYNTHESIS` defined.
After independent analysis, `scripts/check_physical_closure.py --analysis build/.../LABEL`
reviews only actually tested clock periods, report hashes, four path groups and
the serialized fixed I/O/uncertainty/load contract. It rejects unresolved
constraint or electrical reports and negative setup/hold slack. Its result is a
timing review; global-routing/connectivity review and formal 27-workload
measurement are still required before freezing the manifest.
Independent collection verifies the archived 204-file tool/platform checksum
manifest before and after STA, in addition to the bounded adder-warning audit.

Use a fresh `--label` for each attempt. `--detached --container ID` starts a
durable worker that records real process status and input identities even when
the client session ends. Successful execution alone never sets `passed=true`.
`--synthesis-from build/...` imports a completed mapped netlist only after
matching RTL, lowering, config, image and adder-mapping identities and checking
the original synthesis completion log. Its original mapping period stays in the
record; a different backend period does not constitute remapping at that period.
Earlier incomplete 5,500 ps attempts remain unqualified. A 14,000 ps backend
exploration exposed an unsupported `global_placement -random_seed` flag; the
runner explicitly overrides `GPL_RANDOM_SEED=` to use this pinned binary's
default. Global routing retains explicit `GRT_SEED=1`. These exact policies must
be shared by baseline and candidate runs. No placement repeatability claim has
yet been established by a second completed run.
The runner also overrides `CORNER=TC CORNERS=typical`: synthesis and construction
use TT only, as agreed; SS/FF are evaluated in fresh independent STA processes.
The earlier `abc-compatible-v2` probe used three construction views and was
stopped before completion when this contract mismatch was identified. It cannot
be promoted by the independent analyzer. Its original synthesis cache still
uses the same TT `LIB_FILES`; `CORNERS` controls only OpenROAD's analysis views.
New builds set `REPORT_CLOCK_SKEW=0` to avoid expensive duplicate ORFS skew
summaries. Independent STA still checks setup/hold with propagated clocks and
preserves full clock-expanded critical paths. This changes report generation;
the `tt-abc-v3` exploration retains the original enabled summaries in its log.
The pinned binary also rejects the optional post-route `reroute` resizer move.
New builds use `OPT_POST_GRT_WNS=0`; ordinary post-route electrical/setup/hold
repair remains enabled. The complete ORFS global-route step with these settings
has been exercised on the four-cell fixture before the full-core retry.
`--cts-from build/...` reuses only a completed TT CTS checkpoint at the same
period, mapping policy and hashed inputs. It checks the completed stage log,
database copy identity and the serialized I/O/clock contract, then starts
`do-5_1_grt` in a fresh output directory. A later failure in the source attempt
remains a failure. Mismatched periods or mapping policies are rejected.
When independent corners expose electrical gaps, `--grt-from build/...` starts
an explicit TT-only post-route ECO from immutable incoming DB/SDC files. It
reuses the pinned ORFS environment and existing routes, repairs slew with a
30% optimizer margin and hold with 50 ps, legalizes and incrementally reroutes.
These optimizer margins preserve the independent acceptance constraints. The
Makefile/Tcl and incoming checkpoint are hashed by the durable worker. All three
corners must be collected and reviewed again after this stage; the initial v4
run passed setup/hold but failed SS/FF slew, so it remains unqualified.
The ECO concludes with a fresh whole-design global route and antenna-model
report. Incremental demand tables describe modified nets; the final full-route
table is used for whole-design congestion review. Analysis requires the explicit
full-route completion marker as well as the hashed final checkpoint.

The following items describe the **legacy** flow in this directory:

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
