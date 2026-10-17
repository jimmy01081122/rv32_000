/* Diagnostic FIR port for the selected FP32 set; sizes/tolerance are provisional. */
#include <stdint.h>
#include "arm_math.h"

#ifndef FP_BENCH_HOST
#include "sim_mmio.h"
#endif

#define TAPS 32u
#define BLOCK 256u

static float input[BLOCK];
static float coeff[TAPS];
static float state[TAPS + BLOCK - 1u];
static float output[BLOCK];

static void emit(char c) {
#ifdef FP_BENCH_HOST
    extern int putchar(int);
    putchar(c);
#else
    sim_putc(c);
#endif
}

static void emit_str(const char *s) {
    while (*s) emit(*s++);
}

static void emit_hex(uint32_t value) {
    static const char digits[] = "0123456789abcdef";
    for (int shift = 28; shift >= 0; shift -= 4) {
        emit(digits[(value >> shift) & 15u]);
    }
}

#ifndef FP_BENCH_HOST
static uint32_t cycles(void) {
    uint32_t value;
    __asm__ volatile ("rdcycle %0" : "=r"(value));
    return value;
}
#endif

int main(void) {
    arm_fir_instance_f32 fir;
    for (unsigned i = 0; i < BLOCK; ++i)
        input[i] = (float)((int)((i * 37u + 11u) % 113u) - 56) / 64.0f;
    /* CMSIS stores coefficients from oldest to newest input sample. */
    for (unsigned k = 0; k < TAPS; ++k)
        coeff[k] = (float)((int)((k * 17u + 3u) % 43u) - 21) / 512.0f;
    arm_fir_init_f32(&fir, TAPS, coeff, state, BLOCK);

#ifndef FP_BENCH_HOST
    uint32_t start = cycles();
#endif
    arm_fir_f32(&fir, input, output, BLOCK);
#ifndef FP_BENCH_HOST
    uint32_t elapsed = cycles() - start;
#endif

    uint32_t checksum = 2166136261u;
    for (unsigned n = 0; n < BLOCK; ++n) {
        double expected = 0.0;
        for (unsigned k = 0; k < TAPS; ++k) {
            int index = (int)n - (int)(TAPS - 1u) + (int)k;
            if (index >= 0) expected += (double)coeff[k] * (double)input[index];
        }
        double error = (double)output[n] - expected;
        if (error < 0.0) error = -error;
        if (!(error <= 0.00001)) {
            emit_str("FP FIR PILOT FAIL output\n");
            return 1;
        }
        union { float f; uint32_t u; } bits = { .f = output[n] };
        checksum = (checksum ^ bits.u) * 16777619u;
    }
    for (unsigned k = 0; k < TAPS - 1u; ++k) {
        if (state[k] != input[BLOCK - (TAPS - 1u) + k]) {
            emit_str("FP FIR PILOT FAIL state\n");
            return 2;
        }
    }

    emit_str("FP FIR PILOT PASS checksum=");
    emit_hex(checksum);
#ifndef FP_BENCH_HOST
    emit_str(" cycles=");
    emit_hex(elapsed);
#endif
    emit('\n');
    return 0;
}
