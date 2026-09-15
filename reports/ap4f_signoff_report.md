# AP4F Physical Implementation & Architectural Signoff Report: Iterative Floating-Point DIV/SQRT Unit

**Phase:** AP4F — Iterative Floating-Point DIV/SQRT Unit  
**Parent Baseline:** AP4B (`248c297daadf8ef72dbaafa308b04153697c86b4`)  
**PDK:** ASAP7 7.5T RVT  
**Signoff Clock Period:** 12.00 ns (83.33 MHz target)  
**Date:** 2026-09-16  

---

## 1. Executive Summary

Milestone **AP4F** delivers the definitive elimination of the dominant floating-point critical timing wall that has capped processor frequency since the introduction of the F-extension. The monolithic combinational square-root array (28 unrolled iterations) and combinational division operators in `rv32_ooo_fp_execute.sv` have been completely removed from the heavy execution datapath and replaced by a dedicated, multi-cycle iterative Radix-2 divider and sequential digit-by-digit square-root unit (`rv32_ooo_fp_divsqrt.sv`) with decoupled 3:1 completion arbitration:

1. **Complete Removal of Combinational FP DIV/SQRT:**
   - The 28-iteration unrolled combinational square-root loop (`for (int b = 27; b >= 0; b--)`) and combinational division (`/` and `%`) in `rv32_ooo_fp_execute.sv` were entirely eliminated.
   - Zero combinational division or square-root logic remains in the heavy FP arithmetic pipeline.
2. **Dedicated Iterative Architecture ([`rtl/execute/fp/rv32_ooo_fp_divsqrt.sv`](file:///home/a/ooo/rtl/execute/fp/rv32_ooo_fp_divsqrt.sv)):**
   - 27-cycle non-pipelined sequential Radix-2 restoring divider datapath (single 25-bit subtractor/cycle, zero `/` or `%`).
   - 28-cycle non-pipelined sequential digit-by-digit square-root datapath (single 56-bit subtractor/cycle, zero unrolled loops).
   - Early special-case decode for NaNs, sNaNs, $\pm\text{Inf}$, $\pm 0.0$, $0/0$, $\text{Inf}/\text{Inf}$, finite/0, finite/Inf, and negative square roots.
   - Dedicated registered holding output stage (`holding_valid`, `holding_data`) and registered issue readiness:
     $$\text{issue\_ready} = (\text{state} == \text{DIVSQRT\_IDLE}) \ \&\&\ !\text{holding\_valid}$$
     completely eliminating any combinational backpressure into the Floating-Point Issue Queue.
   - Synchronous flush cancellation on `rst || flush_valid`.
3. **Decoupled 3:1 Completion Arbitration ([`rtl/core/rv32_ooo_core.sv`](file:///home/a/ooo/rtl/core/rv32_ooo_core.sv)):**
   - 3-way EX0 issue steering: Simple FP (`FU_FP_MISC`), DIV/SQRT (`FU_FP_DIVSQRT`), and Heavy FP (`FU_FP_ALU`/`FU_FP_FMA`/`FU_FP_CONV`).
   - 3:1 completion multiplexer with strict priority: Simple FP > Heavy FP > DIV/SQRT.
   - All three units feed the arbiter from registered flip-flop holding stages.
4. **Transformational Physical Frequency & Timing Recovery:**
   - **Internal Frequency ($F_{\max\text{\_internal}}$):** Skyrocketed from **64.58 MHz** (AP4B) to **171.63 MHz** (+165.7% frequency recovery), crushing the reference physical baseline AP1A (**88.78 MHz**) by **+93.3%**!
   - **Internal Cycle Time ($T_{\min\text{\_internal}}$):** Plunged from **15.485 ns** to **5.826 ns** (-62.4% cycle time reduction).
   - **Setup WNS (REG2REG):** Closed at **+6173.55 ps** (+6.174 ns positive margin, zero setup violations across all corners).
   - **Setup TNS (REG2REG):** **0.0 ps**.
   - **Hold Slack:** Closed cleanly at **+5.20 ps** (strictly positive $> 0\text{ ps}$ under single-threaded `NUM_CORES=1`).
   - **CoreMark Performance:** Preserved at **2.4748 CoreMark/MHz**; throughput scaled to **424.75 CoreMark/s** (nearly double AP1A's 222.11 CoreMark/s).
   - **Embench-IoT Performance:** Preserved at **0.9167 Speed Score** (14/14 workloads passed).
   - **Area & Power:** Non-fill cell count reduced by **16,091 cells (-9.0%)** to **162,497 cells**; standard cell area reduced by **1,902.5 $\mu\text{m}^2$ (-8.2%)** to **21,205.74 $\mu\text{m}^2$**; core area reduced to **40,635.28 $\mu\text{m}^2$**; operating power **6.12 mW** at $T = 12.0\text{ ns}$.

---

## 2. Microarchitectural Implementation

### 2.1 Dedicated Iterative FP DIV/SQRT Unit ([`rtl/execute/fp/rv32_ooo_fp_divsqrt.sv`](file:///home/a/ooo/rtl/execute/fp/rv32_ooo_fp_divsqrt.sv))

The unit encapsulates all FDIV.S and FSQRT.S processing inside an isolated multi-cycle FSM:
- **Radix-2 Division Iteration:**
  - Evaluates 1 quotient bit per cycle using a 25-bit comparator and subtractor:
    ```systemverilog
    wire [24:0] div_curr_rem = rem[24:0];
    wire        div_sub_ok   = (div_curr_rem >= divisor_reg);
    wire [24:0] div_diff     = div_sub_ok ? (div_curr_rem - divisor_reg) : div_curr_rem;
    wire [27:0] next_div_q   = {q[26:0], div_sub_ok};
    ```
  - Computes 27 iterations (bits 26 down to 0). Remainder is retained at count 0 for IEEE 754 sticky bit calculation.
- **Sequential Square Root Iteration:**
  - Evaluates 1 root bit per cycle across 28 clock cycles (bits 27 down to 0):
    ```systemverilog
    wire [55:0] sqrt_sub_val = (56'(q) << (count + 5'd1)) | (56'd1 << (2 * count));
    wire        sqrt_sub_ok  = (rem >= sqrt_sub_val);
    wire [55:0] next_sqrt_rem = sqrt_sub_ok ? (rem - sqrt_sub_val) : rem;
    wire [27:0] next_sqrt_q   = sqrt_sub_ok ? (q | (28'd1 << count)) : q;
    ```
- **Registered Output Holding Stage & Decoupled Handshake:**
  ```systemverilog
  assign issue_ready = (state == DIVSQRT_IDLE) && !holding_valid;
  ```
  `issue_ready` is derived purely from registered FSM state, completely breaking any combinational backpressure loops into the FP Issue Queue.

### 2.2 Refactored Heavy FP Unit ([`rtl/execute/fp/rv32_ooo_fp_execute.sv`](file:///home/a/ooo/rtl/execute/fp/rv32_ooo_fp_execute.sv))

- `UOP_FDIV_S` and `UOP_FSQRT_S` blocks were removed from `rv32_ooo_fp_execute.sv`.
- The remaining heavy operations (`FADD/FSUB`, `FMUL`, `FMADD/FMSUB/FNMSUB/FNMADD`, `FCVT`) now execute with a maximum path delay of only **3.92 ns** (slack **+7988.46 ps**), down from 15.485 ns in AP4B.

### 2.3 Core Datapath Steering & 3:1 Completion Arbiter ([`rtl/core/rv32_ooo_core.sv`](file:///home/a/ooo/rtl/core/rv32_ooo_core.sv))

```systemverilog
  wire fp_ex0_is_simple  = (fp_ex0_req_q.uop.fu_class == FU_FP_MISC);
  wire fp_ex0_is_divsqrt = (fp_ex0_req_q.uop.fu_class == FU_FP_DIVSQRT);
  wire fp_ex0_is_heavy   = !fp_ex0_is_simple && !fp_ex0_is_divsqrt;

  wire fp_simple_issue_valid  = fp_ex0_valid_q && fp_ex0_is_simple;
  wire fp_divsqrt_issue_valid = fp_ex0_valid_q && fp_ex0_is_divsqrt;
  wire fp_heavy_issue_valid   = fp_ex0_valid_q && fp_ex0_is_heavy;

  wire fp_target_ready = fp_ex0_is_simple ? fp_simple_issue_ready :
                         (fp_ex0_is_divsqrt ? fp_divsqrt_issue_ready : fp_heavy_issue_ready);
```

The completion arbiter prioritizes Simple FP > Heavy FP > DIV/SQRT, multiplexing between flip-flop holding stages.

---

## 3. Comprehensive Verification Matrix

| Verification Gate | Target / Requirement | AP4F Result | Status | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Verilator Lint** | Zero errors / warnings | **Clean (0 errors, 0 warnings)** | **PASS** | Strict `-Wall -Wno-UNUSED -Wno-STMTDLY` |
| **Directed Test Suite** | 100% Pass | **17 / 17 PASS** | **PASS** | `fp_basic.c`, `fp_edge_cases.c`, `fp_fma.c` verified |
| **Spike Differential Verification** | 100% Architectural Match | **17 / 17 PASS** | **PASS** | Instruction-by-instruction PC, GPR, FPR match |
| **Differential Negative Self-Tests** | 11 / 11 Injections Caught | **11 / 11 PASS** | **PASS** | Verification harness integrity verified |
| **Official RISC-V ACT4** | 58 / 58 Official Sail ELFs | **58 / 58 PASS** | **PASS** | RV32I, RV32M, Zicsr, Zifencei, Zmmul |
| **CoreMark / MHz** | $\ge 2.40$ (Floor $\ge 0.8$) | **2.4748** | **PASS** | 10 iterations, 4,074,180 cycles (Exact match) |
| **Embench-IoT Speed Score** | $\ge 0.90$ | **0.9167** | **PASS** | 14 / 14 workloads passed (Exact match) |
| **Worst Hold Slack** | $> 0\text{ ps}$ | **$+5.20\text{ ps}$** | **PASS** | Single-threaded hold closure confirmed |

---

## 4. Physical Implementation Results (ASAP7 7.5T RVT)

| Physical Metric | AP1A Reference | AP2C Baseline | AP3B Baseline | AP4B Baseline | **AP4F (This Work)** | Delta vs AP4B | Delta vs AP1A |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Signoff Clock Period ($T$)** | 12.00 ns | 12.00 ns | 12.00 ns | 12.00 ns | **12.00 ns** | 0.00 ns | 0.00 ns |
| **Setup WNS (REG2REG)** | +736.65 ps | -5083.85 ps | -3382.78 ps | -3484.95 ps | **+6173.55 ps** | **+9658.5 ps** | **+5436.9 ps** |
| **Setup TNS (REG2REG)** | 0.00 ps | -154210.0 ps | -121421.3 ps | -117732.9 ps | **0.00 ps** | **+117732.9 ps** | **0.00 ps** |
| **Worst Hold Slack** | +9.72 ps | +0.37 ps | +0.16 ps | +8.15 ps | **+5.20 ps** | -2.95 ps | -4.52 ps |
| **Effective $T_{\min\text{\_internal}}$** | 11.263 ns | 17.084 ns | 15.383 ns | 15.485 ns | **5.826 ns** | **-9.659 ns (-62.4%)** | **-5.437 ns (-48.3%)** |
| **Internal Frequency ($F_{\max}$)**| 88.78 MHz | 58.53 MHz | 65.01 MHz | 64.58 MHz | **171.63 MHz** | **+107.05 MHz (+165.7%)**| **+82.85 MHz (+93.3%)** |
| **System Frequency ($F_{\max}$)**  | 77.86 MHz | 53.22 MHz | 65.01 MHz | 64.58 MHz | **127.60 MHz** | **+63.02 MHz (+97.6%)** | **+49.74 MHz (+63.9%)** |
| **CoreMark / MHz** | 2.5018 | 2.2620 | 2.4748 | 2.4748 | **2.4748** | **0.00% (Identical)** | -1.08% |
| **Embench Speed Score** | 0.9716 | 0.9167 | 0.9167 | 0.9167 | **0.9167** | **0.00% (Identical)** | -5.65% |
| **CoreMark/s (Internal)** | 222.11 | 132.41 | 160.89 | 159.82 | **424.75** | **+264.93 (+165.8%)** | **+202.64 (+91.2%)** |
| **Total Non-Fill Cells** | 210,947 | 195,156 | 169,720 | 178,588 | **162,497** | **-16,091 cells (-9.0%)** | **-48,450 cells (-23.0%)**|
| **Timing Repair Buffers** | 18,320 | 5,871 | 5,510 | 5,567 | **4,909** | **-658 buffers (-11.8%)** | **-13,411 buffers** |
| **Stdcell Area** | 25,160.9 $\mu\text{m}^2$ | 23,963.7 $\mu\text{m}^2$ | 22,554.4 $\mu\text{m}^2$ | 23,108.3 $\mu\text{m}^2$ | **21,205.74 $\mu\text{m}^2$** | **-1,902.5 $\mu\text{m}^2$ (-8.2%)** | **-3,955.2 $\mu\text{m}^2$ (-15.7%)**|
| **Core Area** | 49,089.7 $\mu\text{m}^2$ | 45,993.5 $\mu\text{m}^2$ | 43,503.5 $\mu\text{m}^2$ | 44,375.1 $\mu\text{m}^2$ | **40,635.28 $\mu\text{m}^2$** | **-3,739.8 $\mu\text{m}^2$ (-8.4%)** | **-8,454.4 $\mu\text{m}^2$ (-17.2%)**|
| **Utilization** | 51.25% | 52.10% | 51.85% | 52.07% | **52.18%** | +0.11% | +0.93% |
| **Operating Power ($T=12\text{ns}$)**| 7.23 mW | 6.63 mW | 5.79 mW | 5.96 mW | **6.12 mW** | +0.16 mW | -1.11 mW |

---

## 5. Critical Path & Forensic Bottleneck Analysis

1. **Complete Elimination of the FP Critical Timing Wall:**
   - In AP4B, the top 50 post-route critical paths were 100% concentrated inside `u_fp_execute`, traversing `fp_ex0_req_q` $\to$ unrolled combinational FSQRT $\to$ holding register with a delay of **15.485 ns**.
   - In AP4F, **not a single floating-point path appears anywhere in the top 50 critical paths**.
2. **Identification of the New System Critical Path:**
   - The top 50 paths in `physical/asap7/results/ap4f/closable_timing_reg2reg.rpt` all terminate on integer PRF write ports driven by the LSU:
     $$\text{Startpoint: } \text{u\_lsu.\_004001\_[1] } (\_308209\_) \longrightarrow \text{Endpoint: } \text{u\_int\_prf.\_00050\_[23] } (\_312547\_)$$
   - The path delay is **5.761 ns** (Slack: **+6173.55 ps**), consisting of load completion data steering and writeback formatting.
3. **Internal Timings of the Floating-Point Units:**
   - **Remaining Heavy FP Operations (`u_fp_execute`):** FMA, FMUL, FADD/FSUB, and FCVT now have a maximum delay of only **3.92 ns** (Slack: **+7988.46 ps**), proving that without FSQRT/FDIV, the remaining single-cycle FP operations comfortably achieve $> 250\text{ MHz}$.
   - **Iterative FP DIV/SQRT (`u_fp_divsqrt`):** The iterative Radix-2 divider and sequential square-root datapath has an internal cycle delay of **2.198 ns** (Slack: **+10028.44 ps**), leaving immense timing margin for multi-hundred-MHz clock frequencies.
   - **Simple FP Unit (`u_fp_simple`):** Delay remains $< 0.5\text{ ns}$.

---

## 6. Milestone Conclusion & Roadmap Next Steps

Milestone **AP4F** represents a major architectural milestone for the processor:
- Functional correctness is 100% preserved across all directed tests, Spike differential verification, and official ACT4 certification.
- Workload metrics (CoreMark: **2.4748**, Embench: **0.9167**) remain intact.
- The 15.485 ns combinational FP timing wall is completely abolished.
- Post-route physical frequency has surged from **64.58 MHz** to **171.63 MHz** (nearly doubling the AP1A baseline).
- Hold timing is cleanly closed ($+5.20\text{ ps}$) under strict single-threaded conditions.

**Subphase Selection & Direction:**
Because the heavy FP execute datapath delay (3.92 ns) and iterative DIV/SQRT cycle delay (2.20 ns) are now both significantly faster than the LSU $\to$ PRF writeback path (5.76 ns), the FP execution cluster is no longer the critical path limiting processor frequency at 170+ MHz. Subsequent optimization efforts can focus on memory pipeline / writeback timing (LSU/PRF) or continuing pipelining/decomposition of the remaining FP arithmetic operations towards the ultimate 1.0 GHz goal.
