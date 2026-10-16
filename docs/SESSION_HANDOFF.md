# Session handoff — 2026-10-16

## Source and project state

- Repository: `jimmy01081122/rv32_000`.
- Incoming SHA: `0d79df58e65c2e1034e40f7f586a463fd8602ff1` (`main`).
- Environment/workflow changes are on branch `codex/session-setup`.
- The incoming working tree was clean. This session has not changed RTL, ISA contracts,
  memory layout, acceptance thresholds, or historical signoff artifacts.
- HTTPS clone and a real temporary-branch push/delete succeeded. SSH was blocked by
  system SSH configuration ownership/permissions, before GitHub authentication.

The implementation is a scalar RV32 OoO core targeting RV32IMF + Zicsr, with
one-wide fetch/rename/dispatch/retirement, ROB=16, integer/FP PRFs=48 each,
integer IQ=8, FP IQ=4, and a 16-entry store queue. `LQ_ENTRIES=16` is a
parameter, but the current LSU has no allocated 16-entry load queue: load tags
are zero and external memory transactions use one in-flight record plus a
response buffer. Retirement limits sustained IPC to 1;
concurrent execution does not make it a two-wide superscalar processor.

The newest report is `reports/ap5a_signoff_report.md`, but current
`rtl/lsu/rv32_ooo_lsu.sv` already implements AP5B registered load responses.
Commit `9712245` introduced that RTL and `verification/unit/tb_lsu_ap5b.sv` under
an `arch graph update` title. AP5B has no corresponding report/ledger entry.
The current directed suite contains 18 C workloads; old README/signoff counts
of 14 or 17 do not describe the current source set.

AP5A reports 175.69 MHz **internal** Fmax and 153.18 MHz system Fmax at its 6 ns
baseline. Its REG2OUT setup slack is -528.19 ps; its internal closure must not
be described as closure of all interface paths. These are historical measurements,
not measurements reproduced by this session.

## Development environment

Host: Debian 13, x86_64, Docker 28.4.0, 3 CPUs, about 10 GiB RAM.
EDA tools run inside Ubuntu 22.04 containers:

| Image | Purpose | Pinned tools |
| --- | --- | --- |
| `rv32ooo-sim:g1` | RTL lint, C++ simulation, C compilation, Spike diff, CoreMark/Embench | Verilator 4.038, GCC release 2026.07.15 / GCC 16.1.0, Spike v1.1.0, Python 3.10 |
| `rv32ooo-syn:g1` | SV lowering and generic synthesis | sv2v 0.0.12, Yosys 0.9, Python 3.10 |
| `ACT_IMAGE` (optional) | Fresh Sail-based ACT4 generation and DUT execution | Sim tools plus Sail 0.13.1, mise or uv + Ruby/Bundler; framework manages its dependencies |
| ORFS/ASAP7 (optional) | Physical implementation and STA | Separate pins in `physical/asap7/toolchain.lock` |

The base sim/syn images deliberately do not install ACT4's Ruby/Python environment
or OpenROAD/PDKs. All project-side Python runners use the standard library.

## Reproduction

```bash
cd /workspace/rv32_000
make deps-init
make docker-build                  # initial build; substantial GCC download
make check-env
make lint smoke
make test diff-test diff-selftest coremark-smoke
make synth
python3 scripts/test_workflow_guards.py
```

For a proxy/private CA, append `PROXY_CA=/path/to/combined-ca-bundle.pem` to the
Docker build command. In this cloud environment the tested CA bundle is
`/etc/ssl/certs/ca-certificates.crt`. The optional CA is mounted as a BuildKit
secret only for network steps, with TLS verification enabled.
`BUILDX_CONFIG` defaults to `build/buildx` so read-only home directories do not
break builds; Docker registry configuration and credentials are preserved.

`SIM_IMAGE`, `SYN_IMAGE`, `ACT_IMAGE`, and `JOBS` are Make overrides. Rebuild the
simulator with `make clean sim-build` when switching to an incompatible tool image.
Build outputs are written with the caller's UID/GID. Subsequent `make sim-build`
skips unchanged source; CI and signoff share `scripts/build_sim.sh`.

Dependencies are the tracked gitlink commits, not upstream HEAD:

- Embench: `0466a18e4f6b47e19598d7c6ba72916d54b68f65`.
- ACT4: `74efcaac81f48f437f58868771daf2ed2776d422`.

## Workflow changes

- Restore `.gitmodules`; initialize only the two needed submodules.
- Separate simulation from synthesis packages; replace Boost-all with targeted
  dependencies, and omit unused MPI/Fortran development dependencies and Python installs.
- Keep only Spike's executable at runtime; strip host-tool debug symbols without
  removing compiler functionality or changing pinned EDA versions.
- Lower SV with sv2v before Yosys hierarchy checks; use the shared RTL file list.
- Run master signoff from the host, dispatching to the appropriate image. No
  Docker-inside-tool-container dependency or old `/home/a` PATH overrides.
- Check prerequisites early; preserve existing SHA-keyed evidence and archive
  only after acceptance passes. Missing tool versions are no longer fabricated.
- Require fresh ACT4 generation with the pinned framework and real Sail; use the
  project config directly instead of copying into vendor sources. Missing,
  failed, or undersized test generation cannot report success.
- CI shares the simulator build script, uses the real pinned Sail release,
  removes the successful Sail stub, and avoids duplicate ACT4 generation.

## Current-session evidence

Evidence logs are in ignored `build/session/`; no new formal signoff is claimed.
Final checks on the lean images:

| Check | Result |
| --- | --- |
| `make check-env` | PASS; both pinned vendor revisions match |
| `make lint` | PASS, no Verilator warnings/errors under the configured exclusions |
| Simulator + cross compilation | PASS; all 18 directed C workloads compile |
| `make test` | 18/18 PASS |
| `make diff-test` | 18/18 exact Spike comparisons PASS |
| `make diff-selftest` | 11/11 negative tests PASS (plus positive baseline) |
| Variable memory latency | 24/24 PASS: four memory workloads × base latency 0/3/10 × random extra 0/5 |
| `make coremark-smoke` | PASS; CRC matches; 443,297 benchmark ticks, 477,173 simulation cycles, 305,676 retired; DEVELOPMENT mode only |
| Embench `crc32` | PASS; 5,402,220 benchmark cycles, 5,814,922 simulation cycles |
| `make smoke` | sv2v + Yosys hierarchy PASS |
| `make synth` | PASS; 1,040,353 generic cells, 20,968 DFFs; zero inferred latches, combinational loops, or unelaborated processes |
| `scripts/test_workflow_guards.py` | 8/8 PASS on host Python and container Python 3.10 |
| CI static checks | actionlint 1.7.7 PASS; YAML parses; all 38 embedded shell blocks pass `bash -n` |
| Incremental build | `make -q sim-build` returns 0 after the build |
| Full-signoff preflight | Expected failure for absent Sail; dirty-tree signoff refusal also verified |

The short CoreMark run prints its upstream insufficient-duration warning;
`--mode development` independently checks the known CRCs and successful completion.
It is not an official >=10-second reporting run.

The first working sim image was 3,572,920,007 bytes before stripping host-tool
debug symbols and removing Spike build/link artifacts. The final sim image is
929,625,067 bytes (**73.98% smaller**); synthesis is 324,033,093 bytes.
The two superseded image versions created in this session were removed.

- Sim image ID: `sha256:0d80d39df2f24dc60a77387242f781edc1cc67f53865719981e01b5b5a989d26`.
- Syn image ID: `sha256:b56c1e8635d9baabe4d64ecdd9c63d0685da9aa11075b69bc6bd665ca52bea2b`.
- Main logs: `build/session/final-verification.log`, `synthesis.log`,
  `synthesis-smoke.log`, `memory-embench.log`, `workflow-guards.log`, and `actionlint.log`.
- Machine-readable evidence: `build/tests/diff_results.json`,
  `build/syn/synthesis_summary.json`, `build/session/memory-latency.json`,
  `build/session/embench/results.json`, and `build/session/summary.json`.

This report records bring-up validation before the environment/workflow commit.
Publishing this maintenance branch does not constitute AP5B architectural or physical signoff.

## Outstanding work

1. Complete AP5B validation before architecture optimization: its dedicated SV
   testbench uses timed constructs unsupported by the pinned Verilator 4.038
   execution flow; the default C++ build also omits `--assert`. Use a separately pinned timing-capable simulator or a C++
   harness; do not silently upgrade the canonical simulator.
2. Provision and test a complete ACT4 image for fresh Sail generation. The base
   development images intentionally fail `make check-signoff-env` until then.
   The revised GitHub workflow has not been executed on GitHub in this session.
3. Reconcile old documentation: baseline spec LQ/SQ=4 vs SQ=16 and an unimplemented LQ
   parameter of 16, superscalar wording, old benchmark scores/counts, and normative ISA/profile differences.
4. Review acceptance thresholds: `check_signoff_acceptance.py` still requires
   CoreMark/MHz >=2.50, whereas AP5A reports 2.4748. No threshold was relaxed.
5. Port the physical flow's `/home/a/ooo` and `/home/a/OpenROAD-flow-scripts`
   paths, provision pinned ORFS/ASAP7, and reproduce AP5B PPA independently.
   Generic Yosys synthesis does not establish physical timing or DRC/LVS closure.
6. Close verification coverage gaps: the current 58-test ACT4 set does not cover
   the F extension, and the differential parser currently leaves `trap_cause`
   and `trap_tval` unset. Passing the existing suites is not proof of complete
   RV32IMF/precise-exception compliance.
