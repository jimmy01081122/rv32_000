// fp_edge_cases.c — Comprehensive directed bare-metal test for Simple FP instructions (AP4B)
// Tests: FMV.X.W, FMV.W.X, FSGNJ.S, FSGNJN.S, FSGNJX.S, FEQ.S, FLT.S, FLE.S, FCLASS.S, FMIN.S, FMAX.S
// Covers: NaN (sNaN, qNaN), ±Inf, ±0, Subnormals, Normals, precise NV flag generation, and branch flushes.

#include "sim_mmio.h"

#define READ_FCSR(val)  __asm__ volatile ("frcsr %0" : "=r"(val))
#define WRITE_FCSR(val) __asm__ volatile ("fscsr %0" :: "r"(val))

// Bitwise bit patterns for IEEE 754 single-precision float
#define POS_ZERO       0x00000000U
#define NEG_ZERO       0x80000000U
#define POS_INF        0x7F800000U
#define NEG_INF        0xFF800000U
#define CANONICAL_NAN  0x7FC00000U
#define QNAN_PAYLOAD   0x7FC01234U
#define SNAN_PAYLOAD   0x7F805678U // bit 22 = 0, nonzero mantissa
#define NEG_SNAN       0xFF805678U
#define POS_SUBNORM    0x00000001U // min positive subnormal
#define NEG_SUBNORM    0x80000001U // min negative subnormal
#define POS_NORM       0x3F800000U // +1.0f
#define NEG_NORM       0xBF800000U // -1.0f
#define POS_TWO        0x40000000U // +2.0f
#define NEG_TWO        0xC0000000U // -2.0f

static inline float u2f(unsigned int u) {
    float f;
    __asm__ volatile ("fmv.w.x %0, %1" : "=f"(f) : "r"(u));
    return f;
}

static inline unsigned int f2u(float f) {
    unsigned int u;
    __asm__ volatile ("fmv.x.w %0, %1" : "=r"(u) : "f"(f));
    return u;
}

int main(void) {
    sim_puts("Running fp_edge_cases test...\n");
    unsigned int flags;

    // ─────────────────────────────────────────────────────────────────────────
    // 1. FMV.W.X and FMV.X.W Bit-Exact Preservation (including sNaN payloads)
    // ─────────────────────────────────────────────────────────────────────────
    WRITE_FCSR(0);
    if (f2u(u2f(SNAN_PAYLOAD)) != SNAN_PAYLOAD) return 101;
    if (f2u(u2f(NEG_SNAN))     != NEG_SNAN)     return 102;
    if (f2u(u2f(QNAN_PAYLOAD)) != QNAN_PAYLOAD) return 103;
    if (f2u(u2f(POS_SUBNORM))  != POS_SUBNORM)  return 104;
    if (f2u(u2f(NEG_ZERO))     != NEG_ZERO)     return 105;
    READ_FCSR(flags);
    if (flags != 0) return 106; // FMV must never set flags

    // ─────────────────────────────────────────────────────────────────────────
    // 2. FCLASS.S (10 Categories)
    // ─────────────────────────────────────────────────────────────────────────
    int c;
    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(NEG_INF)));
    if (c != (1 << 0)) return 201; // bit 0: -inf

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(NEG_NORM)));
    if (c != (1 << 1)) return 202; // bit 1: -normal

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(NEG_SUBNORM)));
    if (c != (1 << 2)) return 203; // bit 2: -subnormal

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(NEG_ZERO)));
    if (c != (1 << 3)) return 204; // bit 3: -0.0

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(POS_ZERO)));
    if (c != (1 << 4)) return 205; // bit 4: +0.0

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(POS_SUBNORM)));
    if (c != (1 << 5)) return 206; // bit 5: +subnormal

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(POS_NORM)));
    if (c != (1 << 6)) return 207; // bit 6: +normal

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(POS_INF)));
    if (c != (1 << 7)) return 208; // bit 7: +inf

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(SNAN_PAYLOAD)));
    if (c != (1 << 8)) return 209; // bit 8: signaling NaN

    __asm__ volatile ("fclass.s %0, %1" : "=r"(c) : "f"(u2f(QNAN_PAYLOAD)));
    if (c != (1 << 9)) return 210; // bit 9: quiet NaN

    READ_FCSR(flags);
    if (flags != 0) return 211; // FCLASS must never set flags

    // ─────────────────────────────────────────────────────────────────────────
    // 3. FSGNJ.S, FSGNJN.S, FSGNJX.S (Sign Manipulation)
    // ─────────────────────────────────────────────────────────────────────────
    float f_pos = u2f(POS_NORM);
    float f_neg = u2f(NEG_NORM);
    float res;

    // FSGNJ
    __asm__ volatile ("fsgnj.s %0, %1, %2" : "=f"(res) : "f"(f_pos), "f"(f_neg));
    if (f2u(res) != NEG_NORM) return 301;
    __asm__ volatile ("fsgnj.s %0, %1, %2" : "=f"(res) : "f"(f_neg), "f"(f_pos));
    if (f2u(res) != POS_NORM) return 302;

    // FSGNJN
    __asm__ volatile ("fsgnjn.s %0, %1, %2" : "=f"(res) : "f"(f_pos), "f"(f_neg));
    if (f2u(res) != POS_NORM) return 303;
    __asm__ volatile ("fsgnjn.s %0, %1, %2" : "=f"(res) : "f"(f_pos), "f"(f_pos));
    if (f2u(res) != NEG_NORM) return 304;

    // FSGNJX
    __asm__ volatile ("fsgnjx.s %0, %1, %2" : "=f"(res) : "f"(f_pos), "f"(f_neg));
    if (f2u(res) != NEG_NORM) return 305;
    __asm__ volatile ("fsgnjx.s %0, %1, %2" : "=f"(res) : "f"(f_neg), "f"(f_neg));
    if (f2u(res) != POS_NORM) return 306;

    READ_FCSR(flags);
    if (flags != 0) return 307; // FSGNJ ops never set flags

    // ─────────────────────────────────────────────────────────────────────────
    // 4. FEQ.S, FLT.S, FLE.S (Corner Cases & IEEE NV Flag Checks)
    // ─────────────────────────────────────────────────────────────────────────
    int cmp_out;

    // +0 == -0 is true
    WRITE_FCSR(0);
    __asm__ volatile ("feq.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(POS_ZERO)), "f"(u2f(NEG_ZERO)));
    if (cmp_out != 1) return 401;
    __asm__ volatile ("flt.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(POS_ZERO)), "f"(u2f(NEG_ZERO)));
    if (cmp_out != 0) return 402;
    __asm__ volatile ("fle.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(POS_ZERO)), "f"(u2f(NEG_ZERO)));
    if (cmp_out != 1) return 403;
    READ_FCSR(flags);
    if (flags != 0) return 404;

    // qNaN comparison:
    // FEQ with qNaN: returns 0, does NOT set NV
    WRITE_FCSR(0);
    __asm__ volatile ("feq.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(QNAN_PAYLOAD)), "f"(u2f(POS_NORM)));
    if (cmp_out != 0) return 405;
    READ_FCSR(flags);
    if ((flags & 0x10) != 0) return 406; // NV should be 0

    // FLT with qNaN: returns 0, DOES set NV (bit 4 of fflags)
    WRITE_FCSR(0);
    __asm__ volatile ("flt.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(QNAN_PAYLOAD)), "f"(u2f(POS_NORM)));
    if (cmp_out != 0) return 407;
    READ_FCSR(flags);
    if ((flags & 0x10) == 0) return 408; // NV must be set

    // FLE with qNaN: returns 0, DOES set NV
    WRITE_FCSR(0);
    __asm__ volatile ("fle.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(QNAN_PAYLOAD)), "f"(u2f(POS_NORM)));
    if (cmp_out != 0) return 409;
    READ_FCSR(flags);
    if ((flags & 0x10) == 0) return 410; // NV must be set

    // sNaN comparison:
    // FEQ with sNaN: returns 0, DOES set NV
    WRITE_FCSR(0);
    __asm__ volatile ("feq.s %0, %1, %2" : "=r"(cmp_out) : "f"(u2f(SNAN_PAYLOAD)), "f"(u2f(POS_NORM)));
    if (cmp_out != 0) return 411;
    READ_FCSR(flags);
    if ((flags & 0x10) == 0) return 412; // NV must be set

    // ─────────────────────────────────────────────────────────────────────────
    // 5. FMIN.S & FMAX.S (Corner Cases, -0 vs +0, NaNs)
    // ─────────────────────────────────────────────────────────────────────────
    // -0.0 is considered smaller than +0.0
    WRITE_FCSR(0);
    __asm__ volatile ("fmin.s %0, %1, %2" : "=f"(res) : "f"(u2f(POS_ZERO)), "f"(u2f(NEG_ZERO)));
    if (f2u(res) != NEG_ZERO) return 501;
    __asm__ volatile ("fmax.s %0, %1, %2" : "=f"(res) : "f"(u2f(POS_ZERO)), "f"(u2f(NEG_ZERO)));
    if (f2u(res) != POS_ZERO) return 502;

    // If one operand is NaN, return the other non-NaN operand (qNaN does not set NV)
    __asm__ volatile ("fmin.s %0, %1, %2" : "=f"(res) : "f"(u2f(QNAN_PAYLOAD)), "f"(u2f(POS_TWO)));
    if (f2u(res) != POS_TWO) return 503;
    __asm__ volatile ("fmax.s %0, %1, %2" : "=f"(res) : "f"(u2f(QNAN_PAYLOAD)), "f"(u2f(POS_TWO)));
    if (f2u(res) != POS_TWO) return 504;
    READ_FCSR(flags);
    if ((flags & 0x10) != 0) return 505; // qNaN should not set NV

    // If both operands are NaN, return CANONICAL_NAN
    __asm__ volatile ("fmin.s %0, %1, %2" : "=f"(res) : "f"(u2f(QNAN_PAYLOAD)), "f"(u2f(0x7FC09999U)));
    if (f2u(res) != CANONICAL_NAN) return 506;

    // sNaN sets NV on FMIN/FMAX
    WRITE_FCSR(0);
    __asm__ volatile ("fmin.s %0, %1, %2" : "=f"(res) : "f"(u2f(SNAN_PAYLOAD)), "f"(u2f(POS_TWO)));
    if (f2u(res) != POS_TWO) return 507;
    READ_FCSR(flags);
    if ((flags & 0x10) == 0) return 508; // sNaN must set NV

    // ─────────────────────────────────────────────────────────────────────────
    // 6. Speculative Flush / Branch Discard Verification
    // ─────────────────────────────────────────────────────────────────────────
    volatile int cond = 0;
    float speculative_res = u2f(POS_NORM);
    if (cond) {
        // This branch will be dynamically mispredicted/flushed during execution
        __asm__ volatile ("fmax.s %0, %1, %2" : "=f"(speculative_res) : "f"(u2f(POS_INF)), "f"(u2f(POS_NORM)));
    }
    if (f2u(speculative_res) != POS_NORM) return 601;

    sim_puts("fp_edge_cases: ALL TESTS PASSED!\n");
    return 0;
}
