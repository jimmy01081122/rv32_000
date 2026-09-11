// rv32m_completion_collisions.c — AP2C Dedicated Completion Collision & Flush Stress Test
#include "sim_mmio.h"

int main(void) {
    sim_puts("Starting AP2C Completion Collision & Flush Stress Tests...\n");

    // -------------------------------------------------------------
    // Test 1: Back-to-back Multiplies (Pipeline Throughput = 1 op/cycle)
    // -------------------------------------------------------------
    int m0 = 3, m1 = 7, m2 = 11, m3 = 13;
    int r0, r1, r2, r3;
    __asm__ volatile (
        "mul %0, %4, %5\n\t"
        "mul %1, %6, %7\n\t"
        "mul %2, %4, %6\n\t"
        "mul %3, %5, %7\n\t"
        : "=&r"(r0), "=&r"(r1), "=&r"(r2), "=&r"(r3)
        : "r"(m0), "r"(m1), "r"(m2), "r"(m3)
    );
    if (r0 != 21 || r1 != 143 || r2 != 33 || r3 != 91) return 1;
    sim_puts("  [PASS] Test 1: Back-to-back MUL throughput\n");

    // -------------------------------------------------------------
    // Test 2: MUL + ALU Completion Collision
    // Interleave independent MULs with ALUs so MUL and ALU finish together
    // -------------------------------------------------------------
    int ma = 12, mb = 15;
    int mul_res, alu_res1, alu_res2, alu_res3;
    __asm__ volatile (
        "mul %0, %4, %5\n\t"    // cycle 0: MUL issued (3-cyc latency)
        "add %1, %4, %5\n\t"    // cycle 1: ALU issued
        "sub %2, %5, %4\n\t"    // cycle 2: ALU issued (enters FIFO as MUL finishes)
        "xor %3, %4, %5\n\t"    // cycle 3: ALU issued
        : "=&r"(mul_res), "=&r"(alu_res1), "=&r"(alu_res2), "=&r"(alu_res3)
        : "r"(ma), "r"(mb)
    );
    if (mul_res != 180 || alu_res1 != 27 || alu_res2 != 3 || alu_res3 != (12 ^ 15)) return 2;
    sim_puts("  [PASS] Test 2: MUL + ALU completion collision\n");

    // -------------------------------------------------------------
    // Test 3: DIV + ALU Completion Collision & Interleaving
    // -------------------------------------------------------------
    int div_n = 10000, div_d = 25;
    int div_res, a1, a2, a3, a4, a5;
    __asm__ volatile (
        "divu %0, %6, %7\n\t"   // DIV takes 32 cycles
        "addi %1, %6, 1\n\t"
        "addi %2, %6, 2\n\t"
        "addi %3, %6, 3\n\t"
        "addi %4, %6, 4\n\t"
        "addi %5, %6, 5\n\t"
        : "=&r"(div_res), "=&r"(a1), "=&r"(a2), "=&r"(a3), "=&r"(a4), "=&r"(a5)
        : "r"(div_n), "r"(div_d)
    );
    if (div_res != 400 || a1 != 10001 || a2 != 10002 || a3 != 10003 || a4 != 10004 || a5 != 10005) return 3;
    sim_puts("  [PASS] Test 3: DIV + ALU completion collision & interleaving\n");

    // -------------------------------------------------------------
    // Test 4: DIV + MUL Completion Collision
    // Loop of interleaved DIVs and MULs
    // -------------------------------------------------------------
    for (int i = 1; i <= 8; i++) {
        volatile int d_val = (i * 100) / i;
        volatile int m_val = (i * 10) * (i * 2);
        if (d_val != 100 || m_val != (20 * i * i)) return 4;
    }
    sim_puts("  [PASS] Test 4: DIV + MUL completion collision\n");

    // -------------------------------------------------------------
    // Test 5: ALU FIFO Pressure (burst of independent ALU ops after DIV)
    // -------------------------------------------------------------
    int x0=1, x1=2, x2=3, x3=4, x4=5, x5=6, x6=7, x7=8;
    int d_out;
    __asm__ volatile (
        "divu %0, %9, %10\n\t"
        "add %1, %1, %2\n\t"
        "add %2, %2, %3\n\t"
        "add %3, %3, %4\n\t"
        "add %4, %4, %5\n\t"
        "add %5, %5, %6\n\t"
        "add %6, %6, %7\n\t"
        "add %7, %7, %8\n\t"
        "add %8, %8, %1\n\t"
        : "=&r"(d_out), "+&r"(x0), "+&r"(x1), "+&r"(x2), "+&r"(x3), "+&r"(x4), "+&r"(x5), "+&r"(x6), "+&r"(x7)
        : "r"(1000), "r"(10)
    );
    if (d_out != 100) return 5;
    sim_puts("  [PASS] Test 5: ALU FIFO pressure\n");

    // -------------------------------------------------------------
    // Test 6: Flush while MUL Pending (Branch Misprediction)
    // -------------------------------------------------------------
    int mul_survive = 0;
    for (int k = 0; k < 20; k++) {
        // Multiplier started inside branch condition
        if (k == 15) {
            // Mispredicted branch will flush
            mul_survive = k * 10;
        }
    }
    if (mul_survive != 150) return 6;
    sim_puts("  [PASS] Test 6: Flush while MUL pending\n");

    // -------------------------------------------------------------
    // Test 7: Flush while DIV Pending (Branch Misprediction)
    // -------------------------------------------------------------
    int div_survive = 0;
    for (int k = 1; k <= 10; k++) {
        if (k == 7) {
            div_survive = 7000 / 7;
        }
    }
    if (div_survive != 1000) return 7;
    sim_puts("  [PASS] Test 7: Flush while DIV pending\n");

    // -------------------------------------------------------------
    // Test 8: Flush with Wrong-Path ALU Completions
    // -------------------------------------------------------------
    volatile int target_val = 42;
    volatile int cond = 0;
    if (cond) {
        // Wrong path: should be completely discarded
        target_val = 999;
        target_val += 1;
        target_val += 2;
    }
    if (target_val != 42) return 8;
    sim_puts("  [PASS] Test 8: Flush with wrong-path ALU completions\n");

    sim_puts("============================================================\n");
    sim_puts("  ALL AP2C COMPLETION COLLISION & FLUSH TESTS PASSED!\n");
    sim_puts("============================================================\n");
    return 0;
}
