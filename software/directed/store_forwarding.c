#include "sim_mmio.h"

// Test Store-to-Load Forwarding (RAW hazard bypass)
// Tests word, halfword, and byte stores immediately followed by dependent loads.

volatile uint32_t target_buf[8];

int main(void) {
    sim_puts("[TEST] Starting store_forwarding test...\n");

    // 1. Word store followed immediately by word load
    target_buf[0] = 0xDEADBEEF;
    uint32_t w_val = target_buf[0];
    if (w_val != 0xDEADBEEF) {
        sim_puts("[FAIL] Word store-to-load forwarding failed!\n");
        return 1;
    }

    // 2. Halfword store followed immediately by halfword load
    volatile uint16_t *h_ptr = (volatile uint16_t *)&target_buf[1];
    h_ptr[0] = 0xABCD;
    uint16_t h_val0 = h_ptr[0];
    h_ptr[1] = 0x1234;
    uint16_t h_val1 = h_ptr[1];
    if (h_val0 != 0xABCD || h_val1 != 0x1234) {
        sim_puts("[FAIL] Halfword store-to-load forwarding failed!\n");
        return 2;
    }

    // 3. Byte store followed immediately by byte load
    volatile uint8_t *b_ptr = (volatile uint8_t *)&target_buf[2];
    b_ptr[0] = 0x11;
    b_ptr[1] = 0x22;
    b_ptr[2] = 0x33;
    b_ptr[3] = 0x44;

    uint8_t b0 = b_ptr[0];
    uint8_t b1 = b_ptr[1];
    uint8_t b2 = b_ptr[2];
    uint8_t b3 = b_ptr[3];

    if (b0 != 0x11 || b1 != 0x22 || b2 != 0x33 || b3 != 0x44) {
        sim_puts("[FAIL] Byte store-to-load forwarding failed!\n");
        return 3;
    }

    // 4. Full word verification after multi-byte writes
    uint32_t combined = target_buf[2];
    if (combined != 0x44332211) {
        sim_puts("[FAIL] Combined word mismatch after byte writes!\n");
        return 4;
    }

    sim_puts("[PASS] Store-to-load forwarding verified across all data sizes.\n");
    return 0;
}
