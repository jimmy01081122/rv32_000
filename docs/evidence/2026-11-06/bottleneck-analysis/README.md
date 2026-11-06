# Retained-workload bottleneck analysis — 2026-11-06

Read-only post-processing of accepted baseline/A/B common-clock results; no new
benchmark, simulator, workload, RTL or physical build. All 81 profiles pass the
existing retained-profile validator. A uses the November completion's fresh
100 MHz replay, B uses its accepted 100 MHz completion, and baseline uses its
frozen formal 100 MHz measurement. I/D memory remains 10 ns.

`summary.json` records every source hash, all wait partitions/phases, per-PC
RV32M integer decomposition, IPC and instruction-count bounds. `workloads.csv`
is a compact per-case view; it does not change official scoring. Each integer
per-PC head-wait sum reconciles to its original mutually exclusive bucket.
Wait positions do not establish pure execution latency or removable cycles.
The zero-stall single-retirement ceiling assumes unchanged retired instruction
count and 100 MHz; it is an ideal bound, not a prediction.

The accepted A/B review hashes and original baseline manifest are pinned by the
analyzer. Existing validation checks profile/ELF/log/model hashes, exact 27-case
sets, cycle partitions and zero trace/layout mismatches. Recomputed scores equal
the accepted results. Raw profiles remain in the unchanged prior archives:
[A](../../2026-11-05/optimization-135-A/README.md) and
[B/reference](../../2026-10-29/lsu-b-complete-validation/README.md).
This folder stores derived data, with original working paths mapped in the JSON;
restore the prior input artifacts at those paths before re-executing analysis.

```sh
python3 experiments/optimization-135-v1/analyze_bottlenecks.py --output /tmp/new-rv32-bottlenecks
```

The output directory must not exist. Analyzer/validator SHA256 and the parent
commit are recorded; this report does not label the newly written analyzer as
having run from an already committed clean source. The discussion and diagram
are in [the report](../../../BOTTLENECK_ANALYSIS.md).
