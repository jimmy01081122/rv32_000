/* Finite FMA bit/flag regression; expected words come from an integer oracle. */
#include <stdint.h>
#include "sim_mmio.h"
#include "fma_vectors.h"

static void hex(uint32_t value) {
    static const char digits[] = "0123456789abcdef";
    for (int shift = 28; shift >= 0; shift -= 4) sim_putc(digits[(value >> shift) & 15]);
}

int main(void) {
    uint32_t failures = 0, checksum = 2166136261u;
    for (unsigned i = 0; i < FMA_VECTOR_COUNT; ++i) {
        const uint32_t *v = fma_vectors[i];
        union { uint32_t u; float f; } a = {.u=v[2]}, b = {.u=v[3]}, c = {.u=v[4]}, result;
        uint32_t flags;
        __asm__ volatile ("csrw frm, %0\n\tcsrw fflags, zero" : : "r"(v[1]) : "memory");
#define EXECUTE(OP) __asm__ volatile (OP " %0, %2, %3, %4\n\tcsrr %1, fflags" \
    : "=&f"(result.f), "=r"(flags) : "f"(a.f), "f"(b.f), "f"(c.f) : "memory")
        switch (v[0]) {
            case 0: EXECUTE("fmadd.s"); break;
            case 1: EXECUTE("fmsub.s"); break;
            case 2: EXECUTE("fnmsub.s"); break;
            default: EXECUTE("fnmadd.s"); break;
        }
        checksum = (checksum ^ result.u ^ flags) * 16777619u;
        if (result.u != v[5] || flags != v[6]) {
            if (failures < 16) {
                sim_puts("FMA VECTOR FAIL index="); hex(i);
                sim_puts(" actual="); hex(result.u); sim_puts(" expected="); hex(v[5]);
                sim_puts(" flags="); hex(flags); sim_puts(" expected_flags="); hex(v[6]); sim_putc('\n');
            }
            ++failures;
        }
    }
    __asm__ volatile ("csrw frm, zero" : : : "memory");
    sim_puts(failures ? "FMA VECTORS FAIL count=" : "FMA VECTORS PASS count="); hex(FMA_VECTOR_COUNT);
    sim_puts(" failures="); hex(failures); sim_puts(" checksum="); hex(checksum); sim_putc('\n');
    return failures != 0;
}
