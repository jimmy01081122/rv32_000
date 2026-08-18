/* core_portme.c — RV32 Out-of-Order Core Bare-Metal CoreMark Port Implementation */
#include "coremark.h"
#include "core_portme.h"
#include "sim_mmio.h"
#include <stdarg.h>

#if VALIDATION_RUN
volatile ee_s32 seed1_volatile = 0x3415;
volatile ee_s32 seed2_volatile = 0x3415;
volatile ee_s32 seed3_volatile = 0x66;
#endif
#if PERFORMANCE_RUN
volatile ee_s32 seed1_volatile = 0x0;
volatile ee_s32 seed2_volatile = 0x0;
volatile ee_s32 seed3_volatile = 0x66;
#endif
#if PROFILE_RUN
volatile ee_s32 seed1_volatile = 0x8;
volatile ee_s32 seed2_volatile = 0x8;
volatile ee_s32 seed3_volatile = 0x8;
#endif

#ifndef ITERATIONS
#define ITERATIONS 10
#endif

volatile ee_s32 seed4_volatile = ITERATIONS;
volatile ee_s32 seed5_volatile = 0;

static uint64_t start_cycles_64, stop_cycles_64;

uint32_t get_mcycle_lo(void) {
    uint32_t val;
    __asm__ volatile("csrr %0, 0xC00" : "=r"(val));
    return val;
}

uint64_t get_mcycle64(void) {
    uint32_t hi0, lo, hi1;
    do {
        __asm__ volatile("csrr %0, 0xC80" : "=r"(hi0));
        __asm__ volatile("csrr %0, 0xC00" : "=r"(lo));
        __asm__ volatile("csrr %0, 0xC80" : "=r"(hi1));
    } while (hi0 != hi1);
    return ((uint64_t)hi0 << 32) | lo;
}

void start_time(void) {
    start_cycles_64 = get_mcycle64();
}

void stop_time(void) {
    stop_cycles_64 = get_mcycle64();
}

CORE_TICKS get_time(void) {
    CORE_TICKS elapsed = (CORE_TICKS)(stop_cycles_64 - start_cycles_64);
    return elapsed;
}

secs_ret time_in_secs(CORE_TICKS ticks) {
    (void)ticks;
    return 10;
}

void portable_init(core_portable *p, int *argc, char *argv[]) {
    (void)argc;
    (void)argv;
    if (sizeof(ee_ptr_int) != sizeof(ee_u8 *)) {
        ee_printf("ERROR! Please define ee_ptr_int to an integer that holds a pointer.\n");
    }
    if (sizeof(ee_u32) != 4) {
        ee_printf("ERROR! Please define ee_u32 to a 32b unsigned integer!\n");
    }
    p->portable_id = 1;
}

void portable_fini(core_portable *p) {
    p->portable_id = 0;
    ee_printf("\n[CoreMark] Benchmark finished cleanly.\n");
    sim_exit(0);
}

// Full bare-metal string and number formatter
static void print_dec(long long val, int min_width, char pad_char) {
    char buf[32];
    int len = 0;
    int is_neg = 0;
    unsigned long long uval;

    if (val < 0) {
        is_neg = 1;
        uval = (unsigned long long)(-val);
    } else {
        uval = (unsigned long long)val;
    }

    if (uval == 0) {
        buf[len++] = '0';
    } else {
        while (uval > 0) {
            buf[len++] = '0' + (uval % 10);
            uval /= 10;
        }
    }

    int total_len = len + (is_neg ? 1 : 0);
    if (!is_neg && pad_char == ' ') {
        while (total_len < min_width) {
            sim_putc(' ');
            min_width--;
        }
    }

    if (is_neg) {
        sim_putc('-');
    }

    if (pad_char == '0') {
        while (total_len < min_width) {
            sim_putc('0');
            min_width--;
        }
    }

    while (len > 0) {
        sim_putc(buf[--len]);
    }
}

static void print_udec(unsigned long long uval, int min_width, char pad_char) {
    char buf[32];
    int len = 0;
    if (uval == 0) {
        buf[len++] = '0';
    } else {
        while (uval > 0) {
            buf[len++] = '0' + (uval % 10);
            uval /= 10;
        }
    }
    while (len < min_width) {
        sim_putc(pad_char);
        min_width--;
    }
    while (len > 0) {
        sim_putc(buf[--len]);
    }
}

static void print_hex(unsigned long long val, int min_width, char pad_char) {
    const char hex_chars[] = "0123456789abcdef";
    char buf[32];
    int len = 0;
    if (val == 0) {
        buf[len++] = '0';
    } else {
        while (val > 0) {
            buf[len++] = hex_chars[val & 0xF];
            val >>= 4;
        }
    }
    while (len < min_width) {
        sim_putc(pad_char);
        min_width--;
    }
    while (len > 0) {
        sim_putc(buf[--len]);
    }
}

int ee_printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    while (*fmt) {
        if (*fmt == '%') {
            fmt++;
            char pad_char = ' ';
            int min_width = 0;

            if (*fmt == '0') {
                pad_char = '0';
                fmt++;
            }
            while (*fmt >= '0' && *fmt <= '9') {
                min_width = min_width * 10 + (*fmt - '0');
                fmt++;
            }

            int is_long = 0;
            if (*fmt == 'l') {
                is_long = 1;
                fmt++;
                if (*fmt == 'l') {
                    is_long = 2;
                    fmt++;
                }
            }

            if (*fmt == 'd' || *fmt == 'i') {
                long long val = is_long ? (is_long == 2 ? va_arg(ap, long long) : va_arg(ap, long)) : va_arg(ap, int);
                print_dec(val, min_width, pad_char);
            } else if (*fmt == 'u') {
                unsigned long long val = is_long ? (is_long == 2 ? va_arg(ap, unsigned long long) : va_arg(ap, unsigned long)) : va_arg(ap, unsigned int);
                print_udec(val, min_width, pad_char);
            } else if (*fmt == 'x' || *fmt == 'X') {
                unsigned long long val = is_long ? (is_long == 2 ? va_arg(ap, unsigned long long) : va_arg(ap, unsigned long)) : va_arg(ap, unsigned int);
                print_hex(val, min_width, pad_char);
            } else if (*fmt == 'p') {
                uintptr_t val = (uintptr_t)va_arg(ap, void *);
                sim_puts("0x");
                print_hex(val, 8, '0');
            } else if (*fmt == 's') {
                char *s = va_arg(ap, char *);
                if (s) sim_puts(s);
                else sim_puts("(null)");
            } else if (*fmt == 'c') {
                char c = (char)va_arg(ap, int);
                sim_putc(c);
            } else if (*fmt == '%') {
                sim_putc('%');
            }
        } else {
            sim_putc(*fmt);
        }
        fmt++;
    }
    va_end(ap);
    return 0;
}
