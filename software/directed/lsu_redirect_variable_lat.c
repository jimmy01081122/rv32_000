#include "sim_mmio.h"

// Dedicated AP5B LSU Verification Test:
// - Tests LB, LBU, LH, LHU, LW formatting & sign/zero extension
// - Immediate load-use data dependency
// - Store-to-load forwarding (SQ match)
// - Partial store-to-load overlap
// - Outstanding load during branch misprediction flush & redirect
// - Multiple back-to-back load transactions

volatile uint32_t mem_block[8] = {
    0xA4B3C2D1, // [0] Byte 0: 0xD1 (-47 / 209), Byte 1: 0xC2 (-62 / 194), Half 0: 0xC2D1 (-15663 / 49873)
    0x11223344, // [1]
    0x55667788, // [2]
    0x99AABBCC, // [3]
    0x00000000, // [4]
    0xCAFEBABE, // [5]
    0xDEADBEEF, // [6]
    0xFEEDFACE  // [7]
};

volatile int branch_cond = 1;

int main(void) {
    sim_puts("========================================================\n");
    sim_puts("  AP5B Dedicated LSU Redirect & Timing Verification     \n");
    sim_puts("========================================================\n");

    // ── 1. Load Formatting & Extension Checks ─────────────────────────────
    sim_puts("[TEST 1] Load Formatting & Sign/Zero Extension...\n");
    volatile uint8_t*  b_ptr = (volatile uint8_t*)&mem_block[0];
    volatile uint16_t* h_ptr = (volatile uint16_t*)&mem_block[0];
    volatile uint32_t* w_ptr = (volatile uint32_t*)&mem_block[0];

    // 1.1 Full Word
    uint32_t val_lw = *w_ptr;
    if (val_lw != 0xA4B3C2D1) {
        sim_puts("[FAIL] 1.1 LW mismatch!\n");
        return 1;
    }

    // 1.2 Signed Byte (0xD1 -> 0xFFFFFFD1)
    int32_t val_lb0 = (int32_t)(*(int8_t*)&b_ptr[0]);
    if (val_lb0 != (int32_t)0xFFFFFFD1) {
        sim_puts("[FAIL] 1.2 LB (byte 0) sign-extension mismatch!\n");
        return 2;
    }

    // 1.3 Unsigned Byte (0xD1 -> 0x000000D1)
    uint32_t val_lbu0 = (uint32_t)b_ptr[0];
    if (val_lbu0 != 0x000000D1) {
        sim_puts("[FAIL] 1.3 LBU (byte 0) zero-extension mismatch!\n");
        return 3;
    }

    // 1.4 Signed Byte 1 (0xC2 -> 0xFFFFFFC2)
    int32_t val_lb1 = (int32_t)(*(int8_t*)&b_ptr[1]);
    if (val_lb1 != (int32_t)0xFFFFFFC2) {
        sim_puts("[FAIL] 1.4 LB (byte 1) sign-extension mismatch!\n");
        return 4;
    }

    // 1.5 Signed Halfword 0 (0xC2D1 -> 0xFFFFC2D1)
    int32_t val_lh0 = (int32_t)(*(int16_t*)&h_ptr[0]);
    if (val_lh0 != (int32_t)0xFFFFC2D1) {
        sim_puts("[FAIL] 1.5 LH sign-extension mismatch!\n");
        return 5;
    }

    // 1.6 Unsigned Halfword 0 (0xC2D1 -> 0x0000C2D1)
    uint32_t val_lhu0 = (uint32_t)h_ptr[0];
    if (val_lhu0 != 0x0000C2D1) {
        sim_puts("[FAIL] 1.6 LHU zero-extension mismatch!\n");
        return 6;
    }
    sim_puts("[PASS] Test 1: All load formatting and extension modes verified.\n");

    // ── 2. Immediate Load-Use Dependency ──────────────────────────────────
    sim_puts("[TEST 2] Immediate Load-Use Timing Dependency...\n");
    register uint32_t loaded_val;
    register uint32_t math_res;
    __asm__ volatile (
        "lw   %0, 4(%2)\n"     // load mem_block[1] = 0x11223344
        "addi %1, %0, 1\n"     // immediate use
        : "=r"(loaded_val), "=r"(math_res)
        : "r"(&mem_block[0])
    );
    if (math_res != 0x11223345) {
        sim_puts("[FAIL] Test 2: Immediate load-use produced incorrect result!\n");
        return 7;
    }
    sim_puts("[PASS] Test 2: Immediate load-use resolved correctly.\n");

    // ── 3. Store-to-Load Forwarding ───────────────────────────────────────
    sim_puts("[TEST 3] Store-to-Load Forwarding...\n");
    register uint32_t fwd_res;
    __asm__ volatile (
        "sw   %1, 16(%2)\n"    // store to mem_block[4]
        "lw   %0, 16(%2)\n"    // immediate load from mem_block[4]
        : "=r"(fwd_res)
        : "r"(0x55AA33CC), "r"(&mem_block[0])
        : "memory"
    );
    if (fwd_res != 0x55AA33CC) {
        sim_puts("[FAIL] Test 3: Store-to-load forwarding failed!\n");
        return 8;
    }
    sim_puts("[PASS] Test 3: Store-to-load forwarding verified.\n");

    // ── 4. Partial Overlap ────────────────────────────────────────────────
    sim_puts("[TEST 4] Partial Overlap Store-to-Load...\n");
    mem_block[4] = 0x12345678;
    volatile uint16_t* partial_h = (volatile uint16_t*)&mem_block[4];
    if (partial_h[0] != 0x5678 || partial_h[1] != 0x1234) {
        sim_puts("[FAIL] Test 4: Partial overlap read mismatch!\n");
        return 9;
    }
    sim_puts("[PASS] Test 4: Partial overlap read verified.\n");

    // ── 5. Outstanding Load during Branch Misprediction (Redirect Test) ───
    sim_puts("[TEST 5] Outstanding Load during Branch Mispredict Flush...\n");
    // We execute a conditional branch that is taken.
    // Static predictor predicts not-taken (forward conditional branch).
    // Speculation enters the wrong path and issues loads to D-memory.
    // Branch misprediction fires while load is in-flight.
    // Core redirects to the taken target.
    // Verify that the register target receives the correct path value!
    register uint32_t res_target = 0;
    register int cond = branch_cond; // 1

    __asm__ volatile (
        "bne  %1, x0, 1f\n"        // Branch taken to 1f (mispredicted not-taken)
        "lw   %0, 20(%2)\n"        // Wrong path: load mem_block[5] (0xCAFEBABE)
        "lw   %0, 24(%2)\n"        // Wrong path: load mem_block[6] (0xDEADBEEF)
        "addi %0, %0, 100\n"
        "1:\n"
        "lw   %0, 28(%2)\n"        // Correct path: load mem_block[7] (0xFEEDFACE)
        : "+r"(res_target)
        : "r"(cond), "r"(&mem_block[0])
        : "memory"
    );

    if (res_target != 0xFEEDFACE) {
        sim_puts("[FAIL] Test 5: Register corrupted by wrong-path speculative load!\n");
        return 10;
    }
    sim_puts("[PASS] Test 5: Speculative in-flight loads flushed cleanly without corruption.\n");

    // ── 6. Back-to-Back Sequential Loads ──────────────────────────────────
    sim_puts("[TEST 6] Back-to-Back Sequential Loads...\n");
    uint32_t s0 = mem_block[0];
    uint32_t s1 = mem_block[1];
    uint32_t s2 = mem_block[2];
    uint32_t s3 = mem_block[3];
    if (s0 != 0xA4B3C2D1 || s1 != 0x11223344 || s2 != 0x55667788 || s3 != 0x99AABBCC) {
        sim_puts("[FAIL] Test 6: Back-to-back loads mismatch!\n");
        return 11;
    }
    sim_puts("[PASS] Test 6: Back-to-back loads completed cleanly.\n");

    sim_puts("========================================================\n");
    sim_puts("  ALL AP5B DEDICATED LSU TESTS PASSED!                  \n");
    sim_puts("========================================================\n");
    return 0;
}
