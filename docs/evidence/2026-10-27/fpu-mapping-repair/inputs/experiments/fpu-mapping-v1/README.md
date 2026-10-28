# Shared FPU mapping experiment

Authorized after the [B timing diagnosis](../../docs/LSU_B_TIMING_DIAGNOSIS.md).
See the [repair report](../../docs/FPU_MAPPING_REPAIR.md) and
[raw archive](../../docs/evidence/2026-10-27/fpu-mapping-repair/README.md).
The FPU RTL, interface, arithmetic and latency are unchanged. This versioned
synthesis experiment does not replace the frozen v1 physical baseline.

## Implementation

1. `run_synthesis.py` runs three frozen lowered cores with pinned ORFS and
   `SYNTH_KEEP_MODULES=rv32_ooo_fp_execute`. The wrapper saves pre/post-ABC and
   final mapped FPU checkpoints. **Keeping the boundary alone failed** the graph
   comparison: baseline, A and B still map differently.
2. Extract the byte-identical FPU and synthesize it as the standalone top, using
   the same 5,500 ps ABC constraint, libraries and native passes. The archived
   `shared-unit-v1/job.json` records the exact command; `shared-unit-repeat-v1`
   independently repeats it in a fresh work directory.
3. `link_shared.py` copies each core module body byte-for-byte, replacing only
   its FPU with that common mapped body. It checks port ABI, native completion,
   input hashes and log hashes. Native ORFS `SYNTH_NETLIST_FILES` imports the
   result without resynthesis.
4. `check_readback.py` compares actual OpenDB masters and every signal pin with
   a flattened reference. Native import removes unused logic, including flops;
   the entire removed subgraph must drive neither retained cells nor top outputs.

`compare_mapped.py` compares full graphs, including pin order, fanout and feedback,
independent of generated names. `check_state_cut.py` verifies that CEC models
change only 100 matched DFF boundaries into arbitrary state inputs and next-state
outputs. `gate_driver.cc` compares original canonical RTL and mapped Liberty
function models on both clock phases, separately from the scored CPU simulator.

## Replay

Use the archived pinned image/source/tool hashes. Inside the runtime the repo is
`/workspace`, ORFS is `/orfs-source`. Native synthesis requires a clean checkout.
Use fresh directories and preserve all old attempts.

```sh
python3 experiments/fpu-mapping-v1/run_synthesis.py --output build/fpu-replay/cores
```

The standalone command uses the same make arguments, with
`DESIGN_NAME=rv32_ooo_fp_execute` and `VERILOG_FILES` set to extracted `fp-source.v`.
Give it a fresh `WORK_HOME` and constraint file. Repeat and compare the mapped
graphs before linking. Exact argument arrays, SDCs, source bytes and native logs
are archived; there is no hidden change to the ABC arguments.

After restoring archived inputs into a scratch checkout, replay the host link
and real-data negative controls (create the output parent directory first):

```sh
python3 experiments/fpu-mapping-v1/link_shared.py \
  --cores build/experiments/fpu-mapping-v1/keep-v2 \
  --unit build/experiments/fpu-mapping-v1/shared-unit-v1 \
  --output build/fpu-replay/linked
python3 experiments/fpu-mapping-v1/review_controls.py \
  --unit-json build/experiments/fpu-mapping-v1/unit-from-verilog.json \
  --readback build/experiments/fpu-mapping-v1/shared-readback-v1 \
  --output build/fpu-replay/negative-controls
```

The archive retains exact Yosys/ABC scripts, cut-point JSON/BLIF models, CXXRTL
generation job/model, runtime headers and host build/run script.
`copy-inventory.json` identifies original paths, compression and stored/decoded
hashes. Restore compressed payloads in a scratch checkout; never rerun inside
the evidence archive or overwrite an original job's status.

## Admission limits

Common mapping and ABC transition equivalence are established. Full RTL-to-mapped
sequential formal equivalence is **unproven (900 s timeout)**. Cycle regression is
bounded testing, not an independent IEEE-754 oracle. Synthesis STA is zero-wire,
ideal-clock diagnosis, not a qualified clock or area. Fresh same-flow baseline/A/B
physical implementations and independent TT/SS/FF checks remain necessary;
B's original FF hold rejection remains unchanged.
