/* rvmodel_macros.h — DUT Target Model Interface for RV32 OoO Core */
#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

#define RVMODEL_BOOT_TO_MMODE

#define RVMODEL_HALT_PASS \
  li t2, 1                ;\
  la t1, tohost           ;\
write_tohost_pass:        ;\
  sw t2, 0(t1)            ;\
  sw zero, 4(t1)          ;\
  li t0, 0x10000004       ;\
  sw zero, 0(t0)          ;\
  wfi                     ;\
  j write_tohost_pass

#define RVMODEL_HALT_FAIL \
  li t2, 3                ;\
  la t1, tohost           ;\
write_tohost_fail:        ;\
  sw t2, 0(t1)            ;\
  sw zero, 4(t1)          ;\
  li t0, 0x10000004       ;\
  li t3, 1                ;\
  sw t3, 0(t0)            ;\
  wfi                     ;\
  j write_tohost_fail

.EQU UART_BASE_ADDR, 0x10000000
.EQU UART_THR, (UART_BASE_ADDR + 0)
.EQU UART_LCR, (UART_BASE_ADDR + 3)
.EQU UART_LSR, (UART_BASE_ADDR + 5)

#define RVMODEL_IO_INIT(_R1, _R2, _R3)

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1: \
  lbu _R1, 0(_STR_PTR) ;\
  beqz _R1, 2f ;\
  li _R2, UART_THR ;\
  sb _R1, 0(_R2) ;\
  addi _STR_PTR, _STR_PTR, 1 ;\
  j 1b ;\
2:

#define RVMODEL_IO_ASSERT_GPR_EQ(_SP, _R, _VAL)

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000
#define RVMODEL_MTIME_ADDRESS 0x0200BFF8
#define RVMODEL_MTIMECMP_ADDRESS 0x02004000
#define RVMODEL_INTERRUPT_LATENCY 10
#define RVMODEL_TIMER_INT_SOON_DELAY 100
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 100

#define CLINT_BASE_ADDRESS 0x02000000
#define MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)
#define SPIKE_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)

#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)

#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, MSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li _R2, MSIP_ADDRESS; \
  sw zero, 0(_R2);

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#define RVMODEL_SET_SSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, SPIKE_SSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_SSW_INT(_R1, _R2) \
  li _R2, SPIKE_SSIP_ADDRESS; \
  sw zero, 0(_R2);

#endif /* _RVMODEL_MACROS_H */
