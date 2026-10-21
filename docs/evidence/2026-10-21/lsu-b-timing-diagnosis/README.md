# B v1 timing diagnosis — 2026-10-21

**Diagnostic work is complete; B v1 remains timing rejected.** This separate
archive changes no original baseline/A/B evidence, CPU RTL, scored simulator,
physical construction policy, or acceptance rule. The current interpretation
and proposed next choices are in [the review](../../../LSU_B_TIMING_DIAGNOSIS.md).

The source checkout is `0804b7c37ad8a4b54a3391010ca608f024c1d4e6` on
`codex/lsu-b-marking`; its B CPU/physical inputs are unchanged from clean
`95ac0dd6451a1799f9f3fe948c7b74c02f5fccd2`. These are read-only analyses of
original completed implementations, not another synthesis/place/route run.

## Results and checks

- [Native collection](context/native-probes.json): 12 independent processes,
  real exit 0 and completion markers, unchanged guarded inputs and 204 pinned
  tool/platform hashes before and after. Nine original TT/SS/FF routed results
  reproduce within 0.000001 ps. Three SS synthesis views deliberately use zero
  wire delay and ideal clock; they do not qualify a physical clock.
- [Independent review](context/diagnostic-review.json): 72 selected cell/net
  decompositions, exact master/instance/pin connectivity of 534,342 synthesis
  cells, unchanged baseline simulator and all 2,060 indexed files in five old
  baseline/A/B archives checked. This is not full RTL/netlist equivalence.
- [Path comparison](context/native-path-comparison.json): worst FP data delay
  baseline/A/B is 9.609165/9.480563/12.214929 ns routed and
  6.518351/6.651498/8.455249 ns in the synthesis zero-wire view. Matching FP
  sink bit 115 also shows a 1.971862 ns pre-placement B-minus-baseline gap.
  Loaded cell arcs retain placement, fanout and slew effects.
- [Structural comparison](context/mapped-cone-comparison.json): the lowered
  FPU modules are byte identical; the routed critical paths contain
  105/106/137 original non-buffer mapped cells. Distinct structural hashes
  do not imply different logical functions. No particular opcode, optimizer
  pass or inevitable B architecture penalty is established.
- [Connectivity review](context/synthesis-connectivity-review.json): source
  parser counts match original Yosys statistics; all three recovered synthesis
  databases exactly match the recorded netlists after scalar-alias and OpenDB
  literal bracket/slash escape normalization. Earlier representation-only
  checker outputs are retained in context. The final checker is authoritative.
- B FF has two violating endpoints, −0.332734 and −0.298511 ps. The same
  ready-to-store-tracking path has +52.584854 ps in TT and −0.332734 ps in FF.
  No hold ECO was performed and no negative slack was waived.

## Contents and replay

`native/` keeps all original new tool outputs. `reported-paths/` extracts each
original worst group without mistaking the first printed block for the global
worst path. `inputs/` keeps original netlists, lowered RTL, synthesis checkpoints,
metadata, statistics and source guards. `connectivity/` retains the complete
OpenDB connection exports. `context/` contains exact scripts and receipts.

Verify this package from this directory:

```sh
sha256sum --strict --quiet -c SHA256SUMS
```

[Copy inventory](copy-inventory.json) binds each published copy to its original
repository path and SHA-256. For auditing the existing result, restore these
source paths in an isolated checkout: decompress `encoding=gzip` copies;
identity copies retain their original encoding. Existing files must have the
recorded hash before reuse. Restore the four temporary raw ODB paths listed in
`context/replay-inputs.json` from their gzip sources. Restore the original final
routed ODBs using [external checkpoint references](external-checkpoints.json).
The references bind to the old committed gzip files and verified raw hashes;
no duplicate routed DB is silently substituted.

For a fresh native replay, start with a fresh ignored
`build/experiments/lsu-b-diagnosis-v1` output directory containing only the helper
sources and restored original implementation inputs; do not prepopulate its
`native/`, `replays/` or result JSON. The pinned image is
`rv32ooo-orfs:8359fde-flat`, local ID
`sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33`.
Use a disposable container named `rv32-lsu-b-diagnosis-v1`, user 1000:1000,
repository mounted at `/workspace`, pinned ORFS checkout at `/orfs-source:ro`,
and entrypoint `/bin/sleep infinity`. Do not run two large VFS tool runtimes
concurrently. `run-probes.py` requires fresh output paths and validates original
mapped/final identities; its exact commands and source guards are also saved.

`export-synth-connectivity.py` runs with pinned `openroad -python`; other Python
helpers run on the host. The dependency order is collection/export, reported
path extraction, connectivity/cone/path comparisons, then `review-diagnostics.py`.
Restore every input identity before repeating that review. The zero-wire
synthesis views have no CTS/route and their hold violations are diagnostic,
not a revision of the already qualified baseline/A operating points.

[Runtime cleanup](context/runtime-cleanup.json) records the idle-only container
removal and losslessly recoverable replay duplicate cleanup; pinned images and
original archives are retained. [Idle-cache compaction](context/idle-cache-compaction.json)
preserves original bytes/hashes in gzip for completed B intermediates. Restore
raw paths before old scripts require them. No original archive index changed.
