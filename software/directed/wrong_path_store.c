#include "sim_mmio.h"

// Test wrong-path speculative store isolation
// A branch misprediction must NEVER allow wrong-path stores to modify memory.

volatile uint32_t canary_memory[4] = {0x11223344, 0x55667788, 0x99AABBCC, 0xDDEEFF00};
volatile int branch_condition = 1;

int main(void) {
    sim_puts("[TEST] Starting wrong_path_store test...\n");

    // We execute a conditional branch that is taken.
    // Static predictor predicts not-taken, so speculative execution enters the if-block.
    // Inside the if-block, store instructions attempt to overwrite canary_memory.
    if (branch_condition == 0) {
        // Speculative wrong path!
        canary_memory[0] = 0xDEADBEEF;
        canary_memory[1] = 0xBAADF00D;
        canary_memory[2] = 0xCAFEBABE;
        canary_memory[3] = 0x00000000;
    }

    // Architectural verification
    if (canary_memory[0] != 0x11223344 ||
        canary_memory[1] != 0x55667788 ||
        canary_memory[2] != 0x99AABBCC ||
        canary_memory[3] != 0xDDEEFF00) {
        sim_puts("[FAIL] Canary memory was corrupted by speculative store!\n");
        return 1;
    }

    sim_puts("[PASS] Canary memory untouched. Speculative stores correctly isolated.\n");
    return 0;
}
