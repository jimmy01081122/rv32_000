#include "sim_mmio.h"

// Test Memory Disambiguation with Unresolved and Interleaved Stores
// Verifies that loads to unrelated addresses proceed while loads to dependent addresses wait.

volatile uint32_t mem_array[16];

int main(void) {
    sim_puts("[TEST] Starting unresolved_store test...\n");

    for (int i = 0; i < 16; i++) {
        mem_array[i] = i * 10;
    }

    // Sequence with data dependency in address calculation
    volatile int idx = 5;
    mem_array[idx] = 999;
    
    // Read an independent location and the updated location
    uint32_t val_independent = mem_array[0];
    uint32_t val_dependent   = mem_array[5];

    if (val_independent != 0) {
        sim_puts("[FAIL] Independent memory read corrupted!\n");
        return 1;
    }
    if (val_dependent != 999) {
        sim_puts("[FAIL] Dependent memory read failed!\n");
        return 2;
    }

    sim_puts("[PASS] Memory disambiguation with unresolved store verified.\n");
    return 0;
}
