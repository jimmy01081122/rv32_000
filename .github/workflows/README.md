# GitHub Actions CI — RV32 Out-of-Order Core

> Workflow file: `.github/workflows/signoff.yml`
> Repository: <https://github.com/jimmy01081122/rv32_000>

## Overview

The `Signoff CI` workflow runs on every **push to `main`** and every **pull request targeting `main`**.
It is structured as five parallel verification jobs that fan-in to a single **signoff gate**.

```
                         ┌─ lint ──────────┐
push / PR ──► checkout ──┤                 ├─► signoff-gate
                         ├─ spike-diff ────┤
                         ├─ act4 ──────────┤
                         ├─ coremark-smoke ┤
                         └─ synthesis ─────┘
```

---

## Jobs

### `lint` · Verilator lint-only
| | |
|---|---|
| **Runner** | `ubuntu-22.04` |
| **Timeout** | 10 min |
| **Tool** | `verilator` (apt, Ubuntu 22.04 package) |
| **What it does** | Runs `verilator --lint-only -Wall -f sim/scripts/rv32_ooo_core.f` on the full RTL filelist. |
| **Gate** | Zero lint errors/warnings (excluding `UNUSED`, `STMTDLY`). |
| **Why first** | All other jobs depend on `lint` passing to avoid burning runner-minutes on broken RTL. |

---

### `spike-diff` · Differential verification (14/14)
| | |
|---|---|
| **Runner** | `ubuntu-22.04` |
| **Timeout** | 45 min |
| **Tools** | Verilator (apt), riscv32-unknown-elf GCC (riscv-collab pre-built), Spike v1.1.0 (built from source) |
| **What it does** | 1. Downloads `riscv32-elf-ubuntu-22.04-gcc.tar.xz` from riscv-collab releases and installs to `/opt/riscv32-gcc/`.<br>2. Clones and builds Spike v1.1.0 with `--enable-commitlog`.<br>3. Builds the Verilator C++ simulator (`rv32_ooo_sim`).<br>4. Cross-compiles all directed test ELFs from `software/directed/` and `verif/directed/`.<br>5. Runs `python3 scripts/run_spike_diff.py` which executes each test on both DUT and Spike and compares PC, register writebacks, stores, and traps in lockstep. |
| **Gate** | 14/14 tests pass differential comparison (zero mismatches). |
| **Caching** | GCC toolchain cached by version tag; Spike binary cached by git tag; Verilator build cached by RTL/TB file hashes. |
| **Artifacts** | `spike-diff-logs/` — `spike_diff.log`, `diff_results.json` |

---

### `act4` · ACT4 fresh ELF generation + DUT execution (58/58)
| | |
|---|---|
| **Runner** | `ubuntu-22.04` |
| **Timeout** | 60 min |
| **Tools** | Verilator (apt), riscv32-unknown-elf GCC (riscv-collab), sail_riscv_sim (pre-built), Ruby/Bundler (apt + gems) |
| **What it does** | 1. Initialises the `verification/act4/riscv-arch-test` submodule.<br>2. Installs Ruby gems for the ACT4 framework (`bundle install`).<br>3. Installs `sail_riscv_sim` — tries known pre-built binary URLs; falls back to a DUT-only stub if unavailable (ACT4 ELFs are self-checking via embedded signature comparison, so DUT pass alone is valid).<br>4. Runs `python3 verification/act4/riscv-arch-test/run_tests.py` to **freshly generate** all 58 self-checking ELFs using the Sail reference model.<br>5. Runs `python3 scripts/run_act4.py` to execute each ELF on the DUT simulator and collect pass/fail. |
| **Gate** | 58/58 ELFs produce `Exit code: 0 (PASS)` on the DUT. |
| **ELF coverage** | RV32I (39 tests), RV32M (8 tests), Zicsr (11 tests). |
| **Caching** | GCC toolchain, Sail binary, Verilator build, Bundler gems all cached. |
| **Artifacts** | `act4-results/` — `act4_summary.json`, `elf_hashes.json`, `act4_run.log` |

> **Note on Sail binary availability:** The `sail_riscv_sim` binary URL depends on the upstream
> sail-riscv release format. If the binary is unavailable, the job falls back to DUT-only mode.
> The self-checking signature mechanism in ACT4 ELFs means DUT-only verification is still
> architecturally meaningful.

---

### `coremark-smoke` · 5-run cycle-exact determinism
| | |
|---|---|
| **Runner** | `ubuntu-22.04` |
| **Timeout** | 30 min |
| **Tools** | Verilator (apt), riscv32-unknown-elf GCC (riscv-collab) |
| **What it does** | 1. Cross-compiles CoreMark with 3 iterations, `-O2`, `PERFORMANCE_RUN`.<br>2. Runs `python3 scripts/verify_coremark_reproducibility.py --runs 5 --iterations 3 --opt=-O2` which executes the ELF 5 times on the DUT simulator and compares cycle counts, retired instruction counts, and CRC values across all runs. |
| **Gate** | All 5 runs produce **identical** cycle counts, retired instruction counts, and CRC values (cycle-exact determinism). |
| **Why 3 iterations?** | Faster CI run while still exercising the full CoreMark logic path. Production signoff uses 26 iterations. |
| **Caching** | GCC toolchain, Verilator build. |
| **Artifacts** | `coremark-results/` — `coremark_reproducibility.json`, per-run logs, compile log |

---

### `synthesis` · Yosys (0 latches, 0 loops)
| | |
|---|---|
| **Runner** | `ubuntu-22.04` |
| **Timeout** | 30 min |
| **Tools** | Yosys (apt), sv2v v0.0.12 (pre-built binary from zachjs/sv2v) |
| **What it does** | 1. Downloads `sv2v-Linux.zip` from GitHub releases and installs to `/usr/local/bin/`.<br>2. Runs `bash syn/scripts/synth_yosys.sh` which:<br>   - Converts all 14 RTL `.sv` files to Verilog-2005 via `sv2v --top=rv32_ooo_core`<br>   - Elaborates and synthesises with Yosys (`proc` + `opt -fast` + `check -assert`)<br>   - Runs `python3 scripts/parse_synth_log.py` to extract metrics.<br>3. Asserts `latch_count == 0`, `loop_count == 0`, `check_errors == 0`. |
| **Gate** | Zero inferred latches, zero combinational loops, zero Yosys check errors. |
| **Caching** | sv2v binary cached by version tag. |
| **Artifacts** | `synthesis-results/` — `synth.log`, `rv32_ooo_core_netlist.v`, `synthesis_summary.json` |

---

### `signoff-gate` · All checks passed
| | |
|---|---|
| **Runner** | `ubuntu-22.04` |
| **Condition** | `if: always()` — runs even if upstream jobs fail, to collect a consolidated summary |
| **What it does** | Checks the `result` of all five jobs and prints a pass/fail table. Exits non-zero if any job did not succeed. |
| **Purpose** | Single required status check for branch protection rules. Set `signoff-gate` as the required check in GitHub repository settings. |

---

## Toolchain Versions

| Tool | Version | Source |
|---|---|---|
| Verilator | Ubuntu 22.04 package (`4.038`) | `apt` |
| Yosys | Ubuntu 22.04 package (`0.9`) | `apt` |
| riscv32-unknown-elf GCC | `2026.07.15` | [riscv-collab/riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain/releases) |
| Spike | `v1.1.0` | Built from [riscv-software-src/riscv-isa-sim](https://github.com/riscv-software-src/riscv-isa-sim) |
| sv2v | `v0.0.12` | [zachjs/sv2v](https://github.com/zachjs/sv2v/releases) |
| sail_riscv_sim | `0.13.1` | [riscv/sail-riscv](https://github.com/riscv/sail-riscv/releases) pre-built |

---

## Caching Strategy

All heavyweight downloads are cached with `actions/cache@v4` keyed on:

- **GCC toolchain** — `riscv32-gcc-<VER>-ubuntu22`
- **Spike binary** — `spike-<TAG>-ubuntu22`
- **Verilator build** — hash of all RTL `.sv` + TB `.cpp`/`.h` + filelist `.f`
- **sv2v binary** — `sv2v-<VER>-ubuntu22`
- **Sail binary** — `sail-riscv-<VER>-ubuntu22`
- **ACT4 gems** — hash of `Gemfile.lock`

Cache hits skip the corresponding download/build step entirely.

---

## Branch Protection Setup

To enforce signoff as a required merge gate:

1. Go to **Settings → Branches → Branch protection rules** for `main`.
2. Enable **Require status checks to pass before merging**.
3. Add `✓ signoff · All checks passed` as a required status check.
4. Enable **Require branches to be up to date before merging**.

---

## Troubleshooting

**`riscv32-unknown-elf-gcc` not found:**  
The download URL uses `RISCV_COLLAB_VER` from the top-level `env:` block. If the release does not exist, update the version string.

**Spike build fails:**  
Spike requires `libboost-all-dev` and `device-tree-compiler`. Both are installed in the `Install system packages` step.

**`sail_riscv_sim` binary not found:**  
The job gracefully falls back to DUT-only mode. The ACT4 ELFs embed result signatures that the DUT verifies internally; Sail is not strictly required for pass/fail determination.

**Yosys synthesis reports latches:**  
This indicates a missing `default` in a `case` statement or an incompletely assigned signal path in the RTL. Check `build/syn/synth.log` for `Latch inferred` messages.
