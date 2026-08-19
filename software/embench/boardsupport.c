/* boardsupport.c — Embench-IoT Board Support Implementation for RV32 OoO Core */
#include "boardsupport.h"
#include "support.h"
#include "sim_mmio.h"

static volatile uint64_t start_cycles_64 = 0;
static volatile uint64_t stop_cycles_64 = 0;

static uint64_t get_cycles64(void) {
    uint32_t hi0, lo, hi1;
    do {
        __asm__ volatile("csrr %0, 0xC80" : "=r"(hi0));
        __asm__ volatile("csrr %0, 0xC00" : "=r"(lo));
        __asm__ volatile("csrr %0, 0xC80" : "=r"(hi1));
    } while (hi0 != hi1);
    return ((uint64_t)hi0 << 32) | lo;
}

void initialise_board(void) {
    /* Initialize environment */
}

void __attribute__((noinline)) __attribute__((externally_visible)) start_trigger(void) {
    start_cycles_64 = get_cycles64();
}

void __attribute__((noinline)) __attribute__((externally_visible)) stop_trigger(void) {
    stop_cycles_64 = get_cycles64();
    uint64_t elapsed = stop_cycles_64 - start_cycles_64;
    sim_puts("\n[Embench] Benchmark executed in cycles: ");
    /* Print elapsed decimal */
    char buf[32];
    int len = 0;
    uint64_t temp = elapsed;
    if (temp == 0) {
        buf[len++] = '0';
    } else {
        while (temp > 0) {
            buf[len++] = (char)('0' + (temp % 10));
            temp /= 10;
        }
    }
    int i;
    for (i = len - 1; i >= 0; i--) {
        sim_putc(buf[i]);
    }
    sim_puts("\n");
}
