#ifndef SIM_MMIO_H
#define SIM_MMIO_H

#include <stdint.h>

#define SIM_PUTC_ADDR     0x10000000UL
#define SIM_EXIT_ADDR     0x10000004UL
#define SIM_STATUS_ADDR   0x10000008UL

static inline void sim_putc(char c) {
    *(volatile uint32_t *)SIM_PUTC_ADDR = (uint32_t)(uint8_t)c;
}

static inline void sim_puts(const char *str) {
    while (*str) {
        sim_putc(*str++);
    }
}

static inline void sim_exit(int code) {
    *(volatile uint32_t *)SIM_EXIT_ADDR = (uint32_t)code;
    while (1) {}
}

#endif /* SIM_MMIO_H */
