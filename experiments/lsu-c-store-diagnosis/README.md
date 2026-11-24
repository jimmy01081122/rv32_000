# Store retirement on candidate C

The diagnostic uses the C normal Verilator model and the accepted 10,000 ps core and memory settings. The observer runs in the host simulator harness. A control executable relinked from the same objects must match the scored binary byte for byte. Every benchmark replay must reproduce its published stdout, memory audit and full ROI profile.

The observer tracks full ROB tags and slot reuse from allocation. It samples both registered operand-ready bits in the integer issue queue for integer and FP stores. Src0 supplies the address base and src1 supplies the store data. The AGU writes the effective address, mask and formatted data together. A sample timestamp labels the rising edge immediately following the settled low phase. Retirement and trap membership are read back from the registered commit trace after that edge. Operand-ready time records the first observed ready bit in the issue queue. An operand can already be available before dispatch.

The normal-run counters span the same two retired markers as the C score. A tag may enter the IQ before the opening marker. Per-store durations include the head and handshake history of every retired store in the ROI. The reviewer checks those sums against the independent ROI cycle partition, retire counts and external accepted writes. The five directed controls observe the whole run, including error returns. The 40 ns and periodically blocked ports are directed controls only.

## Reproduction

Use `/workspace/rv32_000` as the checkout path. Restore the [C evidence](../../docs/evidence/lsu-c-head-v1/README.md) for the frozen ELFs and original workload reference files. The [diagnostic bundle](../../docs/evidence/lsu-c-store-diagnosis/README.md) contains the Verilator objects for relinking, both executables, 27 counter sets, representative tagged timestamps, and the compressed original-binary VCDs for the directed controls. Build with GCC 11.4 in `rv32ooo-sim:g1` with the checkout mounted at its absolute host path. An independent aggregate review only needs the diagnostic bundle and tracked files.

```sh
exp=experiments/lsu-c-store-diagnosis
output=build/experiments/lsu-c-store-diagnosis/reproduction
python3 "$exp/run.py" build --out "$output"
python3 "$exp/run.py" run --out "$output" --jobs 2
python3 "$exp/controls.py" "$output"
python3 "$exp/review.py" "$output" "$output/review.json"
```

`wait_issue_write` counts an accepted external write while the ROB awaits acknowledgement. `wait_yield_new_read` counts an accepted read competing with a ready store. `wait_load_response_edge` counts the return of an in-flight load on a waiting-store edge. `unmarked_*` are subsets of the corresponding wait counts. `pre_*` classify the separate interval during which the store is at the head but its ROB entry is incomplete. `head_capture_port_free` counts the subset of head AGU capture edges with a matched SQ slot, aligned address, no flush, no request on the bus, a ready port, no external transaction in flight and capacity for a response. Its percentage describes observed opportunities under this schedule. Only a separate RTL experiment can measure the resulting change in program time.
