// matmul.c — 4x4 Integer Matrix Multiplication directed test
#include "sim_mmio.h"

#define N 4

static const int A[N][N] = {
    { 1,  2,  3,  4},
    { 5,  6,  7,  8},
    { 9, 10, 11, 12},
    {13, 14, 15, 16}
};

static const int B[N][N] = {
    {16, 15, 14, 13},
    {12, 11, 10,  9},
    { 8,  7,  6,  5},
    { 4,  3,  2,  1}
};

static int C[N][N];

// Expected C = A x B:
// Row 0: 1*16 + 2*12 + 3*8 + 4*4 = 16 + 24 + 24 + 16 = 80
//        1*15 + 2*11 + 3*7 + 4*3 = 15 + 22 + 21 + 12 = 70
//        1*14 + 2*10 + 3*6 + 4*2 = 14 + 20 + 18 + 8  = 60
//        1*13 + 2*9  + 3*5 + 4*1 = 13 + 18 + 15 + 4  = 50
// Row 1: 5*16 + 6*12 + 7*8 + 8*4 = 80 + 72 + 56 + 32 = 240
// Row 2: 9*16 + 10*12 + 11*8 + 12*4 = 144 + 120 + 88 + 48 = 400
// Row 3: 13*16 + 14*12 + 15*8 + 16*4 = 208 + 168 + 120 + 64 = 560
static const int EXPECTED[N][N] = {
    { 80,  70,  60,  50},
    {240, 214, 188, 162},
    {400, 358, 316, 274},
    {560, 502, 444, 386}
};

int main(void) {
    sim_puts("Running integer matmul 4x4 test...\n");

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int sum = 0;
            for (int k = 0; k < N; k++) {
                sum += A[i][k] * B[k][j];
            }
            C[i][j] = sum;
        }
    }

    // Verify results
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] != EXPECTED[i][j]) {
                sim_puts("Error: Matrix mismatch at (");
                sim_putc('0' + i);
                sim_puts(", ");
                sim_putc('0' + j);
                sim_puts(")\n");
                return 1;
            }
        }
    }

    sim_puts("matmul: PASS!\n");
    return 0;
}
