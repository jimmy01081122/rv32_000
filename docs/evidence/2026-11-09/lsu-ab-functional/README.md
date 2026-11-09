# A+B functional milestone and integer-divider diagnosis

Source `3f079c1c3d7b53c50beb13bc2d8bf366ac42999f` is the clean A+B model,
qualification and complete 27-workload measurement revision. All pass.
This archive does not qualify A+B physical timing or area.

- Four actual RTL variants × 83 pin-driven cases, plus three negative controls.
- Directed 18, Spike 18, interface 48, fixed-memory 58, finite FMA 3,400.
- All 27 frozen workloads; 3,629 numerical values and identical per-PC work.
- Common 100 MHz / 10 ns memory: Embench 1.073943192×, FP32 1.088247938×.
- Six B divider observer off/on/reference pairs and 48 real instruction controls;
  all 27 reference profiles independently checked for workload selection.

`functional-evidence.tar.gz` contains 1,395 payloads, including generated normal
and assertion models, raw logs, traces, profiles, memory audits, ELFs, exact
observer sources/objects and retained baseline/A/B reference measurements.
Both failed unit attempts and the assertion-conflict source are preserved.
An interrupted image-cache backup is operational metadata, not a positive test.

Archive: 9,588,510 bytes; SHA256
`f5a26976ff6ac04e0f633beadfe08d0e7aea89282e959d69a0fdfb9928ccb995`.
Every decoded payload was independently checked against `inventory.json`;
`SHA256SUMS` covers the archive, inventory and copied review reports.

Extract into an empty directory. Payload paths preserve repository-relative
locations; use the recorded source/model identities for historical replay.
Read [the review](../../../LSU_AB_REVIEW.md) for the five regressions versus A,
operand-denominator limits and remaining physical qualification.
