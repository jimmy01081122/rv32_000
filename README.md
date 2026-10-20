# RV32 OoO CPU research project

A scalar, single-retirement-width RISC-V core targeting RV32IMF + Zicsr,
developed with SystemVerilog and open-source simulation and ASIC design tools.
The execution environment is bare metal. This is an architecture and PPA research
project; tape-out is outside the agreed scope.

General embedded performance and single-precision floating-point performance
are equally important project objectives. Workload qualification and a fresh
AP5B baseline precede the next architecture optimization.
The selected FP32 set has four control/DSP and four matrix/ML kernels with
equal subgroup weights; its [inputs and numerical contract](docs/FP32_BALANCED_PROPOSAL.md)
are frozen in the post-LSU v1 contract; all eight pass formal numerical and
fixed-time performance measurement.

## Start here

| Document | Purpose |
| --- | --- |
| [Project plan](PLAN.md) | Agreed scope, decision process and next milestones |
| [Current status](docs/STATUS.md) | Measured checks, implementation drift and open verification gaps |
| [Architecture](architecture_spec.md) | Current implementation inventory and architectural requirements |
| [Micro-operations](uop_spec.md) | Implemented packet types and their limitations |
| [Workloads](docs/WORKLOADS.md) | Approved suites and planning targets; open measurement contracts |
| [LSU candidate review](docs/LSU_OPTIMIZATION_REVIEW.md) | Fixed six-case memory sensitivity and concrete hardware options |
| [LSU interface fixes](docs/LSU_INTERFACE_FIX.md) | Backpressure / precise access faults, assertion-enabled tests and regression evidence |
| [FIR/BiCG bottleneck review](docs/FMA_BOTTLENECK_REVIEW.md) | Dynamic instruction savings, load-response/store-retirement waits and observer validation |
| [FMA contraction review](docs/FMA_CONTRACTION_REVIEW.md) | Matched off/fast cycles, numerical differences and corrected finite FMA checks |
| [Progress and baseline review](docs/PROGRESS_REVIEW.md) | Evidence gates, current blockers and decisions for discussion |
| [Session handoff](docs/SESSION_HANDOFF.md) | Environment bring-up evidence and reproduction details |
| [Documentation index](docs/README.md) | Current documents and historical references |

## Implementation snapshot

| Component | Current implementation |
| --- | --- |
| Fetch / decode / rename / dispatch / retirement | One instruction per cycle at each boundary |
| ROB | 16 entries; 12-bit sequence number |
| Integer / FP physical registers | 48 × 32 bits each |
| Integer / FP issue queues | 8 / 4 entries |
| Frontend | 8-entry instruction FIFO, 4-entry fetch tracking, 64-entry BTB and 64-entry two-bit BHT |
| Integer / FP PRF interfaces | 4 read / 3 write ports; 4 read / 2 write ports |
| Store queue | 16 allocated slots |
| Load tracking | One external transaction plus AP5B response buffer; no allocated 16-entry LQ |
| Data-memory requests | At most one outstanding transaction |

Integer and FP execution can overlap; sustained retirement IPC is at most one.
The `LQ_ENTRIES` and PRF-port constants do not fully describe the instantiated
structures; see the architecture inventory before changing their values.

The current RTL contains AP5B registered load responses. Its frozen post-LSU
global-route research baseline is 10 ns (100 MHz), 22,081.1184 µm², with all
27 formal workloads passing; see the [evidence](docs/evidence/2026-10-18/post-lsu-baseline/README.md).
Archived AP5A MHz, area, power and
benchmark numbers are linked from [historical reports](reports/README.md).

## Reproducible development

Run these commands from the repository root on a host with Git, Make, Bash and Docker:

```bash
make deps-init
make docker-build
make check-env
make lint smoke
make test diff-test diff-selftest coremark-smoke
make synth
python3 scripts/test_workflow_guards.py
```

The separate RV32IMF benchmark toolchain can be built with
`make docker-build-fp`, checked with `make check-fp-env`, and used with
`make qualify-embench-fp-reference`. The approved 19-workload suite passes native,
Spike and DUT self-checks in a [clean-commit rerun](docs/evidence/2026-10-17/embench-approved-rerun/README.md).
The post-LSU performance and global-route contracts are frozen; see the
[qualification status](docs/PROGRESS_REVIEW.md).

`make qualify-fp-balanced-dut JOBS=4` builds and numerically checks the selected
FP32 4+4 kernels on native, Spike and DUT. All eight provisional daily cases
pass; [archived results](docs/evidence/2026-10-17/fp32-balanced-qualification/README.md)
include every output, independent references and source identities. The v1
[contract](baselines/ap5b-post-lsu-v1/manifest.json) freezes their sizes, tolerances
and ELF bytes; its formal eight-case run also passes.

`make compare-fp-contraction JOBS=4` first checks exact finite FMA results/flags,
then runs matched off/fast qualifications on the same RTL. The
[FMA review](docs/FMA_CONTRACTION_REVIEW.md) records the cancellation fix,
8/8 passes per mode and diagnostic 1.113x cycle speedup from compiler contraction.
The approved main FP32 policy is `-ffp-contract=fast -fno-fast-math` (also the
qualifier default); use `--fp-contract off` for sensitivity checks. The post-LSU
baseline is frozen; the approved [LSU A experiment](experiments/lsu-a-v1/README.md)
passes clean-source functional qualification and all 27 common-clock cases:
Embench 1.045830× and FP32 1.078255× at 100 MHz with fixed 10 ns memory.
Its [raw evidence](docs/evidence/2026-10-19/lsu-a-functional/README.md) is archived;
[physical qualification](docs/evidence/2026-10-20/lsu-a-physical/README.md) now passes at 100 MHz and
101.01 MHz, with 22,162.24152 µm² cell area (1.003674× baseline). The complete
101.01 MHz run yields Embench 0.726601× and FP32 0.700275×: fixed 10 ns memory
is sampled after two cycles at that clock. Neither point reaches both 1.20×
goals. The 100 MHz point is recommended for discussion; the baseline is unchanged
and B remains an independent comparison.

`make profile-fp-bottlenecks JOBS=4` adds read-only FIR/BiCG cycle observations
and checks that observer on/off runs preserve the qualified output and timing.
The [wait analysis](docs/FMA_BOTTLENECK_REVIEW.md) accounts for the removed
instructions and exposed retirement gaps; no RTL optimization is included.
`make profile-lsu-candidates JOBS=4` uses the six already-qualified inputs at
response delays 1/2/4. Its [review](docs/LSU_OPTIMIZATION_REVIEW.md) separates
18/18 historical normal-response passes from the reproduced interface defects, and
compares A/B/C options. The source-locked historical runner rejects newer RTL.
The [interface fixes](docs/LSU_INTERFACE_FIX.md) close the two defects with 48
assertion-enabled cases; rerun with `make check-lsu-interface JOBS=4` and
`python3 scripts/test_lsu_interface.py`. The approved performance/area targets
await independent CPU candidate experiments.

The simulation and generic-synthesis images are separate. For a proxy/private CA:

```bash
make docker-build PROXY_CA=/path/to/combined-ca-bundle.pem
```

The CA is a build secret. `SIM_IMAGE`, `SYN_IMAGE` and `JOBS` are Make overrides;
versions are recorded in [toolchain.lock](toolchain.lock). The simulator build is
incremental. After switching to an incompatible tool image, rebuild it explicitly.

Useful individual commands:

```bash
make sim ELF=build/tests/store_forwarding.elf SIM_ARGS="+dmem-latency=3 +dmem-rand-delay=5"
make coremark ITER=10 OPT=-O3
make embench-run EMBENCH_BENCH=crc32
make embench-run
```

`make coremark` produces development measurements. A fixed iteration count does
not by itself satisfy CoreMark reporting rules. `make embench-run` currently runs
the existing 14-workload subset. The approved general embedded suite contains
all 19 workloads; use `make qualify-embench-fp-dut` for its functional checks.

## Verification and physical scope

The 2026-10-16 bring-up passed 18 directed workloads, 18 corresponding Spike
comparisons, comparator self-tests, 24 memory-delay configurations, lint and
generic synthesis. Evidence and limits are recorded in the session handoff.
These checks do not establish complete RV32IMF or machine-mode conformance.

Fresh ACT4 generation requires a prepared image with Sail 0.13.1 and the pinned
framework's generator dependencies:

```bash
make check-signoff-env ACT_IMAGE=your-prepared-act4-image
make act4-run ACT_IMAGE=your-prepared-act4-image
# Existing regression/archive workflow; requires a clean working tree:
make signoff ACT_IMAGE=your-prepared-act4-image
```

The existing `signoff` target has legacy acceptance thresholds and does not
implement the proposed dual-performance milestone. Its ACT4 set excludes F;
the differential parser does not yet compare trap cause/tval. Full ACT4 and
detailed-route qualification remain open.

The [GitHub workflow](.github/workflows/README.md) runs on pushes to `main` and
pull requests targeting `main`. The [ASAP7 flow](physical/asap7/README.md) is a
separate pinned environment. Its portable post-LSU runner and report controls are
available; the full-core global-route research baseline is qualified. Detailed
routing, workload power and full architectural coverage remain separate work.

## License

Project code uses the [MIT license](LICENSE). Vendored benchmarks and frameworks
retain their own licenses; consult their source trees before redistribution.
