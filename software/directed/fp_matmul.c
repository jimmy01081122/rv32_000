// fp_matmul.c — 3x3 Single-Precision Floating-Point Matrix Multiply-Accumulate
#include "sim_mmio.h"

#define N 3

static const float A[N][N] = {
    {1.5f, 2.0f, 0.5f},
    {3.0f, 1.0f, 4.0f},
    {0.5f, 2.5f, 1.5f}
};

static const float B[N][N] = {
    {2.0f, 1.0f, 3.0f},
    {0.5f, 4.0f, 1.0f},
    {1.0f, 2.0f, 0.5f}
};

// Row 0: 1.5*2.0 + 2.0*0.5 + 0.5*1.0 = 3.0 + 1.0 + 0.5 = 4.5
//        1.5*1.0 + 2.0*4.0 + 0.5*2.0 = 1.5 + 8.0 + 1.0 = 10.5
//        1.5*3.0 + 2.0*1.0 + 0.5*0.5 = 4.5 + 2.0 + 0.25 = 6.75
// Row 1: 3.0*2.0 + 1.0*0.5 + 4.0*1.0 = 6.0 + 0.5 + 4.0 = 10.5
//        3.0*1.0 + 1.0*4.0 + 4.0*2.0 = 3.0 + 4.0 + 8.0 = 15.0
//        3.0*3.0 + 1.0*1.0 + 4.0*0.5 = 9.0 + 1.0 + 2.0 = 12.0
// Row 2: 0.5*2.0 + 2.5*0.5 + 1.5*1.0 = 1.0 + 1.25 + 1.5 = 3.75
//        0.5*1.0 + 2.5*4.0 + 1.5*2.0 = 0.5 + 10.0 + 3.0 = 13.5
//        0.5*3.0 + 2.5*1.0 + 1.5*0.5 = 1.5 + 2.5 + 0.75 = 4.75

// Raw IEEE 754 bit representations:
// 4.5f  = 0x40900000
// 10.5f = 0x41280000
// 6.75f = 0x40D80000
// 10.5f = 0x41280000
// 15.0f = 0x41700000
// 12.0f = 0x41400000
// 3.75f = 0x40700000
// 13.5f = 0x41580000
// 4.75f = 0x40980000

static const unsigned int EXPECTED_RAW[N][N] = {
    {0x40900000, 0x41280000, 0x40D80000},
    {0x41280000, 0x41700000, 0x41400000},
    {0x40700000, 0x41580000, 0x40980000}
};

static float C[N][N];

int main(void) {
    sim_puts("Running fp_matmul test...\n");

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            float sum = 0.0f;
            for (int k = 0; k < N; k++) {
                float a = A[i][k];
                float b = B[k][j];
                // Using FMADD: sum = a * b + sum
                __asm__ volatile ("fmadd.s %0, %1, %2, %0" : "+f"(sum) : "f"(a), "f"(b));
            }
            C[i][j] = sum;
        }
    }

    // Verify bit-exact results
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            unsigned int raw;
            float val = C[i][j];
            __asm__ volatile ("fmv.x.w %0, %1" : "=r"(raw) : "f"(val));
            if (raw != EXPECTED_RAW[i][j]) {
                sim_puts("Error: FP Matmul mismatch at (");
                sim_putc('0' + i);
                sim_puts(", ");
                sim_putc('0' + j);
                sim_puts(")\n");
                return 1;
            }
        }
    }

    sim_puts("fp_matmul: PASS!\n");
    return 0;
}
