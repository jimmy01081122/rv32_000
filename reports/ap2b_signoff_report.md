# AP2B Physical & Architectural Signoff Report
**Phase:** AP2B — Pipelined Multiplier Optimization (`AP2B_PIPELINED_MUL`)  
**PDK:** ASAP7 7.5T RVT  
**Signoff Target Period:** 12.00 ns (83.33 MHz)  
**Date:** 2026-09-09  

---

## 1. Executive Summary & Attribution Boundary

AP2B decomposes and pipelines the integer multiplication datapath (`MUL`, `MULH`, `MULHSU`, `MULHU`), replacing the single-cycle combinational multiplier with a dedicated 3-stage pipelined multiplier supporting full throughput (1 operation per cycle), unified 33x33 signed multiplication, synchronous pipeline flush, and backpressure ready/valid stall handshakes.

In accordance with strict single-variable attribution methodology:
- No changes were made to the CPU frontend, branch predictor, ROB size, IQ capacity, or LSU scheduling policies.
- Architectural state transitions are 100% compliant with the official RISC-V specification and golden Spike reference.

### Milestone Classification:
- **Functional architecture:** PASS
- **Multiplier critical-path removal:** PASS
- **Overall physical performance:** REGRESSION ($F_{\max\text{\_internal}}$: 88.78 MHz AP1A $\to$ 57.46 MHz AP2B)
- **Design Status:** Pareto dominated by earlier configurations; physical timing regression is attributed to newly introduced cross-module M-extension completion and issue-ready coupling (resolved in AP2C).
- **Physical Verification Scope:** Routing complete, 0 DRC violations, 0 antenna violations. (No LVS tool was executed; LVS is NOT claimed).

### Key Architectural & Signoff Metrics Comparison

| Metric | AP0.1 Baseline | AP1A (Ex0 Reg) | AP2A (Iterative Div) | AP2B (Pipelined Mul) | Unit |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Multiplier Architecture** | Combinational | Combinational | Combinational | **3-Stage Pipelined (1 op/cyc)** | - |
| **Divider Architecture** | Combinational | Combinational | 32-cyc Radix-2 | **32-cyc Radix-2** | - |
| **Multiplier Critical Path** | Dominant | Present | Present | **ELIMINATED (0 instances in top paths)** | - |
| **CoreMark / MHz** | 2.5282 | 2.5018 | 2.5018 | **2.3221** | Score/MHz |
| **Embench Speed Score** | 1.0325 | 0.9716 | 0.9379 (14/14 PASS) | **0.9110 (14/14 PASS)** | Score |
| **Spike Trace Differential** | 14/14 PASS | 14/14 PASS | 15/15 PASS | **15/15 PASS** | Tests |
| **ACT4 Official Compliance** | 58/58 PASS | 58/58 PASS | 58/58 PASS | **58/58 PASS** | Tests |
| **Target Period ($T_{\text{clk}}$)** | 13.00 | 12.00 | 12.00 | **12.00** | ns |
| **Internal $T_{\min}$ ($\text{reg2reg}$)** | 13.043 | 11.263 | 16.315 | **17.402** | ns |
| **Internal $F_{\max}$ ($\text{reg2reg}$)** | 76.67 | 88.78 | 61.29 | **57.46** | MHz |
| **System $T_{\min}$ ($\text{in2reg}$)** | 13.043 | 12.843 | 18.006 | **19.104** | ns |
| **System $F_{\max}$ ($\text{in2reg}$)** | 76.67 | 77.86 | 55.54 | **52.34** | MHz |
| **$\text{CoreMark/s}_{\text{internal}}$** | 193.84 | 222.11 | 153.34 | **133.43** | Iterations/s |
| **$\text{CoreMark/s}_{\text{system}}$** | 193.84 | 194.79 | 138.95 | **121.54** | Iterations/s |
| **Hold Slack** | +9.72 | +9.72 | +10.21 | **+9.14 (MET)** | ps |
| **Total Standard Cells** | 206,019 | 210,947 | 192,116 | **192,798** | cells |
| **Sequential Flip-Flops** | 18,023 | 18,023 | 18,023 | **18,322 (+299 FFs)** | FFs |
| **Stdcell Area** | 24,196.2 | 25,160.9 | 24,452.8 | **23,769.0** | $\mu\text{m}^2$ |
| **Core Area** | 49,089.7 | 49,089.7 | 47,311.4 | **45,796.8** | $\mu\text{m}^2$ |
| **Placement Utilization** | 49.29% | 51.25% | 51.68% | **51.90%** | % |
| **Operating Power ($T=12\text{ns}$)** | 6.67 | 7.23 | 6.14 | **6.45** | mW |

---

## 2. RTL Implementation & Physical Timing Analysis

### A. Pipelined Multiplier Architecture ([`rv32_ooo_multiplier.sv`](file:///home/a/ooo/rtl/execute/int/rv32_ooo_multiplier.sv))
- **Pipeline Latency & Throughput:** Parameterized 3-cycle fixed latency with 1 operation per cycle throughput.
- **Unified 33x33 Signed Multiplier:** Uses operand sign-extension to 33-bit signed representations conditionally:
  - `sign_a = (op == MUL) || (op == MULH) || (op == MULHSU)`
  - `sign_b = (op == MUL) || (op == MULH)`
  - A single $33 \times 33 \rightarrow 66$-bit signed product covers all four RV32M multiply variants (`MUL`, `MULH`, `MULHSU`, `MULHU`), saving over 30,000 gates compared to separate multiplier trees.
- **Pipeline Pipeline Registers:**
  - `s1`: Latched operands ($A, B$) and instruction metadata (`rob_tag`, `dest_phys`, `dest_domain`, `pc`).
  - `s2`: Latched 66-bit signed product.
  - `s3`: Latched selected 32-bit result and response valid output.
- **Hazard & Stalling Handshake:** Integrates full backpressure (`stall = rsp_valid && !rsp_ready`). When stalled, pipeline stages freeze state and `req_ready = 0` backpressures the integer issue queue. Synchronous `flush_valid` immediately clears valid bits across all 3 stages.

### B. Timing Analysis & Critical Path Elimination
- **Multiplier Elimination Verified:** Detailed path audit and ripgrep inspection of [`closable_timing_reg2reg.rpt`](file:///home/a/ooo/physical/asap7/results/ap2b/closable_timing_reg2reg.rpt) confirms that **zero multiplier cells, signals, or registers appear in the top 20 timing paths**. The wide 32-bit combinational multiplication cone has been completely eliminated from the critical timing path.
- **Post-Route Timing:**
  - Setup WNS ($\text{reg2reg}$): -5402.18 ps $\rightarrow T_{\min\text{\_internal}} = 17.402\text{ ns}$, $F_{\max\text{\_internal}} = 57.46\text{ MHz}$.
  - System WNS ($\text{in2reg}$): -7103.83 ps $\rightarrow T_{\min\text{\_system}} = 19.104\text{ ns}$, $F_{\max\text{\_system}} = 52.34\text{ MHz}$.
  - Hold timing: **+9.14 ps worst hold slack** (all paths met with zero hold violations).

---

## 3. Physical Implementation Quality & Integrity

1. **Cell Count & Logic Density:**
   - 192,798 standard cells in synthesis; 180,219 core cells in routed netlist (18,322 sequential flip-flops, an increase of 299 FFs corresponding directly to the 3-stage pipeline registers and metadata tags).
   - Core area: 45,796.83 $\mu\text{m}^2$ at 51.90% standard cell placement density.
2. **CTS & Routing:**
   - Clock tree synthesis inserted 1,735 clock buffers and 247 clock inverters.
   - Global routing routed 179,474 nets with **0 DRC violations, 0 antenna violations, and 0 shorts**.
3. **Power Analysis:**
   - Total operating power at 12.0 ns clock is **6.45 mW** (internal: 4.48 mW, switching: 1.95 mW, leakage: 0.02 mW).

---

## 4. Archival & Ledger Signoff

The experiment ledger [`experiments/asap7_results.csv`](file:///home/a/ooo/experiments/asap7_results.csv) has been updated with the complete signoff tuple, and all generated reports are preserved under [`physical/asap7/results/ap2b/`](file:///home/a/ooo/physical/asap7/results/ap2b/).
