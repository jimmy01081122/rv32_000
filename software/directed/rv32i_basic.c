// rv32i_basic.c — Directed test for RV32I base integer instructions
#include "sim_mmio.h"

int main(void) {
    sim_puts("Running rv32i_basic test...\n");

    // 1. Basic Arithmetic
    volatile int a = 42;
    volatile int b = 58;
    if (a + b != 100) return 1;
    if (b - a != 16) return 2;
    if ((a & b) != (42 & 58)) return 3;
    if ((a | b) != (42 | 58)) return 4;
    if ((a ^ b) != (42 ^ 58)) return 5;

    // 2. Shifts
    volatile unsigned int u = 0x12345678;
    if ((u << 4) != 0x23456780) return 6;
    if ((u >> 4) != 0x01234567) return 7;
    volatile int s = -16;
    if ((s >> 2) != -4) return 8;

    // 3. Comparisons
    if (!(a < b)) return 9;
    if (b < a) return 10;
    volatile unsigned int u1 = 5;
    volatile unsigned int u2 = 0xFFFFFFFF;
    if (!(u1 < u2)) return 11;

    // 4. Memory Byte & Halfword access
    volatile unsigned char byte_buf[4] = {0x12, 0x34, 0xAB, 0xCD};
    if (byte_buf[0] != 0x12) return 12;
    if (byte_buf[1] != 0x34) return 13;
    if (byte_buf[2] != 0xAB) return 14;
    if (byte_buf[3] != 0xCD) return 15;

    volatile signed char sbyte = (signed char)byte_buf[2]; // 0xAB -> -85
    if (sbyte != -85) return 16;

    volatile unsigned short half_buf[2] = {0x5678, 0x9ABC};
    if (half_buf[0] != 0x5678) return 17;
    if (half_buf[1] != 0x9ABC) return 18;

    volatile signed short shalf = (signed short)half_buf[1]; // 0x9ABC -> negative
    if (shalf >= 0) return 19;

    sim_puts("rv32i_basic PASSED!\n");
    return 0;
}
