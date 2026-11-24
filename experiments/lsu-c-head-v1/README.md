# Registered external head-load retirement (C)

C inherits ROOM's LSU arbitration. A successful external load can retire on the
edge that writes its buffered response to the physical register file. Eligibility
requires a live incomplete load at the ROB head, a full tag match (sequence and
slot), run state and a deasserted reset. Both the ordinary completion bus and the
retirement trace use the same subword extraction. A forwarded or faulting
completion uses the ordinary ROB completion path. Registered head state controls
trap, redirect and store acknowledgement.

The [contract](manifest.json) binds C to the ROOM parent, original baseline, 27
ELFs, FP contraction policy and fixed 10,000 ps memory. See the [common-clock
results](../../docs/evidence/lsu-c-head-v1/README.md).

## Replay

The original run used the checkout at `/workspace/rv32_000`. Recorded commands
in the evidence contain that path. Restore the verified evidence bundle in a
fresh checkout at that location to run the reviewer. For a new measurement use
a clean checkout with the frozen ELFs available and fresh build output paths.

Run the core build and qualification in the pinned `rv32ooo-fp:p1` container,
with the checkout bound at the same absolute path. Run the pin controls in
`rv32ooo-sim:g1` or the FP image. Run the timed workloads and independent review
on the host with the generated simulator.

```sh
exp=experiments/lsu-c-head-v1
base=build/experiments/lsu-c-head-v1
python3 scripts/build_experiment_sim.py --experiment "$exp/manifest.json" --out "$base/build-v1" --jobs 2
python3 scripts/qualify_cpu_experiment.py --experiment "$exp/manifest.json" --build-summary "$base/build-v1/summary.json" --out "$base/qualification-v1"
python3 "$exp/check_head_load.py" --out "$base/unit"
python3 scripts/measure_cpu_experiment.py --experiment "$exp/manifest.json" --build-summary "$base/build-v1/summary.json" --out "$base/measurement-10000ps-v1" --period-ps 10000
python3 "$exp/review.py" --output "$base/review.json"
```

The CPU comparison uses 19 equally weighted Embench programs. DSP and matrix/ML
each contribute four workloads and 50% of the FP32 score. Pin controls compile
the actual ROOM and C ROBs, verify the response edge and precise trace, and
reject each model under the other model's timing expectation.

The synthesis front end runs in `rv32ooo-syn:g1`. It reads the same frozen
source set with the synthesis preprocessor configuration.

```sh
python3 scripts/lower_baseline_rtl.py --experiment "$exp/manifest.json" --out "$base/lowering/C.v"
yosys -s "$exp/structural.ys"
```

## Local tool storage

`python3 scripts/activate_project_image.py fp` restores the pinned functional
image from this host's local archive. Use `sim`, `syn` or `orfs` to select the
respective image. The existing FP and sim tags share all six sim layers. Native
ORFS is held in `build/tool-cache/orfs-8359fde.tar.gz` with its verification
receipt. The activation command uses the project host's local Docker socket.
To switch this VFS host to the physical phase, park the unused functional tags
before loading ORFS. Parking checks the exact archive digest, the live image ID
and attached containers.

```sh
python3 scripts/activate_project_image.py fp --park
python3 scripts/activate_project_image.py sim --park
python3 scripts/activate_project_image.py syn --park
python3 scripts/activate_project_image.py orfs
```

Park `orfs` after the physical session and activate `fp` and `sim` for functional
work. On another host, the project Dockerfiles and physical toolchain lock
describe the builds.

Thirty-four generated A+B construction files are held in three verified local
checkpoints. To materialize them again, allow 1.31 GB of output space and run
`python3 experiments/lsu-c-head-v1/restore_ab_files.py`. An optional
`--destination DIR` restores an independent copy for comparison. The published
A+B inventory supplies the checkpoint digests.
