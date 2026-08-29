# AP0 ASAP7 Timing Constraint Documentation

## 1. Clock Definition
- **Clock Name:** `core_clk`
- **Clock Port:** `clk`
- **Target Period:** `1.000 ns` (`1000.0 ps`) = **1.0 GHz**
- **Waveform:** 50% duty cycle (`[0.0, 500.0] ps`)

## 2. Clock Uncertainty & Slew
- **Setup Uncertainty:** `50.0 ps` (5.0% of clock period budget for clock jitter, PLL phase noise, and post-CTS skew margin).
- **Hold Uncertainty:** `25.0 ps` (2.5% of clock period budget for fast path hold safety).
- **Clock Input Transition:** `20.0 ps` (standard steep input slew for high-speed clock buffer).

## 3. Top-Level Port Audit & I/O Delay Budget
The top-level module `rv32_ooo_core` exposes three interface groups:

| Port Name | Direction | Bit Width | Description | Delay Constraint | Transition / Load |
|---|---|---|---|---|---|
| `clk` | Input | 1 | Master core clock | Clock source | 20 ps slew |
| `rst` | Input | 1 | Synchronous active-high reset | `200 ps` input delay | 20 ps slew |
| `imem_req_valid` | Output | 1 | Instruction fetch request valid | `200 ps` output delay | 2.0 fF load |
| `imem_req_addr` | Output | 32 | Instruction fetch request address | `200 ps` output delay | 2.0 fF load |
| `imem_req_ready` | Input | 1 | Instruction memory ready | `200 ps` input delay | 20 ps slew |
| `imem_rsp_valid` | Input | 1 | Instruction response valid | `200 ps` input delay | 20 ps slew |
| `imem_rsp_rdata` | Input | 32 | Instruction response data | `200 ps` input delay | 20 ps slew |
| `imem_rsp_error` | Input | 1 | Instruction fetch bus error | `200 ps` input delay | 20 ps slew |
| `imem_rsp_ready` | Output | 1 | Core ready for instruction | `200 ps` output delay | 2.0 fF load |
| `dmem_req_valid` | Output | 1 | Data memory request valid | `200 ps` output delay | 2.0 fF load |
| `dmem_req_addr` | Output | 32 | Data memory address | `200 ps` output delay | 2.0 fF load |
| `dmem_req_wdata` | Output | 32 | Data memory write data | `200 ps` output delay | 2.0 fF load |
| `dmem_req_byte_en` | Output | 4 | Data memory byte enable mask | `200 ps` output delay | 2.0 fF load |
| `dmem_req_wen` | Output | 1 | Data memory write enable | `200 ps` output delay | 2.0 fF load |
| `dmem_req_ready` | Input | 1 | Data memory ready | `200 ps` input delay | 20 ps slew |
| `dmem_rsp_valid` | Input | 1 | Data memory response valid | `200 ps` input delay | 20 ps slew |
| `dmem_rsp_rdata` | Input | 32 | Data memory response data | `200 ps` input delay | 20 ps slew |
| `dmem_rsp_error` | Input | 1 | Data memory bus error | `200 ps` input delay | 20 ps slew |
| `dmem_rsp_ready` | Output | 1 | Core ready for data response | `200 ps` output delay | 2.0 fF load |
| `commit_trace.*` | Output | Struct | Architectural commit trace | `200 ps` output delay | 2.0 fF load |

## 4. Rationales & Engineering Assumptions
- **I/O Budget (20% / 200 ps):** In an ASIC SoC integration at 1 GHz, on-chip SRAM macros and interconnect fabric allocate ~20% of the cycle for external setup and board/bus propagation.
- **Load Capacitance (2.0 fF):** Standard load corresponding to ~2-3 equivalent input inverter pins in ASAP7 7nm FinFET.
- **Path Groups:** Configured `reg2reg`, `in2reg`, `reg2out`, and `in2out` path groups to ensure OpenSTA diagnostic reports separate core internal register-to-register critical paths from I/O boundaries.
