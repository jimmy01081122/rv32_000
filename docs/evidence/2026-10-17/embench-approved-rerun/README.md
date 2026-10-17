# Approved Embench 19-workload functional rerun

Source commit: `7ba020297da6e6cdc4e5857fdde6ff57fec627d6`; project and Embench trees were clean before and after execution.
Embench commit: `0466a18e4f6b47e19598d7c6ba72916d54b68f65`.
UTC: 2026-10-17T13:10:38.696790+00:00 to 2026-10-17T13:29:28.495781+00:00 (1129.8s host wall time for the suite).

Functional gate: **19/19**. Complete commands, stage results and ELF hashes are in [the summary](embench-full-summary.json).
Each workload was built and self-checked natively, built for RV32IMF, run on Spike, and self-checked on the DUT.
Self-checks use the upstream result checks and tolerances. This is not a full instruction-trace or FP-flag comparison.

Conditions: `-std=gnu11 -O3 -march=rv32imf_zicsr -mabi=ilp32f`, `WARMUP_HEAT=1`, `CPU_MHZ=1` scaling.
DUT defaults: 1 MiB RAM, data latency 1 cycle, random extra delay 0, no random seed supplied; 25,000,000-cycle / 180s per-program limits.
The current DUT build does not enable Verilator assertions. Memory service, timing-window and physical contracts remain provisional.
The CPU_MHZ scaling value does not establish an ASIC operating frequency.

These are diagnostic cycles, not a frozen AP5B performance/PPA baseline or evidence of the 1.20x / 1.10x goals.

| Workload | Native | Spike | DUT | Diagnostic ROI cycles |
| --- | --- | --- | --- | ---: |
| `aha-mont64` | PASS | PASS | PASS | 5,356,670 |
| `crc32` | PASS | PASS | PASS | 5,402,220 |
| `cubic` | PASS | PASS | PASS | 14,490,894 |
| `edn` | PASS | PASS | PASS | 4,754,496 |
| `huffbench` | PASS | PASS | PASS | 3,377,028 |
| `matmult-int` | PASS | PASS | PASS | 4,193,163 |
| `minver` | PASS | PASS | PASS | 878,777 |
| `nbody` | PASS | PASS | PASS | 5,893,151 |
| `nettle-aes` | PASS | PASS | PASS | 5,203,513 |
| `nettle-sha256` | PASS | PASS | PASS | 4,307,562 |
| `nsichneu` | PASS | PASS | PASS | 7,298,679 |
| `picojpeg` | PASS | PASS | PASS | 5,300,988 |
| `qrduino` | PASS | PASS | PASS | 4,524,180 |
| `sglib-combined` | PASS | PASS | PASS | 4,526,268 |
| `slre` | PASS | PASS | PASS | 4,902,163 |
| `st` | PASS | PASS | PASS | 7,165,107 |
| `statemate` | PASS | PASS | PASS | 3,368,567 |
| `ud` | PASS | PASS | PASS | 2,775,897 |
| `wikisort` | PASS | PASS | PASS | 2,173,042 |

[Run context](run-context.json) records exact source, image IDs, simulator hash and command; [binary checks](binary-checks.json) verify the ELF ISA/ABI and hashes.
[Gate report](dut-gate-report.json) keeps all 19 results. [Reproducibility comparison](reproducibility.json) checks ELF hashes and diagnostic metrics against the earlier run.
Original DUT outputs are under [dut-logs](dut-logs/). Other original logs, including empty successful outputs, are stored by their runtime path in [other-logs.json](other-logs.json); [log-index.json](log-index.json) maps paths and hashes.
Large ELFs and disassemblies remain regenerable; their identities and sizes are in [regenerable-artifacts.json](regenerable-artifacts.json).
Raw size output includes port/runtime reservations and is not an application working-set measurement.

Reproduce from the source commit above:

```bash
make check-fp-env sim-build JOBS=4
make qualify-embench-fp-dut JOBS=4
make summarize-embench-fp-dut
```

After copying this directory, verify archived files with `sha256sum -c SHA256SUMS` from this directory.
