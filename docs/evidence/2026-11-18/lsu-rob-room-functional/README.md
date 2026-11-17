# ROB-space arbitration functional evidence

The candidate requires at least two free ROB slots for a new first-head load
bypass. Held loads retain ownership under backpressure. Original baseline,
frozen ELF bytes, memory times, two-family scores and targets are unchanged.

This archive includes both unit attempts (the first failed filename/module-name
lint), the repaired checker and actual parent/candidate/mutant models, clean
normal/assert core builds, complete qualification, all 27 workload logs/profiles/
memory audits/ELFs, independent reviews and the five-stage pipeline receipts.
It does not qualify new physical timing or area.

See [results and limits](../../../LSU_ROB_ROOM_REVIEW.md) and
[the experiment contract](../../../../experiments/lsu-rob-room-v1/README.md).
Original A+B, arbitration-v1 and baseline reference files are reused from
[the prior functional archive](../../2026-11-16/lsu-arbitration-functional/README.md).
Restore those earlier inputs before replaying the independent full comparison.
Their published inventory is retained here; reference measurements are not relabeled.

Verify public files and every decoded member without extracting:

```sh
python3 experiments/lsu-load-arb-v1/verify_archive.py docs/evidence/2026-11-18/lsu-rob-room-functional
```

Only extract verified evidence into a fresh review checkout. All members use
repository-relative paths; prior execution commands retain their original paths.
