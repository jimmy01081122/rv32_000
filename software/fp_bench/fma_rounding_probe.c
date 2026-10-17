/* Exact finite cancellation checks for all four RV32F fused opcodes. */
#include <stdint.h>
#include "sim_mmio.h"

static void hex(uint32_t value) {
    static const char digits[] = "0123456789abcdef";
    for (int s = 28; s >= 0; s -= 4) sim_putc(digits[(value >> s) & 15]);
}

static uint32_t word(float x) {
    union { float f; uint32_t u; } bits = { .f = x };
    return bits.u;
}

int main(void) {
    float a = 0x1.000002p0f, b = 0x1.fffffcp-1f;
    float minus_one = -1.0f, plus_one = 1.0f, product, separate, result[4];
    uint32_t flags[4], separate_flags;
    __asm__ volatile (
        "csrw fflags, zero\n\t"
        "fmul.s %0, %3, %4\n\t"
        "fadd.s %1, %0, %5\n\t"
        "csrr %2, fflags"
        : "=&f"(product), "=&f"(separate), "=r"(separate_flags)
        : "f"(a), "f"(b), "f"(minus_one) : "memory");
#define FUSED(OP, INDEX, C) \
    __asm__ volatile ("csrw fflags, zero\n\t" OP " %0, %2, %3, %4\n\tcsrr %1, fflags" \
        : "=&f"(result[INDEX]), "=r"(flags[INDEX]) : "f"(a), "f"(b), "f"(C) : "memory")
    FUSED("fmadd.s", 0, minus_one);
    FUSED("fmsub.s", 1, plus_one);
    FUSED("fnmsub.s", 2, plus_one);
    FUSED("fnmadd.s", 3, minus_one);
    unsigned failed = word(separate) != 0 || separate_flags != 1;
    sim_puts("FMA PROBE separate="); hex(word(separate));
    sim_puts(" flags="); hex(separate_flags); sim_putc('\n');
    for (unsigned i = 0; i < 4; ++i) {
        uint32_t expected = i < 2 ? 0xa8800000u : 0x28800000u;
        sim_puts("FMA PROBE op="); hex(i);
        sim_puts(" actual="); hex(word(result[i]));
        sim_puts(" expected="); hex(expected);
        sim_puts(" flags="); hex(flags[i]); sim_putc('\n');
        failed += word(result[i]) != expected || flags[i] != 0;
    }
    sim_puts(failed ? "FMA ROUNDING PROBE FAIL\n" : "FMA ROUNDING PROBE PASS\n");
    return failed != 0;
}
