// fp_basic.c — Directed bare-metal test for basic RV32F instructions
// Tests FADD.S, FSUB.S, FMUL.S, FDIV.S, FSQRT.S, FEQ.S, FLT.S, FLE.S,
// FSGNJ.S, FSGNJN.S, FSGNJX.S, FMIN.S, FMAX.S, FCVT, FMV, FLW, FSW
#include "sim_mmio.h"

// Helper macros for assembly FP ops
#define READ_FCSR(val) \
    __asm__ volatile ("frcsr %0" : "=r"(val))

#define WRITE_FCSR(val) \
    __asm__ volatile ("fscsr %0" :: "r"(val))

int main(void) {
    sim_puts("Running fp_basic test...\n");

    // Clear FCSR flags
    WRITE_FCSR(0);

    // 1. Move and Conversions
    volatile int ix = 42;
    float fx;
    __asm__ volatile ("fcvt.s.w %0, %1" : "=f"(fx) : "r"(ix)); // 42.0f
    int ix_out;
    __asm__ volatile ("fcvt.w.s %0, %1" : "=r"(ix_out) : "f"(fx));
    if (ix_out != 42) return 1;

    volatile unsigned int uix = 3000000000U;
    float fux;
    __asm__ volatile ("fcvt.s.wu %0, %1" : "=f"(fux) : "r"(uix));
    unsigned int uix_out;
    __asm__ volatile ("fcvt.wu.s %0, %1" : "=r"(uix_out) : "f"(fux));
    if (uix_out != 3000000000U) return 2;

    // Bitwise FMV
    unsigned int raw_bits = 0x3F800000; // 1.0f in IEEE 754
    float f1;
    __asm__ volatile ("fmv.w.x %0, %1" : "=f"(f1) : "r"(raw_bits));
    unsigned int raw_out;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw_out) : "f"(f1));
    if (raw_out != 0x3F800000) return 3;

    // 2. Basic Arithmetic (FADD, FSUB, FMUL, FDIV, FSQRT)
    float a = 3.5f;
    float b = 2.0f;
    float c_add, c_sub, c_mul, c_div, c_sqrt;

    __asm__ volatile ("fadd.s %0, %1, %2" : "=f"(c_add) : "f"(a), "f"(b));
    __asm__ volatile ("fsub.s %0, %1, %2" : "=f"(c_sub) : "f"(a), "f"(b));
    __asm__ volatile ("fmul.s %0, %1, %2" : "=f"(c_mul) : "f"(a), "f"(b));
    __asm__ volatile ("fdiv.s %0, %1, %2" : "=f"(c_div) : "f"(a), "f"(b));
    __asm__ volatile ("fsqrt.s %0, %1"     : "=f"(c_sqrt) : "f"(b));

    unsigned int add_raw, sub_raw, mul_raw, div_raw;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(add_raw) : "f"(c_add)); // 5.5f = 0x40B00000
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(sub_raw) : "f"(c_sub)); // 1.5f = 0x3FC00000
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(mul_raw) : "f"(c_mul)); // 7.0f = 0x40E00000
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(div_raw) : "f"(c_div)); // 1.75f = 0x3FE00000

    if (add_raw != 0x40B00000) return 4;
    if (sub_raw != 0x3FC00000) return 5;
    if (mul_raw != 0x40E00000) return 6;
    if (div_raw != 0x3FE00000) return 7;

    // FSQRT of 4.0f
    float four = 4.0f;
    float sqrt_four;
    __asm__ volatile ("fsqrt.s %0, %1" : "=f"(sqrt_four) : "f"(four));
    unsigned int sqrt_raw;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(sqrt_raw) : "f"(sqrt_four)); // 2.0f = 0x40000000
    if (sqrt_raw != 0x40000000) return 8;

    // 3. Comparisons (FEQ, FLT, FLE)
    int eq_res, lt_res, le_res, gt_res;
    __asm__ volatile ("feq.s %0, %1, %2" : "=r"(eq_res) : "f"(a), "f"(b)); // 3.5 == 2.0 -> 0
    __asm__ volatile ("flt.s %0, %1, %2" : "=r"(lt_res) : "f"(b), "f"(a)); // 2.0 < 3.5 -> 1
    __asm__ volatile ("fle.s %0, %1, %2" : "=r"(le_res) : "f"(b), "f"(a)); // 2.0 <= 3.5 -> 1
    __asm__ volatile ("fle.s %0, %1, %2" : "=r"(gt_res) : "f"(a), "f"(b)); // 3.5 <= 2.0 -> 0

    if (eq_res != 0) return 9;
    if (lt_res != 1) return 10;
    if (le_res != 1) return 11;
    if (gt_res != 0) return 12;

    // 4. Min / Max
    float min_res, max_res;
    __asm__ volatile ("fmin.s %0, %1, %2" : "=f"(min_res) : "f"(a), "f"(b));
    __asm__ volatile ("fmax.s %0, %1, %2" : "=f"(max_res) : "f"(a), "f"(b));
    unsigned int min_raw, max_raw;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(min_raw) : "f"(min_res)); // 2.0f = 0x40000000
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(max_raw) : "f"(max_res)); // 3.5f = 0x40600000

    if (min_raw != 0x40000000) return 13;
    if (max_raw != 0x40600000) return 14;

    // 5. Sign Injection (FSGNJ, FSGNJN, FSGNJX)
    float pos = 2.5f;
    float neg = -2.5f;
    float sgnj_res, sgnjn_res, sgnjx_res;
    __asm__ volatile ("fsgnj.s  %0, %1, %2" : "=f"(sgnj_res)  : "f"(pos), "f"(neg)); // copies neg sign -> -2.5
    __asm__ volatile ("fsgnjn.s %0, %1, %2" : "=f"(sgnjn_res) : "f"(pos), "f"(neg)); // copies inverted neg sign -> +2.5
    __asm__ volatile ("fsgnjx.s %0, %1, %2" : "=f"(sgnjx_res) : "f"(pos), "f"(neg)); // XOR signs -> -2.5

    unsigned int sgnj_raw, sgnjn_raw, sgnjx_raw;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(sgnj_raw)  : "f"(sgnj_res));
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(sgnjn_raw) : "f"(sgnjn_res));
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(sgnjx_raw) : "f"(sgnjx_res));

    if (sgnj_raw  != 0xC0200000) return 15;
    if (sgnjn_raw != 0x40200000) return 16;
    if (sgnjx_raw != 0xC0200000) return 17;

    // 6. Memory Operations (FLW, FSW)
    volatile float mem_arr[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float loaded_val;
    __asm__ volatile ("flw %0, 8(%1)" : "=f"(loaded_val) : "r"(mem_arr)); // mem_arr[2] = 3.0f
    unsigned int loaded_raw;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(loaded_raw) : "f"(loaded_val));
    if (loaded_raw != 0x40400000) return 18; // 3.0f

    float store_val = 99.0f;
    __asm__ volatile ("fsw %0, 12(%1)" :: "f"(store_val), "r"(mem_arr)); // mem_arr[3] = 99.0f
    if (mem_arr[3] != 99.0f) return 19;

    sim_puts("fp_basic: ALL TESTS PASSED!\n");
    return 0; // PASS
}
