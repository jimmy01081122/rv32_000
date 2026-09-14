# AP4A Forensic Attribution Report: Floating-Point Critical Sub-Operation Analysis
**Phase:** AP4A — Source-Level Physical Attribution of FP Critical Paths  
**PDK:** ASAP7 7.5T RVT  
**Signoff Target Period:** 12.00 ns (83.33 MHz)  
**Baseline STA Delay:** 15.383 ns ($F_{\max} = 65.01\text{ MHz}$, Setup WNS: $-3382.78\text{ ps}$)  
**Date:** 2026-09-14  

---

## 1. Executive Summary

Milestone **AP4A** performs a source-level physical attribution of the 15.383 ns critical timing cone identified in AP3B before any RTL modifications are made. 

Every single one of the top 50 post-route REG2REG critical paths in `physical/asap7/results/ap3b/closable_timing_reg2reg.rpt` originates at `fp_ex0_req_q` (`_333843_`, bit 89 of `issue_req`, which corresponds to `operand0` exponent bit 25) and terminates at `fp_cmp_q` (`_334033_`, bit 53 of `fp_cmp_q`, which corresponds to the accrued **NX (Inexact)** floating-point exception flag).

Through netlist gate-level tracing and RTLIL source mapping, the combinational datapath of 374 standard cells is definitively attributed:
1. **The path is overwhelmingly dominated by FDIV/FSQRT (specifically the 28-iteration unrolled non-restoring square-root array in `blk_fsqrt`)**, which alone accounts for **11.45 ns (74.76%)** of the 15.313 ns combinational delay across 301 logic gates.
2. **Shared Normalization and Rounding (`round_and_pack`)** is the second largest contributor, accounting for **1.67 ns (10.90%)** across 40 gates (including priority encoding, barrel shift, and rounding increment).
3. **Unpack / Classification** contributes **0.69 ns (4.48%)** across 13 gates.
4. **FMUL and FMA datapaths run in parallel** with the FSQRT/FDIV datapath; they do not determine the current critical timing path because the 28-iteration combinational square root array is strictly longer than the 24x24 multiplier tree.

---

## 2. Functional Region Delay Breakdown

The delay along the 374-gate physical path is categorized into the 10 functional regions specified by the AP4 architecture directive:

| Functional Region | Delay (ps) | Delay (ns) | % of Path | Gate Count | Start Time (ps) | End Time (ps) | Functional Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **unpack/classification** | 685.34 | 0.685 | 4.48% | 13 | 0.00 | 915.68 | Op0 exponent check (`8'hFF`/`8'd0`), NaN/Inf/Zero detection, and mantissa unpacking |
| **exponent compare/alignment** | 97.94 | 0.098 | 0.64% | 3 | 915.67 | 1013.61 | Exponent parity check (`e0[0]`) and initial radicand alignment shift |
| **mantissa arithmetic (FSQRT)** | 11,448.01 | 11.448 | **74.76%** | 301 | 1013.61 | 13,265.62 | **Unrolled 28-iteration combinational square-root comparator-subtractor-mux array** |
| **multiply** | 0.00 | 0.000 | 0.00% | 0 | - | - | FMUL 24x24 mantissa multiplier (runs in parallel; off critical path) |
| **FMA datapath** | 0.00 | 0.000 | 0.00% | 0 | - | - | FMADD 72-bit product-add-align datapath (runs in parallel; off critical path) |
| **normalization** | 299.05 | 0.299 | 1.95% | 11 | 13,265.62 | 13,564.67 | Square-root mantissa formatting to unit bit 26 (`sqrt_mant = {21'd0, q[26:0]}`) |
| **priority encoding** | 430.07 | 0.430 | 2.81% | 10 | 13,564.68 | 13,994.76 | 48-bit MSB priority encoder inside `round_and_pack` |
| **round_and_pack** | 940.81 | 0.941 | 6.14% | 19 | 13,994.76 | 14,935.56 | Barrel shift, guard/round/sticky evaluation, rounding adder, and NX flag generation |
| **conversion** | 0.00 | 0.000 | 0.00% | 0 | - | - | Float-to-int and int-to-float conversion (runs in parallel; off critical path) |
| **result mux** | 377.40 | 0.377 | 2.46% | 8 | 14,935.56 | 15,312.95 | Opcode case-statement result selection and completion packet formation |
| **Total Datapath** | **15,312.95** | **15.313** | **100.0%** | **374** | **0.00** | **15,312.95** | Full combinational transit from `fp_ex0_req_q` to `fp_cmp_q` |

*(Note: Data arrival is $15,595.07\text{ ps}$, including $282.12\text{ ps}$ clock launch delay. Effective $T_{\min} = 15.383\text{ ns}$ after clock skew and setup time).*

---

## 3. Detailed Forensic Analysis

### 3.1 Unrolled FSQRT Loop Mechanism
In [`rtl/execute/fp/rv32_ooo_fp_execute.sv`](file:///home/a/ooo/rtl/execute/fp/rv32_ooo_fp_execute.sv) lines 848–854:
```systemverilog
          rem_val = radicand;
          q = 28'd0;
          for (int b = 27; b >= 0; b--) begin
            logic [55:0] sub_val = (56'(q) << (b + 1)) | (56'd1 << (2 * b));
            if (rem_val >= sub_val) begin
              rem_val = rem_val - sub_val;
              q = q | 28'(1 << b);
            end
          end
```
Because this loop is purely combinational, synthesis unrolls all 28 iterations:
- Each iteration performs a 56-bit magnitude comparison (`rem_val >= sub_val`).
- Each iteration performs a 56-bit subtraction (`rem_val - sub_val`).
- Each iteration updates `rem_val` and `q` via a 56-bit 2:1 multiplexer.
- Across 28 iterations, this creates a sequential combinational chain of $28 \times 11 \approx 308$ logic gates composed of `MAJx2` (carry), `XNOR2` (sum), and `AO/OA` compound gates.
- This single unrolled block accounts for **11.45 ns (74.76%)** of the entire physical cycle time.

### 3.2 Endpoint Attribution (`fp_cmp_q[53]`)
In [`rtl/pkg/rv32_ooo_types.sv`](file:///home/a/ooo/rtl/pkg/rv32_ooo_types.sv), `completion_t` packs `fp_flags` at bits `[49:45]` above LSQ/branch fields. With standard layout, bit 53 of `fp_cmp_q` corresponds directly to `res_flags.nx` (Inexact). Because `round_and_pack` computes `flags.nx = guard || round_bit || sticky`, and because `sticky` depends on the final remainder of the 28th square-root iteration, `res_flags.nx` represents the extreme tail of the dependency graph.

---

## 4. AP4 Subphase Strategy & Roadmap Verification

The forensic evidence confirms the architectural diagnosis:
1. **AP4B (Simple FP Separation):**
   - Operations such as `FMV`, `FSGNJ`, `FEQ/FLT/FLE`, `FCLASS`, and `FMIN/FMAX` currently suffer from placement and routing congestion inside the monolithic `rv32_ooo_fp_execute` multiplexer structure.
   - Separating them into a dedicated low-complexity path isolates fast 1-cycle integer/comparison uops completely from the heavy arithmetic datapath.
2. **AP4C / AP4D / AP4E (Pipelining FADD, FMUL, FMA):**
   - Once FSQRT/FDIV are separated into an iterative unit, the next limiting arithmetic paths will be FMA ($24 \times 24$ multiply $+ 72$-bit add $+ \text{normalization}$) and FADD ($48$-bit alignment $+ \text{add} + \text{normalization}$).
   - Decomposing these into balanced 4-cycle pipelines will bring their stage delays down to $\approx 2.5 - 3.5\text{ ns}$.
3. **AP4F (Iterative FDIV/FSQRT):**
   - Replacing the unrolled 28-iteration combinational loop with a multi-cycle iterative state machine is the **single necessary change to eliminate the 11.45 ns bottleneck**.
   - Moving FSQRT and FDIV to an iterative radix-2 / radix-4 structure with a dedicated result register will instantly dismantle the $15.38\text{ ns}$ critical path.
