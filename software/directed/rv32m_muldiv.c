// rv32m_muldiv.c — Directed test for RV32M Multiply and Divide Extension
#include "sim_mmio.h"

int main(void) {
    sim_puts("Running rv32m_muldiv test...\n");

    // 1. Multiplications
    volatile int a = 12345;
    volatile int b = 6789;
    if (a * b != 83810205) return 1;

    volatile int neg = -100;
    volatile int pos = 25;
    if (neg * pos != -2500) return 2;

    // High multiplications
    volatile int big1 = 0x7FFFFFFF;
    volatile int big2 = 2;
    long long full_mul = (long long)big1 * (long long)big2;
    int hi_mul = (int)(full_mul >> 32);
    // In assembly MULH:
    int res_hi;
    __asm__ volatile ("mulh %0, %1, %2" : "=r"(res_hi) : "r"(big1), "r"(big2));
    if (res_hi != hi_mul) return 3;

    // 2. Division & Remainder
    volatile int num = 1000;
    volatile int den = 7;
    if (num / den != 142) return 4;
    if (num % den != 6) return 5;

    volatile int snum = -100;
    volatile int sden = 6;
    if (snum / sden != -16) return 6;
    if (snum % sden != -4) return 7;

    // 3. Unsigned Division
    volatile unsigned int unum = 0xFFFFFFFF;
    volatile unsigned int uden = 10;
    if (unum / uden != 429496729) return 8;
    if (unum % uden != 5) return 9;

    // 4. RISC-V Corner Cases: Division by zero
    volatile int zero = 0;
    if (num / zero != -1) return 10;
    if (num % zero != num) return 11;
    if (unum / (unsigned int)zero != 0xFFFFFFFF) return 12;
    if (unum % (unsigned int)zero != unum) return 13;

    // 5. Signed Overflow: INT_MIN / -1
    volatile int min_int = -2147483648;
    volatile int minus_one = -1;
    if (min_int / minus_one != min_int) return 14;
    if (min_int % minus_one != 0) return 15;

    sim_puts("rv32m_muldiv PASSED!\n");
    return 0;
}
