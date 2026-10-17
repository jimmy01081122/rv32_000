# 2026-10-17 qualification evidence

This directory preserves the earlier FP-profile diagnostic run. The later
[approved full-suite rerun](embench-approved-rerun/README.md) records a clean
source commit, 19/19 native/Spike/DUT checks and matching diagnostic outputs.

The earlier snapshots below omit generated ELFs, disassemblies and some logs.
The ignored `build/qualification/` directory is reused by later runs; regenerate
those outputs with the commands in [the progress review](../../PROGRESS_REVIEW.md)
and use each archived run's source and tool identities.

- [Embench full summary](embench-full-summary.json): commands, source/tool probes,
  return codes, ELF hashes and references to raw logs for all 19 workloads.
- [DUT gate report](embench-dut-gate-report.json): fixed 19-item denominator,
  individual functional checks, ROI and total cycles, simulator binary hash.
- [DUT logs](embench-dut-logs/): the 19 original simulator outputs, including
  each program's self-check and cycle report.
- [FP source summary](fp-source-summary.json): pinned CMSIS-DSP, KissFFT and
  PolyBench/C identities.
- [FIR pilot summary](fir-pilot-summary.json), [DUT log](fir-pilot-dut.log),
  [native log](fir-pilot-native.log) and [ELF attributes](fir-pilot-attributes.log):
  provisional 32-tap, 256-sample numerical probe. Spike's MMIO console is
  silent; its successful exit is recorded in the summary.

The Embench run used a working tree with the FP-store bypass fix before that
source change was committed. The `repository` probe in the generated JSON is
therefore the previous HEAD
`bff6629bfe00a2e3ec38f797fc64994238fb556f`, not a complete source snapshot.
The FP-store source fix was subsequently committed as
`8bf3e21dc2ec43b93439e871d6e0bd6fb7aa5807`. The exact simulator
binary SHA-256 is `44d59f5b29fe427e20988799d2780e127b15f833f21e10a3af7348361e54c1c7`;
the qualifier script SHA-256 is
`677e52f1c508a6d79c93a9632c47f6014c23d02dcff68751e8d6dac5280f340a`.
This run establishes a functional diagnostic, not a frozen performance or PPA
baseline. A clean-commit rerun is required for the latter.
