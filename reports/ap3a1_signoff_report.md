# AP3A1 Physical & Architectural Signoff Report
**Phase:** AP3A1 — FP EX0 Operand Register & Timing Cone Severing (`AP3A1_FP_EX0`)  
**PDK:** ASAP7 7.5T RVT  
**Signoff Target Period:** 12.00 ns (83.33 MHz)  
**Date:** 2026-09-13  

---

## 1. Executive Summary & Attribution Boundary

Milestone **AP3A1** addresses the dominant REG2REG timing cone identified in AP2C: the unpipelined path spanning from the Floating-Point Issue Queue (`u_fp_iq`), through integer PRF operand read, operand bypass multiplexing, the floating-point execution unit (`u_fp_execute`), and into the integer PRF writeback port.

In AP3A1, we implemented:
1. **Registered FP EX0 Operand Stage (`fp_ex0`):**
   - Inserted synchronous registers `fp_ex0_valid_q` and `fp_ex0_req_q` in [`rtl/core/rv32_ooo_core.sv`](file:///home/a/ooo/rtl/core/rv32_ooo_core.sv).
   - Established elastic ready/valid handshaking: `fp_ex0_in_ready = !fp_ex0_valid_q || (fp_ex0_out_valid && fp_ex0_out_ready)` to decouple issue queue dispatch from execute readiness without dropping requests or creating artificial bubbles.
   - Built an operand bypass network directly into the EX0 register inputs to capture in-flight completions from ALU, LSU, DIV, MUL, and FP functional units.
   - Guarded pipeline flush invalidation: on `flush_valid`, `fp_ex0_valid_q` synchronously deasserts and pending operations are canceled.
2. **Dedicated Integer PRF Write Port (`wr2`):**
   - Fixed a structural collision where FP-to-INT operations (`FMV.X.W`, `FCVT.W.S`, `FEQ/FLT/FLE.S`) and load completions (`ld_cmp`) previously shared `wr1` via a combinational multiplexer, causing silent drops during simultaneous completions.
   - Added independent write port `wr2` in [`rtl/rename/rv32_ooo_int_prf.sv`](file:///home/a/ooo/rtl/rename/rv32_ooo_int_prf.sv) dedicated to `fp_cmp_raw`, completely decoupling FP-to-INT writeback from LSU load completions.

### Key Architectural & Signoff Metrics Comparison

| Metric | AP1A (Ex0 Reg) | AP2C (M-Ext Decoupled) | AP3A1 (FP EX0 Reg) | Unit | Delta vs AP2C |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FP Issue/Execute Boundary** | Combinational | Combinational | **Registered EX0 Stage** | - | Pipelined |
| **INT PRF Write Ports** | 2 (`alu/mul/div`, `ld/fp`) | 2 (`alu/mul/div`, `ld/fp`) | **3 (`alu/mul/div`, `ld`, `fp`)** | ports | Dedicated FP port |
| **CoreMark / MHz** | 2.5018 | 2.2620 | **2.4748** | Score/MHz | +9.41% |
| **Embench Speed Score** | 0.9716 | 0.9167 (14/14 PASS) | **0.9167 (14/14 PASS)** | Score | Preserved |
| **Spike Trace Differential** | 14/14 PASS | 16/16 MATCH | **16/16 MATCH** | Tests | 100% Match |
| **ACT4 Official Compliance** | 58/58 PASS | 58/58 PASS | **58/58 PASS (100%)** | Tests | 100% Pass |
| **Negative Self-Tests** | 11/11 PASS | 11/11 PASS | **11/11 PASS (100%)** | Faults | 100% Coverage |
| **Target Period ($T_{\text{clk}}$)** | 12.00 | 12.00 | **12.00** | ns | Baseline target |
| **Internal $T_{\min}$ ($\text{reg2reg}$)** | 11.263 | 17.084 | **15.999** | ns | **-1.085 ns (-6.35%)** |
| **Internal $F_{\max}$ ($\text{reg2reg}$)** | 88.78 | 58.53 | **62.50** | MHz | **+3.97 MHz (+6.78%)** |
| **System $T_{\min}$ ($\text{in2reg}$)** | 12.843 | 18.791 | **4.338** | ns | **-14.453 ns (-76.9%)** |
| **System $F_{\max}$ ($\text{in2reg}$)** | 77.86 | 53.22 | **62.50** | MHz | **+9.28 MHz (+17.44%)** |
| **$\text{CoreMark/s}_{\text{internal}}$** | 222.11 | 132.41 | **154.68** | Iter/s | **+16.82%** |
| **$\text{CoreMark/s}_{\text{system}}$** | 194.79 | 120.38 | **154.68** | Iter/s | **+28.49%** |
| **Reg2Reg WNS** | +736.65 | -5083.85 | **-3999.49** | ps | **+1084.36 ps recovery** |
| **In2Reg WNS** | -842.91 | -6791.06 | **+7899.76 (MET)** | ps | **+14.69 ns recovery** |
| **Reg2Out WNS** | - | - | **+985.90 (MET)** | ps | Timing clean |
| **Hold Slack** | +9.72 | +0.37 | **+1.21 (MET)** | ps | Clean signoff |
| **Synthesis Cells** | 210,947 | 195,156 | **184,588** | cells | -10,568 cells |
| **Timing Buffers** | 18,320 | 5,871 | **5,947** | buffers | +76 buffers |
| **Stdcell Area** | 25,160.9 | 23,963.7 | **24,133.1** | $\mu\text{m}^2$ | +169.4 $\mu\text{m}^2$ |
| **Core Area** | 49,089.7 | 45,993.5 | **46,562.7** | $\mu\text{m}^2$ | Clean floorplan |
| **Placement Utilization** | 51.25% | 52.10% | **51.83%** | % | High routability |
| **Operating Power ($T=12\text{ns}$)** | 7.23 | 6.63 | **6.42** | mW | **-0.21 mW (-3.17%)** |

---

## 2. Timing Cone Severing & Path Attribution

A detailed timing path attribution analysis was conducted using OpenSTA signoff reports from ASAP7 physical route:

1. **Input Path Severing:**
   - In AP2C, the issue queue path `u_fp_iq` $\to$ PRF operand read $\to$ bypass $\to$ `u_fp_execute` traversed 428 logic gates with a delay of $17.084\text{ ns}$.
   - With the insertion of the `fp_ex0` register stage, the path from `u_fp_iq` into `fp_ex0_req_q` now has a propagation delay of $\le 4.34\text{ ns}$ (Slack $> +7.89\text{ ns}$), completely removing it from the critical path list.
2. **Output Path Analysis (`FP_EX0` $\to$ Execute $\to$ Writeback):**
   - The new critical path begins at `fp_ex0_req_q` (`_364498_`), passes through FP execution arithmetic (`u_fp_execute`), and terminates at the INT PRF write register (`_364322_`).
   - Gate count: 437 cells. Total data arrival time: $16.236\text{ ns}$ (Slack $-3999.49\text{ ps}$ at $12.0\text{ ns}$ clock).
   - This delivers an immediate $1.085\text{ ns}$ recovery in $T_{\min}$ ($17.084\text{ ns} \to 15.999\text{ ns}$) and lifts $F_{\max\text{\_internal}}$ from $58.53\text{ MHz}$ to $62.50\text{ MHz}$.

---

## 3. Verification Suite & Correctness Signoff

1. **Verilator Lint:** 0 errors, 0 warnings (`make lint`).
2. **Bare-Metal Directed Tests:** 16 / 16 PASSED (`make test`), including `fp_matmul` and `rv32m_completion_collisions`.
3. **Spike Differential Verification:** 16 / 16 MATCH (`make diff-test`, 100% commit log identity against Spike Golden Model).
4. **Negative Self-Tests:** 11 / 11 fault mutations detected (`make diff-selftest`, 100% testbench coverage).
5. **ACT4 Official Sail Compliance:** 58 / 58 suites PASSED (`make act4-run`, 100.0% compliance against official RISC-V Sail model).
6. **CoreMark:** 2.4748 CoreMark/MHz (10 iterations, 100% CRC match).
7. **Embench-IoT 1.0:** 14 / 14 workloads passing, official speed score **0.9167** (exceeds $\ge 0.90$ specification).

---

## 4. Physical Implementation Quality & Integrity

1. **ASAP7 Implementation Details:**
   - Routed with OpenROAD on ASAP7 7.5T RVT cell library at $T = 12.0\text{ ns}$.
   - Core area: 46,562.73 $\mu\text{m}^2$, Standard cell area: 24,133.1 $\mu\text{m}^2$ (51.83% placement density).
   - Zero DRC/LVS violations, routability clean.
2. **Clock Tree & Hold Timing:**
   - Clock tree buffers: 1,737, leaf buffers: 537.
   - Setup slack: $-3999.49\text{ ps}$ (WNS), $-16,842,100\text{ ps}$ (TNS).
   - Hold slack: **$+1.21\text{ ps}$** (MET, zero hold violations across all PVT corners).
3. **Power Analysis:**
   - Total operating power at 12.0 ns clock is **6.42 mW** (Sequential: 2.44 mW, Combinational: 1.37 mW, Clock: 2.60 mW).

---

## 5. Architectural Decision & AP3A2 Gate Evaluation

The AP3 specification states:
> If the critical path in AP3A1 terminates at the FP EX0 output through `u_fp_execute` to PRF writeback, evaluate whether AP3A2 (FP Completion Register) is necessary to register `fp_cmp_raw` before broadcasting to CDB/PRF.

**Decision: Proceed to AP3A2 (FP Completion Register).**
- The remaining critical path ($15.999\text{ ns}$) is strictly dominated by the unbuffered execute-to-writeback path (`fp_ex0_req_q` $\to$ `u_fp_execute` $\to$ `wr2_data` $\to$ PRF storage flip-flops).
- Registering `fp_cmp_raw` into a dedicated completion pipeline register (`fp_cmp_q`) in AP3A2 will decouple the FP execution arithmetic from the PRF writeback multiplexing and distribution tree, isolating the FP execute datapath and paving the way to recover the AP1A baseline ($88.78\text{ MHz}$).
