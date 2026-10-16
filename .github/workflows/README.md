# GitHub Actions verification workflow

Source: [signoff.yml](signoff.yml). Updated 2026-10-16.

The workflow runs on pushes to `main` and pull requests targeting `main`.
Pushing a maintenance branch alone does not trigger it. Local static checks have
passed; this session has not executed the revised workflow on GitHub.
The job ID and required-check name `signoff-gate` are retained for compatibility.
Passing it means the configured jobs passed, not full ISA or physical qualification.

## Jobs and actual coverage

`lint` runs first. The other four verification jobs depend on it, and the final
gate checks all five results.

| Job | Work performed | Scope/limits |
| --- | --- | --- |
| `lint` | Verilator lint over the shared RTL list | `UNUSED` and `STMTDLY` are excluded |
| `spike-diff` | Compile directed programs and run DUT/Spike trace comparison | Current source set has 18 workloads; trap cause/tval comparison is incomplete |
| `act4` | Fresh framework generation with Sail, then self-checking ELFs on DUT | Expected historical set: I 39, M 8, Zicsr 6, Zifencei 1, Zmmul 4; no F |
| `coremark-smoke` | Five runs of a 3-iteration `-O2` performance binary | Cycle/retirement/CRC reproducibility, not an official-duration performance report |
| `synthesis` | sv2v and generic Yosys synthesis/checks | No physical implementation or timing/power qualification |
| `signoff-gate` | Fail if any prerequisite job did not succeed | Existing automated regression gate |

The default simulator build does not enable `--assert`. The broader verification
and measurement work is tracked in [STATUS.md](../../docs/STATUS.md).
Comparator negative self-tests run through local `make diff-selftest` and the
host `make signoff` pipeline; this GitHub job does not currently invoke them.

## Dependencies and caching

Tools are installed on Ubuntu 22.04 runners. Exact download versions are in the
workflow environment, and the simulator build uses
[build_sim.sh](../../scripts/build_sim.sh), shared with Make.

- Verilator 4.038 and Yosys 0.9 from Ubuntu packages.
- RISC-V GCC release 2026.07.15; Spike v1.1.0; sv2v v0.0.12.
- Sail 0.13.1, Ruby 3.4.10, Bundler 4.0.18 and uv 0.11.33 for ACT4.
- ACT4 framework SHA `74efcaac81f48f437f58868771daf2ed2776d422`.

GCC, Spike, sv2v, Sail and simulator outputs are cached. Simulator keys include
RTL, harness, filelist and shared build script. Sail's key includes `verified-v2`
to avoid reusing earlier invalid cached content. Consult the YAML for exact keys,
timeouts and artifact paths.

Sail is a real prerequisite: missing Sail, failed generation and fewer than 58
generated ELFs fail ACT4. There is no successful stub or fallback to old ELFs.
ACT4 executes the generated tests on the DUT; Spike differential testing is a
separate job, not a second execution stage in `run_act4.py`.

## Local reproduction and troubleshooting

Use the [root quickstart](../../README.md) and
[session handoff](../../docs/SESSION_HANDOFF.md). Locally, ACT4 needs a separately
prepared `ACT_IMAGE`; the default simulation image does not provide Sail or its
generator environment. `make check-signoff-env` checks prerequisites early.

- Missing compiler/Sail: check the pinned release URL, executable path and version;
  dependency changes must be recorded, not substituted with a success stub.
- Spike build dependencies include `libboost-regex-dev`, `libboost-system-dev`
  and `device-tree-compiler`; the former Boost-all requirement was removed.
- Synthesis latches/loops: inspect the source and synthesis log; do not waive a
  failure by relabeling the job or changing report counts.

Branch protection can require the existing `signoff-gate` check. No repository
protection settings are changed by this documentation. The proposed independent
embedded/FP32 performance gates are not yet implemented in this workflow.
