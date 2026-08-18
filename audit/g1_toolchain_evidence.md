# G1 Toolchain Freeze & Simulation Platform Evidence

**Date:** 2026-08-15  
**Milestone:** G1 (Toolchain Freeze & Container Environment) + G2 Simulation Foundation  
**Environment:** Dockerized EDA Toolchain  

---

## 1. Container Images

| Container Image | Tag | Base Image | Size | Purpose |
|---|---|---|---|---|
| `rv32ooo-sim` | `g1` | `ubuntu:22.04` | 1.64 GB | RTL simulation, linting, Verilator elaboration, Spike differential testing, bare-metal cross-compilation |
| `rv32ooo-syn` | `g1` | `ubuntu:22.04` | 343 MB | Yosys 0.9 RTL synthesis, Nangate45 quick sweep, SKY130HD physical design baseline |

---

## 2. Pinned Tool Versions (`toolchain.lock`)

```text
Tool               Version / Tag                   Build Source / Distribution
-----------------------------------------------------------------------------------------
Verilator          4.038 (v4.036-114-g0cd4a57ad)   Ubuntu 22.04 LTS native package (4.038-1)
Yosys              0.9 (git sha1 1979e0b)          Ubuntu 22.04 LTS native package (0.9-2)
Spike              v1.1.0                          Built from source (riscv-isa-sim v1.1.0)
RISC-V GCC         16.1.0 (release 2026.07.15)     Prebuilt (riscv-collab/riscv-gnu-toolchain)
Python             3.10.12                         Ubuntu 22.04 LTS system
pyelftools         0.31                            PyPI package
pyyaml             6.0.2                           PyPI package
tabulate           0.9.0                           PyPI package
rich               13.9.4                          PyPI package
```

---

## 3. Makefile Docker-Driven Interface

All EDA and verification commands execute inside isolated Docker containers:

- `make docker-build` — Builds both `rv32ooo-sim:g1` and `rv32ooo-syn:g1`
- `make check-tools` — Verifies all simulation toolchain binaries inside the container
- `make check-syn-tools` — Verifies synthesis toolchain binaries inside the container
- `make lint` — Runs `verilator --lint-only -Wall` on top-level core RTL (`rv32_ooo_core`)
- `make elab` — Elaborates Verilator testbench model (`build/verilator_elab/`)
- `make compile-tests` — Cross-compiles bare-metal C programs with `crt0.S` and `link.ld`
- `make sim-build` — Builds the C++ Verilator simulation executable (`build/sim/rv32_ooo_sim`)
- `make sim ELF=<path>` — Runs cycle-accurate simulation with 1MB RAM model, MMIO, and watchdog timeout

---

## 4. Verification Evidence & Test Results

### 4.1 Toolchain Version Check (`make check-tools`)
```text
=== Simulation container tool versions ===
--- Verilator ---
Verilator 4.038 2020-07-11 rev v4.036-114-g0cd4a57ad
--- Yosys ---
Yosys 0.9 (git sha1 1979e0b)
--- Spike ---
Spike RISC-V ISA Simulator 1.1.0
--- RISC-V GCC ---
riscv32-unknown-elf-gcc (g6afcc4f6d) 16.1.0
--- Python ---
Python 3.10.12
--- pyelftools ---
0.31
```

### 4.2 Verilator Lint (`make lint`)
- **Status:** PASS (0 errors, 0 warnings)
- Clean connectivity on all top-level and sub-module ports.

### 4.3 Bare-Metal Test Compilation (`make compile-tests`)
- **Artifact:** `build/tests/hello.elf`
- **Linker Base:** `0x80000000` (1MB RAM)
- Disassembly verified with proper entry initialization sequence and `SIM_EXIT` write.

### 4.4 C++ Simulation Harness Execution (`make sim`)
- **Memory Model:** 1MB RAM (`SimMemory`), ELF32 segment loader, MMIO (`SIM_PUTC` `0x10000000`, `SIM_EXIT` `0x10000004`).
- **Deadlock Guard:** 100,000-cycle no-retire watchdog with formatted exit summary.
- **Trace Support:** Optional VCD wave generation (`+vcd=...`) and retirement trace logging.

---

## 5. Milestone Status

- **G0 (Architecture Specification):** FROZEN
- **G1 (Toolchain Freeze & Docker Environment):** **COMPLETED & VERIFIED**
- **G2 (Simulation Platform Foundation):** **OPERATIONAL**
