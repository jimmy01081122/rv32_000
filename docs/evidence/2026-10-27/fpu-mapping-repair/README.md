# Shared FPU mapping evidence — 2026-10-27

Scope: repair the synthesis comparison boundary after the
[B timing diagnosis](../../../LSU_B_TIMING_DIAGNOSIS.md). See the
[review](../../../FPU_MAPPING_REPAIR.md) and
[implementation/replay guide](../../../../experiments/fpu-mapping-v1/README.md).
No CPU RTL, scored simulator, workload, memory contract or frozen v1 baseline
changed. This archive establishes a mapping/verification milestone, not PPA
admission or a replacement baseline.

## Evidence chain

- `runs/keep-v2`: three completed native boundary-preserving core syntheses.
  `runs/mapping-comparison-v1.json` rejects keep-only mapping: all three differ.
- `runs/shared-unit-v1` and `shared-unit-repeat-v1`: standalone FPU native jobs,
  exact inputs, SDCs, logs and mapped results. Independent runs have the same
  25,855-cell/100-DFF graph; `runs/repeat-comparison.json` records it.
- `runs/shared-linked-v1`: identical FPU body inserted into each unchanged core
  body, exact port ABI and link manifest. `runs/link-replay-review.json` checks
  the replayed output bytes. `runs/unit-readback-review.json` binds the actual
  linked Verilog to the native mapped JSON used by formal checks.
- `runs/shared-native-v1`: native ORFS imports without remapping; original
  compressed OpenDBs and logs. `runs/shared-readback-v1` contains flattened
  references, all-cell/pin readbacks, pruning review and independent SS probes.
  All 525,189 retained cells match. The removed subgraphs drive no retained cell
  or top output; the earlier strict missing-cell rejection is preserved too.
- `runs/mapping-cec-v2`: exact pre/post state-cut JSON, BLIF, scripts and ABC
  logs. CEC passes, with an actual bit-corruption counterexample. ABC also returns
  zero for inequivalence, so the log result is essential. `runs/state-cut-review.json`
  independently verifies the transformation and common 100-bit state/clock
  identity; its negative review rejects the deliberately corrupted model.
- `runs/review-controls-v2`: four actual-data reviewer negatives, all rejected.
- `runs/gate-sim-v4`: native CXXRTL generation inputs and model. The final
  `runs/gate-sim-v9` host qualification records compiler flags, input/executable
  hashes, real exit codes and bounded cycle regression. Runtime headers reside
  under `runs/gate-sim-v1/include`. Native model bytes are under v4; v9 adds
  only a host `optimize("O0")` attribute to the giant eval function. Its generation
  reference verifies that undoing this annotation restores the native bytes.

Native `run.json` files retain `passed:false`: the durable runner sets
`flow_completed` and real `returncode` but deliberately does not grant physical
admission. Do not rewrite or misinterpret that field as a new PPA pass.

## Preserved failures and limits

The first wrapper trial used an incorrect module-count assertion. Keep-only
mapping failed stability. Early formal attempts exposed missing library models,
unhelpful internal matching and a sequential SAT clock-model error; the faulty
positive results are not accepted evidence. Explicit `clk2fflogic` fixtures pass
positive and reject negative examples. The PDR negative detects failure but its
witness postprocessing lacks `yices-smt2`, so it is not a clean negative pass.

`equivalence-full-v1` and `equivalence-shared-v1` retain full RTL-to-mapped EQY/PDR
timeouts (900 s strategy limit). Full equivalence is unproven. Large intermediate
proof databases are excluded; configs, commands, logs and statuses are retained.
The pinned Yosys/ABC mapping CEC is independently replayable from its archived
models; do not treat it as proof of all earlier RTL transformations.

Early CXXRTL generation failed before unsupported cells were lowered correctly.
Host forced-inline compiles were stopped/interrupted and are not passes. The
first executable failed because the harness sampled combinational outputs before
post-clock propagation. The final driver explicitly reevaluates after FF commit
and checks stability with the clock held constant, before comparing all output
bits. Original drivers and failed results remain under v3/v5/v6; slower host variants
are retained separately. The final host build disables forced inline attributes,
compiles the giant eval function at O0, and optimizes runtime helpers at O2.
No generated model statements change; runtime headers, assertions and CPU inputs
remain fixed. This is a two-state model
comparison, not an independent IEEE-754 oracle or full ISA coverage.

SS probes are zero-wire/ideal-clock diagnosis only. No new routed clock, area or
system-time score is admitted. B's original FF hold rejection remains open.

## Provenance and restoration

Native flow source parent is `0798c75`, following initial wrapper commit `9c52d68`.
Later experiment helpers are identified by archived file hashes and the result
commit, not represented as an earlier clean-source CPU qualification.
ORFS is `8359fde81991e6118b15b8a93fcde606b577794d`, image
`rv32ooo-orfs:8359fde-flat`, image ID
`sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33`.
The prior 204-file tool/platform manifest is copied under `inputs/docs/evidence`;
the runtime cleanup receipt records its successful check before idle container
removal. Images were retained. Compiler identity is in `runs/host-compiler.json`.

`copy-inventory.json` gives original workspace paths, stored and decoded SHA256,
compression, and sizes. Large payloads are losslessly gzipped; source files that
were already gzip retain their original bytes. In a scratch checkout, copy the
stored bytes when `source_sha256 == stored_sha256`, otherwise decompress before
restoring to `source`. Verify the restored source hash. The earlier driver in
`inputs` belongs to failed attempts; `inputs-final` contains the reviewed driver.
Original `job.json` paths assume the repo is mounted as `/workspace` inside the
pinned runtime. Host commands use `/workspace/rv32_000`; adjust those paths in
new replay records, preserving originals. Use fresh output directories.

`SHA256SUMS` covers every archived file except itself. Validate it from this
directory with `sha256sum --strict --quiet -c SHA256SUMS`. The copy inventory
also permits decoded-byte checking. Prior baseline/A/B archives were checked
separately; their contents and acceptance status remain unchanged.
