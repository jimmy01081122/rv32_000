// fp_fma.c — Directed bare-metal test for RV32F FMA, Rounding Modes, Special Values, and Accrued Exception Flags
#include "sim_mmio.h"

#define READ_FCSR(val) \
    __asm__ volatile ("frcsr %0" : "=r"(val))

#define WRITE_FCSR(val) \
    __asm__ volatile ("fscsr %0" :: "r"(val))

#define READ_FFLAGS(val) \
    __asm__ volatile ("frflags %0" : "=r"(val))

#define WRITE_FFLAGS(val) \
    __asm__ volatile ("fsflags %0" :: "r"(val))

int main(void) {
    sim_puts("Running fp_fma test...\n");

    WRITE_FCSR(0); // clear flags, default RNE

    // =========================================================================
    // 1. FMA Operations (Single Rounding Verification)
    // =========================================================================

    // FMADD: a * b + c
    // 1.5 * 2.0 + 3.0 = 6.0
    float a = 1.5f, b = 2.0f, c = 3.0f, res_fmadd;
    __asm__ volatile ("fmadd.s %0, %1, %2, %3" : "=f"(res_fmadd) : "f"(a), "f"(b), "f"(c));
    unsigned int raw_fmadd;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_fmadd) : "f"(res_fmadd));
    if (raw_fmadd != 0x40C00000) return 1; // 6.0f

    // FMSUB: a * b - c
    // 3.0 * 4.0 - 2.0 = 10.0
    float a2 = 3.0f, b2 = 4.0f, c2 = 2.0f, res_fmsub;
    __asm__ volatile ("fmsub.s %0, %1, %2, %3" : "=f"(res_fmsub) : "f"(a2), "f"(b2), "f"(c2));
    unsigned int raw_fmsub;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_fmsub) : "f"(res_fmsub));
    if (raw_fmsub != 0x41200000) return 2; // 10.0f

    // FNMSUB: -(a * b - c) = -a * b + c
    // -(2.0 * 3.0 - 10.0) = -(6.0 - 10.0) = +4.0f
    float a3 = 2.0f, b3 = 3.0f, c3 = 10.0f, res_fnmsub;
    __asm__ volatile ("fnmsub.s %0, %1, %2, %3" : "=f"(res_fnmsub) : "f"(a3), "f"(b3), "f"(c3));
    unsigned int raw_fnmsub;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_fnmsub) : "f"(res_fnmsub));
    if (raw_fnmsub != 0x40800000) return 3; // 4.0f

    // FNMADD: -(a * b + c) = -a * b - c
    // -(2.0 * 3.0 + 2.0) = -8.0f
    float res_fnmadd;
    __asm__ volatile ("fnmadd.s %0, %1, %2, %3" : "=f"(res_fnmadd) : "f"(a3), "f"(b3), "f"(c2));
    unsigned int raw_fnmadd;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_fnmadd) : "f"(res_fnmadd));
    if (raw_fnmadd != 0xC1000000) return 4; // -8.0f = 0xC1000000 (2*3+2=8 -> -8)

    // =========================================================================
    // 2. IEEE 754 Rounding Modes (RNE, RTZ, RDN, RUP, RMM)
    // =========================================================================

    // Value 1.000000059604644775390625 = 1 + 2^-24
    // In single precision (23 bits mantissa):
    // 1.0f + 2^-24:
    // RNE (ties to even): rounds to 1.0 (since LSB is 0) -> 0x3F800000
    // RTZ (towards zero): rounds to 1.0 -> 0x3F800000
    // RDN (down): rounds to 1.0 -> 0x3F800000
    // RUP (up): rounds up to 1.0 + 2^-23 -> 0x3F800001
    // RMM (max magnitude): rounds up to 1.0 + 2^-23 -> 0x3F800001

    float one = 1.0f;
    float eps;
    unsigned int eps_bits = 0x33800000; // 2^-24
    __asm__ volatile ("fmv.w.x %0, %1" : "=f"(eps) : "r"(eps_bits));

    float res_rne, res_rtz, res_rdn, res_rup, res_rmm;
    __asm__ volatile ("fadd.s %0, %1, %2, rne" : "=f"(res_rne) : "f"(one), "f"(eps));
    __asm__ volatile ("fadd.s %0, %1, %2, rtz" : "=f"(res_rtz) : "f"(one), "f"(eps));
    __asm__ volatile ("fadd.s %0, %1, %2, rdn" : "=f"(res_rdn) : "f"(one), "f"(eps));
    __asm__ volatile ("fadd.s %0, %1, %2, rup" : "=f"(res_rup) : "f"(one), "f"(eps));
    __asm__ volatile ("fadd.s %0, %1, %2, rmm" : "=f"(res_rmm) : "f"(one), "f"(eps));

    unsigned int raw_rne, raw_rtz, raw_rdn, raw_rup, raw_rmm;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_rne) : "f"(res_rne));
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_rtz) : "f"(res_rtz));
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_rdn) : "f"(res_rdn));
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_rup) : "f"(res_rup));
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_rmm) : "f"(res_rmm));

    if (raw_rne != 0x3F800000) return 5;
    if (raw_rtz != 0x3F800000) return 6;
    if (raw_rdn != 0x3F800000) return 7;
    if (raw_rup != 0x3F800001) return 8;
    if (raw_rmm != 0x3F800001) return 9;

    // =========================================================================
    // 3. Dynamic frm Resolution from CSR
    // =========================================================================

    // Set frm in CSR to RUP (3'b011 = 3)
    WRITE_FCSR(3 << 5);
    float res_dyn;
    __asm__ volatile ("fadd.s %0, %1, %2, dyn" : "=f"(res_dyn) : "f"(one), "f"(eps));
    unsigned int raw_dyn;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_dyn) : "f"(res_dyn));
    if (raw_dyn != 0x3F800001) return 10; // Dynamic RUP correctly picked up from frm

    // =========================================================================
    // 4. Special Values & Canonical NaNs
    // =========================================================================

    // 0.0 / 0.0 -> Canonical NaN (0x7FC00000) with Invalid Operation (NV = bit 4)
    WRITE_FCSR(0);
    float zero = 0.0f;
    float nan_res;
    __asm__ volatile ("fdiv.s %0, %1, %2" : "=f"(nan_res) : "f"(zero), "f"(zero));
    unsigned int raw_nan;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_nan) : "f"(nan_res));
    if (raw_nan != 0x7FC00000) return 11; // Must produce Canonical NaN

    unsigned int flags;
    READ_FFLAGS(flags);
    if ((flags & 0x10) == 0) return 12; // NV flag must be set

    // 1.0 / 0.0 -> +Infinity (0x7F800000) with Divide-by-Zero (DZ = bit 3)
    WRITE_FCSR(0);
    float inf_res;
    __asm__ volatile ("fdiv.s %0, %1, %2" : "=f"(inf_res) : "f"(one), "f"(zero));
    unsigned int raw_inf;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_inf) : "f"(inf_res));
    if (raw_inf != 0x7F800000) return 13;

    READ_FFLAGS(flags);
    if ((flags & 0x08) == 0) return 14; // DZ flag must be set

    // FCLASS.S classification
    int cls_pos_inf, cls_nan, cls_pos_zero;
    __asm__ volatile ("fclass.s %0, %1" : "=r"(cls_pos_inf)  : "f"(inf_res)); // Bit 7 (pos inf) = 0x80
    __asm__ volatile ("fclass.s %0, %1" : "=r"(cls_nan)      : "f"(nan_res)); // Bit 9 (quiet nan) = 0x200
    __asm__ volatile ("fclass.s %0, %1" : "=r"(cls_pos_zero) : "f"(zero));    // Bit 4 (pos zero) = 0x10

    if (cls_pos_inf  != 0x80)  return 15;
    if (cls_nan      != 0x200) return 16;
    if (cls_pos_zero != 0x10)  return 17;

    sim_puts("fp_fma: ALL TESTS PASSED!\n");
    return 0; // PASS
}
