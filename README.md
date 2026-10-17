# RV32 OoO CPU research project

A scalar, single-retirement-width RISC-V core targeting RV32IMF + Zicsr,
developed with SystemVerilog and open-source simulation and ASIC design tools.
The execution environment is bare metal. This is an architecture and PPA research
project; tape-out is outside the agreed scope.

General embedded performance and single-precision floating-point performance
are equally important project objectives. Workload qualification and a fresh
AP5B baseline precede the next architecture optimization.
The FP32 workload direction balances control/DSP and matrix/ML kernels;
the [candidate set and scoring proposal](docs/FP32_BALANCED_PROPOSAL.md) await qualification.

## Start here

| Document | Purpose |
| --- | --- |
| [Project plan](PLAN.md) | Agreed scope, decision process and next milestones |
| [Current status](docs/STATUS.md) | Measured checks, implementation drift and open verification gaps |
| [Architecture](architecture_spec.md) | Current implementation inventory and architectural requirements |
| [Micro-operations](uop_spec.md) | Implemented packet types and their limitations |
| [Workload proposal](docs/WORKLOADS.md) | Candidate benchmark sets and numerical targets awaiting qualification |
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

The current RTL contains AP5B registered load responses. Its physical performance
has not been re-established in this session. Archived AP5A MHz, area, power and
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
`make qualify-embench-fp-reference`. The 19-workload reference probe now passes;
the [DUT qualification status](docs/PROGRESS_REVIEW.md) remains open.

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
the existing 14-workload subset, not the proposed full 19-workload set.

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
physical qualification remain open.

The [GitHub workflow](.github/workflows/README.md) runs on pushes to `main` and
pull requests targeting `main`. The [ASAP7 flow](physical/asap7/README.md) is a
separate environment that still needs porting and requalification.

## License

Project code uses the [MIT license](LICENSE). Vendored benchmarks and frameworks
retain their own licenses; consult their source trees before redistribution.
