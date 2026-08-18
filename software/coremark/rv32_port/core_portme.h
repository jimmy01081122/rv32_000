/* core_portme.h — RV32 Out-of-Order Core Bare-Metal CoreMark Port */
#ifndef CORE_PORTME_H
#define CORE_PORTME_H

#include <stdint.h>
#include <stddef.h>

#define HAS_FLOAT 0
#define HAS_TIME_H 0
#define USE_CLOCK 0
#define HAS_STDIO 0
#define HAS_PRINTF 0

#define COMPILER_VERSION "RISC-V GCC 16.1.0"
#ifndef COMPILER_FLAGS
#define COMPILER_FLAGS "-march=rv32im_zicsr -mabi=ilp32 -O2"
#endif
#define MEM_LOCATION "STATIC"

typedef int16_t   ee_s16;
typedef uint16_t  ee_u16;
typedef int32_t   ee_s32;
typedef double    ee_f32;
typedef uint8_t   ee_u8;
typedef uint32_t  ee_u32;
typedef uintptr_t ee_ptr_int;
typedef size_t    ee_size_t;

#define NULL ((void *)0)
#define align_mem(x) (void *)(4 + (((ee_ptr_int)(x)-1) & ~3))

typedef ee_u32 CORETIMETYPE;
typedef ee_u32 CORE_TICKS;

#define GETMYTIME(_t)              (*_t = (ee_u32)get_mcycle_lo())
#define MYTIMEDIFF(fin, ini)       ((fin) - (ini))
#define TIMER_RES_DIVIDER          1
#define SAMPLE_TIME_IMPLEMENTATION 1
#define EE_TICKS_PER_SEC           1000000

#define MEM_METHOD MEM_STATIC
#define SEED_METHOD SEED_VOLATILE

#ifndef MULTITHREAD
#define MULTITHREAD 1
#endif
#define default_num_contexts 1

typedef struct CORE_PORTABLE_S {
    ee_u8 portable_id;
} core_portable;

void portable_init(core_portable *p, int *argc, char *argv[]);
void portable_fini(core_portable *p);

int ee_printf(const char *fmt, ...);
uint32_t get_mcycle_lo(void);
uint64_t get_mcycle64(void);

#endif /* CORE_PORTME_H */
