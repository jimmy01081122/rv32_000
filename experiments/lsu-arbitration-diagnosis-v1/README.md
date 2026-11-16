# Read-only arbitration diagnosis

Compare the retained A+B and bounded-arbitration-v1 models on PID, FFT and
statemate. This is a diagnostic subset, not another family score or a new CPU
candidate. RTL, ELF bytes, 10,000 ps clock and all three 10,000 ps memory settings
remain frozen. The architectural findings and proposed next experiment are in
[the diagnosis](../../docs/LSU_ARBITRATION_DIAGNOSIS.md).

`run_observer.py` relinks only the host harness against the archived generated
Verilator 4.038 objects. Compile inside `rv32ooo-fp:p1` with GCC 11.4; use the same
absolute repository mount inside and outside the container. The image ID is
`sha256:2140263677b3a378d5cab75a3d0d4fd285ddb38a1a5a1f81f5cf97db024a02d5`.
The original simulator binaries remain untouched. Build receipts hash all model,
runtime and harness inputs before and after; reference files are checked against
the published arbitration-functional inventory.

```sh
# Inside the pinned image, with the repository mounted at the same absolute path:
python3 experiments/lsu-arbitration-diagnosis-v1/run_observer.py \
  --phase build --output build/experiments/lsu-arbitration-diagnosis-v1/capture-v1
# Then on the host, using the resulting executables:
python3 experiments/lsu-arbitration-diagnosis-v1/run_observer.py \
  --phase run --output build/experiments/lsu-arbitration-diagnosis-v1/capture-v1
python3 experiments/lsu-arbitration-diagnosis-v1/review_observer.py \
  --capture build/experiments/lsu-arbitration-diagnosis-v1/capture-v1 \
  --output build/experiments/lsu-arbitration-diagnosis-v1/review-v1
python3 experiments/lsu-arbitration-diagnosis-v1/compare_schedules.py \
  --capture build/experiments/lsu-arbitration-diagnosis-v1/capture-v1 \
  --review build/experiments/lsu-arbitration-diagnosis-v1/review-v1 \
  --output build/experiments/lsu-arbitration-diagnosis-v1/schedule-comparison-v1.json
```

Use fresh output names when reproducing; all tools reject replacing prior runs.
Six observer on/off pairs must match the accepted stdout (only the validated ELF
path is normalized), memory audit and complete profile. The 88-word binary schema
retains raw packed fields each cycle. Gzip is lossless; both decoded bytes and
compressed files have hashes. Do not interpret unused/stale packed requests as
accepted operations: handshake, valid, flush and state qualify every event.

The reviewer calibrates 39 common fields over all 8,256 A+B PID cycles against the
independently captured, publicly archived VCD extraction. All six cycle partitions
and per-PC accounts must reconcile. Ordered retired PC/instruction hashes match
between variants. Load tags remain live until retirement, retirement-time branch
flush, or ROI-end censoring; tag reuse, non-control flushes and incomplete lifecycle
denominators are rejected. The three ROIs have no censored external reads. A load
without an external ROI request may have forwarded or crossed the ROI boundary;
the reviewer does not silently label all such loads as forwarded.

Two actual-data negative controls corrupt a registered commit PC and truncate a
row. `compare_schedules.py` pairs every retired store by ordinal/PC, reconciles
mark-to-retire durations with the exclusive store-ack bucket, and retains complete
raw windows for three representative stores. Its guard coverage is observational;
changing arbitration changes later schedules, so coverage is not a speed estimate.

Public evidence is under
[`docs/evidence/2026-11-16/lsu-arbitration-diagnosis`](../../docs/evidence/2026-11-16/lsu-arbitration-diagnosis/README.md).
Original model/runtime objects remain in the linked earlier functional archive;
the diagnosis archive adds the two relinked executables and all six raw streams.
