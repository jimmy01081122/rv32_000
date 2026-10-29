# B complete validation — native runs completed 2026-10-29 UTC

Final documentation/archival review: 2026-10-30 (Asia/Taipei).
The [result report](../../../LSU_B_COMPLETE_VALIDATION.md) completes the B
experiment contract at global-route research scope. Verification passes;
both independent 1.20× performance targets remain unmet. The frozen v1 baseline
is unchanged. No A+B, new CPU RTL, FPU arithmetic or pipeline change is included.

## Final admission

- [Completion summary](runs/completion-summary.json) binds the final evidence.
- [100 MHz review](runs/final-common-clock-review.json): all 27 workloads and
  3,629 FP32 values pass; Embench 1.029459×, FP32 1.009599×.
- [104.17 MHz review](runs/final-fastest-review.json): all 27 and 3,629 values
  pass; Embench 0.748705×, FP32 0.719680×. Fixed 10 ns memory requires two cycles
  at 9.6 ns, so the faster CPU clock performs worse in this model.
- B area 21,309.821820 µm², 0.965070× original baseline, 0.989062× the baseline
  rebuilt in the same new flow. Only the latter isolates B within this flow.
- Final three-corner boundary: baseline 9.4 ns fail / 9.5 ns pass;
  B 9.5 ns fail / 9.6 ns pass. Both pass 10 ns. No WNS extrapolation.

## Evidence layout

`runs/fpu-state-relation-v1` contains original/Liberty models, output-state
relation, all seven generated models, lowering scripts, BLIF and native ABC logs.
Both independent reset-to-zero obligations and arbitrary related-state/input
step plus complete-output equivalence pass. The negative bit obligation is
correctly inequivalent. `fpu-negative-controls-v1` rejects two actual RTL mutants
and four structural/model faults. `fpu-frontend-replay-v1` reproduces the native
frontend and generated models. The definedness review excludes X/Z from functional
Boolean proof bits. `formal-to-physical-link-review.json` binds that proof to the
actual shared mapped JSON, Verilog readback and linked baseline/B netlists.

This establishes full two-state FPU implementation equivalence after one
synchronous reset edge, with no internal arithmetic cutpoints or operand/opcode
assumptions. The pinned sv2v original FPU is the golden implementation; frontend,
Liberty, Yosys and ABC are the stated trust boundary. IEEE-754 specification and
full CPU ISA conformance remain separate coverage work.

`runs/physical-{B,baseline}-v1` retains native GRT and the failed B 100 ps hold
ECO. The explicit stop, nonzero exit and pre-ECO failures are preserved.
`physical-*-v2/eco` contains the common 40 ps hold / 45% slew repair; the baseline
FF hold failure is still rejected, while B passed. `physical-*-v3/guard` contains
the first failed name check, with its exact source under `failed-guard-v1-source`.
The native API uses the requested name as a prefix; the corrected unique-added-cell
check was rerun at clean `a5cc433` into `physical-*-v4/guard`.

The final guard adds exactly one Liberty-proven Y=A BUFx2 per core, preserves all
original cells/pins/ports, and performs full routing. The connectivity JSON and
native log agree on 345,677 original cells, 1,915,669 pins and 1,046 ports across
the two cores. Final overflow, placement, antenna and electrical violations are
zero. `independent-boundary-v1` under each v4 guard contains independent native
TT/SS/FF reports and actual adjacent faster failures. `guard-admission-controls-v1`
passes positive data and rejects all seven corruptions. Earlier formal/hold40
reviewer controls are retained under their original reviewer hashes.

`measurement-10000ps-v1` and `measurement-9600ps-v1` contain both fresh complete
DUT runs, original stdout, numerical outputs, profiles, memory/stack audits and
source/executable identities. All per-PC/instruction/kind counts match; these
maps are not ordered traces. The old normal/assert binaries and functional
qualification were reused with fresh provenance review, not rebuilt or rerun as
a new full Spike suite. Their native records are in the unchanged
[B v1 archive](../../2026-10-21/lsu-b/README.md). Common FPU input mappings and
prior failed EQY attempts remain in the unchanged
[FPU repair archive](../../2026-10-27/fpu-mapping-repair/README.md).
`retained-evidence-review.json` verifies all 712 and 771 indexed files respectively.

Native `run.json` may retain `passed:false`: it records `flow_completed`, actual
exit and unchanged input hashes; admission is separate. Workload summaries retain
`physical_qualification_pending:true` from their measurement stage. Final reviews
resolve that condition using the new actual timing records; originals are not edited.

## Sources, restoration and checks

Native GRT source is `6493269`; hold40 is `f2c8b45`; final guard is `a5cc433`.
The two fresh workload runs have clean sources `6493269` and `f2c8b45`, using the
same frozen B executable. Final reviewer changes and docs are identified by exact
archived snapshots and the result commit, not represented as earlier native source.
`runs/final-source-status.json` explicitly records this distinction.

ORFS is `8359fde81991e6118b15b8a93fcde606b577794d`; image is
`rv32ooo-orfs:8359fde-flat`, ID
`sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33`.
The 204-file tool/platform manifest is under `inputs/docs/evidence`; its final
check and idle-container removal receipt are retained. Images and bind-mounted
artifacts were preserved. Compaction, private-runtime pruning and reversible
ACT4 sparse-checkout receipts record all environment cleanup.

`copy-inventory.json` maps every original `source` to a `destination`, encoding,
source hash and stored hash. For encoding `gzip`, decompress once before restoring;
for `copy`, preserve bytes, including any already-compressed `.gz` source. Several
identical large sources share one archived payload; restore each source path from
its inventory entry. `payload-deduplication.json` records these exact-byte aliases.
Large intermediate ODB caches and convenience symlinks are excluded explicitly;
all final and incoming GRT checkpoints remain recoverable. Python bytecode is omitted.

Restore in a scratch checkout, never over an original run. Restore build dependencies
from the linked older inventories as needed; those use `archive` or `stored`
for payload paths and retain their own encoding descriptions. Preserve source
hashes. Native job paths assume the repo mounted as `/workspace`, ORFS at
`/orfs-source`; host records use `/workspace/rv32_000`. Recreate v2 `grt` symlinks
to `../physical-B-v1/grt` or `../physical-baseline-v1/grt`. Negative-control fixture
symlinks can be regenerated by the retained test driver; mutated bytes are archived.

For native Yosys replay, decompress completed `.json.gz` model files first and
use fresh output paths. All native command arrays/scripts and exact predecessor
hashes are retained. The [experiment guide](../../../../experiments/lsu-b-validation-v2/README.md)
provides host-only final review and negative-control commands. Do not overwrite
original summaries when replaying; preserve any new path adaptations in new records.

Validate stored bytes from this directory:

```sh
sha256sum --strict --quiet -c SHA256SUMS
```

The copy inventory also verifies decoded original bytes. `archive-integrity-review.json`
records the final inventory/source/decoded checks. `SHA256SUMS` covers every file
except itself; all indexed files are committed, including ignored native `.log`
files. Full detailed-route/OCV/power/ISA signoff and a new-flow A comparison are
outside this B completion scope.
