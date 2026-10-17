/* Provisional qualification adapters; upstream kernels remain unchanged. */
#include <stdint.h>
#include <string.h>
#include "fp_fixture.h"
#ifndef FP_CASE
#error FP_CASE must select a qualification adapter
#endif
#ifdef FP_BENCH_HOST
#include <stdio.h>
#else
#include "sim_mmio.h"
#endif

#if FP_CASE <= 3 || FP_CASE == 7
#include "arm_math.h"
#endif
#if FP_CASE == 2
#include "kiss_fft.h"
#endif
#if FP_CASE >= 4 && FP_CASE <= 6
/* Include the pinned kernel in this TU to call its static function directly.
 * The upstream main, initializer and printing functions are discarded. */
#define main fp_unused_upstream_main
#if FP_CASE == 4
#include "gemm.c"
#elif FP_CASE == 5
#include "bicg.c"
#else
#include "cholesky.c"
#endif
#undef main
#endif

static float fp_values[FP_EXPECT_COUNT];

static void emit(const char *s) {
    while (*s) {
#ifdef FP_BENCH_HOST
        putchar(*s++);
#else
        sim_putc(*s++);
#endif
    }
}

static void hex32(uint32_t v) {
    static const char digits[] = "0123456789abcdef";
    char text[9];
    for (unsigned i = 0; i < 8; ++i) text[i] = digits[(v >> (28 - 4 * i)) & 15];
    text[8] = 0;
    emit(text);
}

static uint32_t bits(float f) {
    uint32_t u;
    memcpy(&u, &f, sizeof u);
    return u;
}

static uint32_t cycles(void) {
#ifdef FP_BENCH_HOST
    return 0;
#else
    uint32_t value;
    __asm__ volatile ("rdcycle %0" : "=r"(value) : : "memory");
    return value;
#endif
}

#if FP_CASE == 0
static arm_fir_instance_f32 instance;
static float state[32 + 256 - 1];
static int prepare(void) {
    arm_fir_init_f32(&instance, 32, fx_coeff, state, 256);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    arm_fir_f32(&instance, fx_input, fp_values, 256);
}
static int finish(void) {
    memcpy(fp_values + 256, state, 31 * sizeof(float));
    arm_fir_init_f32(&instance, 32, fx_coeff, state, 64);
    for (unsigned n = 0; n < 256; n += 64)
        arm_fir_f32(&instance, fx_input + n, fp_values + 287 + n, 64);
    memcpy(fp_values + 543, state, 31 * sizeof(float));
    return 0;
}
#elif FP_CASE == 1
static arm_biquad_cascade_df2T_instance_f32 instance;
static float state[8];
static int prepare(void) {
    arm_biquad_cascade_df2T_init_f32(&instance, 4, fx_coeff, state);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    arm_biquad_cascade_df2T_f32(&instance, fx_input, fp_values, 256);
}
static int finish(void) {
    memcpy(fp_values + 256, state, sizeof state);
    arm_biquad_cascade_df2T_init_f32(&instance, 4, fx_coeff, state);
    for (unsigned n = 0; n < 256; n += 64)
        arm_biquad_cascade_df2T_f32(&instance, fx_input + n, fp_values + 264 + n, 64);
    memcpy(fp_values + 520, state, sizeof state);
    return 0;
}
#elif FP_CASE == 2
static union { uint64_t alignment; unsigned char bytes[16384]; } storage;
static kiss_fft_cpx input[256], output[256];
static kiss_fft_cfg instance;
static volatile unsigned allocation_violation;
void *fp_fft_malloc(size_t size) {
    (void)size;
    allocation_violation = 1;
    return 0;
}
void fp_fft_free(void *pointer) {
    (void)pointer;
    allocation_violation = 1;
}
static int prepare(void) {
    for (unsigned n = 0; n < 256; ++n) {
        input[n].r = fx_input[2 * n];
        input[n].i = fx_input[2 * n + 1];
    }
    size_t length = sizeof storage.bytes;
    instance = kiss_fft_alloc(256, 0, storage.bytes, &length);
    return !instance;
}
__attribute__((noinline)) void fp_kernel(void) {
    kiss_fft(instance, input, output);
}
static int finish(void) {
    for (unsigned n = 0; n < 256; ++n) {
        fp_values[2 * n] = output[n].r;
        fp_values[2 * n + 1] = output[n].i;
    }
    return allocation_violation != 0;
}
#elif FP_CASE == 3
static arm_pid_instance_f32 instance;
static int prepare(void) {
    instance.Kp = fx_gains[0];
    instance.Ki = fx_gains[1];
    instance.Kd = fx_gains[2];
    arm_pid_init_f32(&instance, 1);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    for (unsigned n = 0; n < 512; ++n)
        fp_values[n] = arm_pid_f32(&instance, fx_input[n]);
}
static int finish(void) {
    memcpy(fp_values + 512, instance.state, 3 * sizeof(float));
    return 0;
}
#elif FP_CASE == 4
static float a[NI][NK], b[NK][NJ], c[NI][NJ];
static int prepare(void) {
    memcpy(a, fx_A, sizeof a);
    memcpy(b, fx_B, sizeof b);
    memcpy(c, fx_C, sizeof c);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    kernel_gemm(NI, NJ, NK, fx_scalars[0], fx_scalars[1], c, a, b);
}
static int finish(void) {
    memcpy(fp_values, c, sizeof c);
    return 0;
}
#elif FP_CASE == 5
static float a[N][M], p[M], r[N], s[M], q[N];
static int prepare(void) {
    memcpy(a, fx_A, sizeof a);
    memcpy(p, fx_p, sizeof p);
    memcpy(r, fx_r, sizeof r);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    kernel_bicg(M, N, a, s, q, p, r);
}
static int finish(void) {
    memcpy(fp_values, s, sizeof s);
    memcpy(fp_values + M, q, sizeof q);
    return 0;
}
#elif FP_CASE == 6
static float a[N][N];
static int prepare(void) {
    memcpy(a, fx_A, sizeof a);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    kernel_cholesky(N, a);
}
static int finish(void) {
    unsigned count = 0;
    for (unsigned i = 0; i < N; ++i)
        for (unsigned j = 0; j <= i; ++j)
            fp_values[count++] = a[i][j];
    return 0;
}
#elif FP_CASE == 7
static arm_svm_linear_instance_f32 instance;
static const int32_t classes[2] = { FX_CLASS0, FX_CLASS1 };
static int32_t labels[FX_SAMPLES];
static int prepare(void) {
    arm_svm_linear_init_f32(&instance, FX_SUPPORT_VECTORS, FX_DIMENSION,
        fx_params[FX_SUPPORT_VECTORS * (FX_DIMENSION + 1)],
        fx_params + FX_SUPPORT_VECTORS * FX_DIMENSION, fx_params, classes);
    return 0;
}
__attribute__((noinline)) void fp_kernel(void) {
    for (unsigned n = 0; n < FX_SAMPLES; ++n)
        arm_svm_linear_predict_f32(&instance, fx_input + n * FX_DIMENSION, labels + n);
}
static int finish(void) {
    for (unsigned n = 0; n < FX_SAMPLES; ++n) fp_values[n] = (float)labels[n];
    return 0;
}
#else
#error Unknown FP_CASE
#endif

int main(void) {
    if (prepare()) { emit("FP BALANCED FAIL initialization\n"); return 1; }
    uint32_t start = cycles();
    fp_kernel();
    uint32_t elapsed = cycles() - start;
    if (finish()) { emit("FP BALANCED FAIL unexpected allocation\n"); return 2; }
    uint32_t checksum = 2166136261u;
    unsigned failed = 0;
    for (unsigned i = 0; i < FP_EXPECT_COUNT; ++i) {
        float error = fp_values[i] - fx_expected[i];
        float magnitude = fx_expected[i];
        if (error < 0) error = -error;
        if (magnitude < 0) magnitude = -magnitude;
        if (!(error <= FP_ATOL + FP_RTOL * magnitude)) ++failed;
        checksum = (checksum ^ bits(fp_values[i])) * 16777619u;
        emit("FP DATA "); hex32(i); emit(" "); hex32(bits(fp_values[i])); emit("\n");
    }
    emit(failed ? "FP BALANCED FAIL name=" : "FP BALANCED PASS name=");
    emit(FP_NAME); emit(" checksum="); hex32(checksum);
    emit(" cycles="); hex32(elapsed);
    emit(" checked="); hex32(FP_EXPECT_COUNT); emit("\n");
    return failed != 0;
}
