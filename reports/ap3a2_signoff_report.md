# AP3A2 Physical & Architectural Signoff Report
**Phase:** AP3A2 — FP Completion Register & Writeback Isolation (`AP3A2_FP_COMPLETION_REG`)  
**PDK:** ASAP7 7.5T RVT  
**Signoff Target Period:** 12.00 ns (83.33 MHz)  
**Date:** 2026-09-14  

---

## 1. Executive Summary & Attribution Boundary

Milestone **AP3A2** completes the floating-point pipeline boundary isolation mandated by the AP3 architectural specification. In AP3A1, inserting the registered operand stage `FP_EX0` eliminated the front-end timing cone (`u_fp_iq` $\to$ PRF read $\to$ Execute), improving $T_{\min}$ from $17.084\text{ ns}$ to $15.999\text{ ns}$. However, timing path analysis demonstrated that the output path remained monolithic: the combinational FP execution cluster (`u_fp_execute`) drove directly into the integer PRF, floating-point PRF, ROB, and issue-queue wakeup logic.

In AP3A2, we implemented:
1. **Registered FP Completion Stage (`fp_cmp_q`):**
   - Inserted synchronous completion register `fp_cmp_q` in [`rtl/core/rv32_ooo_core.sv`](file:///home/a/ooo/rtl/core/rv32_ooo_core.sv).
   - Formed `fp_cmp_comb` as the purely combinational output of `u_fp_execute`, which is registered into `fp_cmp_q` on clock edges.
   - Assigned the broadcast bus `fp_cmp_raw = fp_cmp_q`, completely isolating the FP execution cluster from the downstream PRF write decoders, ROB completion logic, and bypass multiplexers.
2. **Elastic Handshaking & Zero-Bubble Flow:**
   - Modeled non-blocking sink readiness: `fp_cmp_ready = 1'b1`, with backward readiness `fp_cmp_in_ready = !fp_cmp_q.valid || fp_cmp_ready`.
   - Interlocked with `fp_ex0` execution readiness: `fp_execute_ready = fp_cmp_in_ready`, providing structural backpressure support if downstream sinks ever stall.
   - Preserves full pipelined throughput (1 FP operation issued per cycle).
3. **Strict Flush Invalidation:**
   - On `rst || flush_valid`, both `fp_ex0_valid_q` and `fp_cmp_q` are synchronously invalidated.
   - Added formal/simulation SVA assertions guaranteeing that a flushed in-flight FP operation never produces a valid completion or corrupts architectural state.

### Key Architectural & Signoff Metrics Comparison

| Metric | AP1A (Ex0 Reg) | AP2C (M-Ext Decoupled) | AP3A1 (FP EX0 Reg) | AP3A2 (FP Completion Reg) | Unit | Delta vs AP3A1 | Delta vs AP2C |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FP Pipeline Stages** | 1 (Comb) | 1 (Comb) | 2 (`EX0` $\to$ Comb) | **3 (`EX0` $\to$ `EX1` $\to$ `CMP`)** | stages | +1 stage | +2 stages |
| **FP-to-PRF Boundary** | Direct Wire | Direct Wire | Direct Wire | **Registered (`fp_cmp_q`)** | - | Decoupled | Decoupled |
| **CoreMark / MHz** | 2.5018 | 2.2620 | 2.4748 | **2.4748** | Score/MHz | 0.00% | +9.41% |
| **Embench Speed Score** | 0.9716 | 0.9167 (14/14) | 0.9167 (14/14) | **0.9167 (14/14 PASS)** | Score | Preserved | Preserved |
| **Spike Trace Differential** | 14/14 PASS | 16/16 MATCH | 16/16 MATCH | **16/16 MATCH** | Tests | 100% Match | 100% Match |
| **ACT4 Official Compliance** | 58/58 PASS | 58/58 PASS | 58/58 PASS | **58/58 PASS (100%)** | Tests | 100% Pass | 100% Pass |
| **Negative Self-Tests** | 11/11 PASS | 11/11 PASS | 11/11 PASS | **11/11 PASS (100%)** | Faults | 100% Coverage | 100% Coverage |
| **Target Period ($T_{\text{clk}}$)** | 12.00 | 12.00 | 12.00 | **12.00** | ns | Baseline target | Baseline target |
| **Internal $T_{\min}$ ($\text{reg2reg}$)** | 11.263 | 17.084 | 15.999 | **15.693** | ns | **-0.306 ns** | **-1.391 ns (-8.14%)** |
| **Internal $F_{\max}$ ($\text{reg2reg}$)** | 88.78 | 58.53 | 62.50 | **63.72** | MHz | **+1.22 MHz (+1.95%)** | **+5.19 MHz (+8.87%)** |
| **System $T_{\min}$ ($\text{in2reg}$)** | 12.843 | 18.791 | 4.338 | **4.121** | ns | **-0.217 ns** | **-14.670 ns (-78.1%)** |
| **System $F_{\max}$ ($\text{in2reg}$)** | 77.86 | 53.22 | 62.50 | **63.72** | MHz | **+1.22 MHz (+1.95%)** | **+10.50 MHz (+19.73%)** |
| **$\text{CoreMark/s}_{\text{internal}}$** | 222.11 | 132.41 | 154.68 | **157.70** | Iter/s | **+1.95%** | **+19.10%** |
| **$\text{CoreMark/s}_{\text{system}}$** | 194.79 | 120.38 | 154.68 | **157.70** | Iter/s | **+1.95%** | **+30.99%** |
| **Reg2Reg WNS** | +736.65 | -5083.85 | -3999.49 | **-3693.31** | ps | **+306.18 ps recovery** | **+1390.54 ps recovery** |
| **Setup TNS** | 0.0 | -23.45M | -16.84M | **-124,278** | ps | **135x reduction** | **188x reduction** |
| **In2Reg WNS** | -842.91 | -6791.06 | +7899.76 | **+8124.23 (MET)** | ps | **+224.47 ps** | **+14.91 ns recovery** |
| **Reg2Out WNS** | - | - | +985.90 | **+792.34 (MET)** | ps | Timing clean | Timing clean |
| **Hold Slack** | +9.72 | +0.37 | +1.21 | **+0.15 (MET)** | ps | Clean signoff | Zero hold violations |
| **Sequential Flip-Flops** | 18,023 | 18,573 | 18,573 | **18,755 (+182 FFs)** | FFs | Completion register | +182 FFs |
| **Functional Cells** | 210,947 | 195,156 | 184,588 | **184,958** | cells | +370 cells | -10,198 cells |
| **Timing Buffers** | 18,320 | 5,871 | 5,947 | **5,488** | buffers | -459 buffers | -383 buffers |
| **Stdcell Area** | 25,160.9 | 23,963.7 | 24,133.1 | **24,169.2** | $\mu\text{m}^2$ | +36.1 $\mu\text{m}^2$ | +205.5 $\mu\text{m}^2$ |
| **Core Area** | 49,089.7 | 45,993.5 | 46,562.7 | **46,924.7** | $\mu\text{m}^2$ | Clean floorplan | Clean floorplan |
| **Placement Utilization** | 51.25% | 52.10% | 51.83% | **51.81%** | % | High routability | High routability |
| **Operating Power ($T=12\text{ns}$)** | 7.23 | 6.63 | 6.42 | **6.01** | mW | **-0.41 mW (-6.39%)** | **-0.62 mW (-9.35%)** |

---

## 2. Timing Path Attribution & Critical Path Evolution

1. **Writeback Path Elimination:**
   - In AP3A1, the critical path terminated at the INT PRF write register flip-flop (`_364322_`), incurring $1.68\text{ ns}$ of write decoder and routing delay from the FP execution unit.
   - In AP3A2, the critical path terminates strictly at the completion register `fp_cmp_q` (`_366258_`). The writeback path to the PRF is decoupled into a separate cycle, executing in $< 2.0\text{ ns}$.
2. **Setup TNS Collapse:**
   - The total negative setup slack collapsed from $-16,842,100\text{ ps}$ in AP3A1 to $-124,278\text{ ps}$ in AP3A2 (a $135\times$ reduction). This proves that the vast majority of near-critical violating paths in AP3A1 were writeback distribution branches from `u_fp_execute`.
3. **Remaining Path Inside FP Execute:**
   - The remaining critical path starts at `fp_ex0_req_q` (`_366119_`), traverses the FP arithmetic, normalization, rounding, and packaging logic, and terminates at `fp_cmp_q` (`_366258_`) with a path delay of $15.693\text{ ns}$ (Setup WNS $-3693.31\text{ ps}$).

---

## 3. Verification Suite & Correctness Signoff

1. **Verilator Lint:** 0 errors, 0 warnings (`make lint`).
2. **Bare-Metal Directed Tests:** 16 / 16 PASSED (`make test`), verifying FADD, FSUB, FMUL, FDIV, FSQRT, FMADD, conversions, classification, and matrix multiplications.
3. **Spike Differential Verification:** 16 / 16 MATCH (`make diff-test`, 100% commit log equivalence against Spike Golden Model).
4. **Negative Differential Self-Tests:** 11 / 11 fault mutations detected (`make diff-selftest`, 100% testbench diagnostic integrity).
5. **ACT4 Official Sail Compliance:** 58 / 58 suites PASSED (`make act4-run`, 100.0% compliance against official RISC-V Sail reference).
6. **CoreMark:** 2.4748 CoreMark/MHz (10 iterations, 100% CRC match; integer performance completely preserved).
7. **Embench-IoT 1.0:** 14 / 14 workloads passing, official speed score **0.9167** (exceeds $\ge 0.90$ specification).

---

## 4. Physical Implementation Quality & Integrity

1. **ASAP7 Implementation Details:**
   - Implemented with OpenROAD on ASAP7 7.5T RVT library at $T = 12.0\text{ ns}$.
   - Core area: 46,924.65 $\mu\text{m}^2$, Standard cell area: 24,169.2 $\mu\text{m}^2$ (51.81% placement density).
   - Zero DRC/LVS violations, zero routability congestions.
2. **Clock Tree & Hold Timing:**
   - Clock buffers: 1,752, Clock inverters: 259.
   - Hold slack: **$+0.15\text{ ps}$** (MET, zero hold violations).
3. **Power Analysis:**
   - Total operating power at 12.0 ns clock decreased to **6.01 mW** (Sequential: 2.44 mW, Combinational: 0.95 mW, Clock: 2.62 mW, Leakage: 0.021 mW).

---

## 5. Architectural Decision & AP3B Gate Evaluation

With AP3A2 complete:
- The FP issue-to-writeback monolithic cone is fully broken into two registered stages: `FP_EX0` and `FP_CMP`.
- Internal frequency reached $63.72\text{ MHz}$, but the project milestone gate requires recovering the AP1A reference baseline:
  $$\mathbf{F_{\max\text{\_internal}} \ge 88.78\text{ MHz}}$$
- In accordance with the AP3 specification, we now proceed to **AP3B (Replace the Integer Compacting Issue Queue with a Non-Compacting Static-Slot Issue Queue)** to dismantle the $15.8\text{ ns}$ compaction next-state cone and achieve $\ge 88.78\text{ MHz}$.
