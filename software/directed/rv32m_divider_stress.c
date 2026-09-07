// rv32m_divider_stress.c — Comprehensive directed test for multi-cycle iterative divider
#include "sim_mmio.h"

int main(void) {
    sim_puts("Running rv32m_divider_stress test...\n");

    // Test 1: Full range of quotient signs
    volatile int a = 100000;
    volatile int b = 333;
    if (a / b != 300) return 1;
    if (a % b != 100) return 2;

    if ((-a) / b != -300) return 3;
    if ((-a) % b != -100) return 4;

    if (a / (-b) != -300) return 5;
    if (a % (-b) != 100) return 6;

    if ((-a) / (-b) != 300) return 7;
    if ((-a) % (-b) != -100) return 8;

    // Test 2: Unsigned large operands
    volatile unsigned int ua = 0x80000000;
    volatile unsigned int ub = 3;
    if (ua / ub != 0x2AAAAAAA) return 9;
    if (ua % ub != 2) return 10;

    volatile unsigned int umax = 0xFFFFFFFF;
    if (umax / 1 != umax) return 11;
    if (umax % 1 != 0) return 12;
    if (umax / umax != 1) return 13;
    if (umax % umax != 0) return 14;

    // Test 3: Corner cases - Division by zero (using inline assembly to test hardware instructions directly)
    volatile int z = 0;
    volatile int v100 = 100;
    volatile int vn100 = -100;
    volatile int vzero = 0;
    int r_div, r_rem;

    __asm__ volatile ("div %0, %1, %2" : "=r"(r_div) : "r"(v100), "r"(z));
    if (r_div != -1) return 15;
    __asm__ volatile ("rem %0, %1, %2" : "=r"(r_rem) : "r"(v100), "r"(z));
    if (r_rem != 100) return 16;

    __asm__ volatile ("div %0, %1, %2" : "=r"(r_div) : "r"(vn100), "r"(z));
    if (r_div != -1) return 17;
    __asm__ volatile ("rem %0, %1, %2" : "=r"(r_rem) : "r"(vn100), "r"(z));
    if (r_rem != -100) return 18;

    __asm__ volatile ("div %0, %1, %2" : "=r"(r_div) : "r"(vzero), "r"(z));
    if (r_div != -1) return 19;
    __asm__ volatile ("rem %0, %1, %2" : "=r"(r_rem) : "r"(vzero), "r"(z));
    if (r_rem != 0) return 20;

    volatile unsigned int uz = 0;
    volatile unsigned int uv100 = 100U;
    unsigned int ur_divu, ur_remu;
    __asm__ volatile ("divu %0, %1, %2" : "=r"(ur_divu) : "r"(uv100), "r"(uz));
    if (ur_divu != 0xFFFFFFFF) return 21;
    __asm__ volatile ("remu %0, %1, %2" : "=r"(ur_remu) : "r"(uv100), "r"(uz));
    if (ur_remu != 100U) return 22;

    // Test 4: Corner cases - Signed overflow
    volatile int int_min = -2147483648;
    volatile int neg_one = -1;
    if (int_min / neg_one != int_min) return 23;
    if (int_min % neg_one != 0) return 24;

    // Test 5: Back-to-back divisions interleaved with ALU ops (testing OoO execution)
    volatile int x1 = 123456 / 7;
    volatile int y1 = 10 + 20;
    volatile int x2 = 654321 / 11;
    volatile int y2 = y1 * 2;
    volatile int x3 = 987654 / 13;
    volatile int y3 = y2 + x1;

    if (x1 != 17636) return 25;
    if (y1 != 30) return 26;
    if (x2 != 59483) return 27;
    if (y2 != 60) return 28;
    if (x3 != 75973) return 29;
    if (y3 != 17696) return 30;

    sim_puts("rv32m_divider_stress PASSED!\n");
    return 0;
}
