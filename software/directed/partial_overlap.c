#include "sim_mmio.h"

// Test Partial Byte Overlap Store/Load ordering
// Tests writing a word, then overwriting a single byte, followed by a full word load.

volatile uint32_t overlap_buf[4];

int main(void) {
    sim_puts("[TEST] Starting partial_overlap test...\n");

    overlap_buf[0] = 0x11223344;

    volatile uint8_t *byte_ptr = (volatile uint8_t *)&overlap_buf[0];
    byte_ptr[1] = 0xAA; // Modify byte 1: 0x1122AA44

    uint32_t result = overlap_buf[0];

    if (result != 0x1122AA44) {
        sim_puts("[FAIL] Partial overlap load returned incorrect data!\n");
        return 1;
    }

    sim_puts("[PASS] Partial byte overlap load verified.\n");
    return 0;
}
