// rv32_csr.c — Directed test for Machine-Mode CSRs
#include "sim_mmio.h"

int main(void) {
    sim_puts("Running rv32_csr test...\n");

    // 1. Write and read mscratch
    uint32_t scratch_val = 0xDEADBEEF;
    uint32_t readback = 0;

    __asm__ volatile ("csrw mscratch, %0" :: "r"(scratch_val));
    __asm__ volatile ("csrr %0, mscratch" : "=r"(readback));
    if (readback != scratch_val) return 1;

    // 2. Atomic Set (CSRRS)
    uint32_t set_mask = 0x00000010;
    uint32_t old_val = 0;
    __asm__ volatile ("csrrs %0, mscratch, %1" : "=r"(old_val) : "r"(set_mask));
    if (old_val != scratch_val) return 2;

    __asm__ volatile ("csrr %0, mscratch" : "=r"(readback));
    if (readback != (scratch_val | set_mask)) return 3;

    // 3. Read mcycle and minstret counters
    uint32_t cycle0 = 0, cycle1 = 0;
    __asm__ volatile ("csrr %0, mcycle" : "=r"(cycle0));
    // Do some work
    for (volatile int i = 0; i < 20; i++) {}
    __asm__ volatile ("csrr %0, mcycle" : "=r"(cycle1));

    if (cycle1 <= cycle0) return 4;

    sim_puts("rv32_csr PASSED!\n");
    return 0;
}
