/* crt0.S — Minimal RISC-V bare-metal runtime for rv32-ooo */
.section .text.init
.global _start
.type _start, @function

_start:
    /* Initialize stack pointer */
    la sp, __stack_top

    /* Initialize integer registers to 0 */
    mv x1,  zero
    mv x3,  zero
    mv x4,  zero
    mv x5,  zero
    mv x6,  zero
    mv x7,  zero
    mv x8,  zero
    mv x9,  zero
    mv x10, zero
    mv x11, zero
    mv x12, zero
    mv x13, zero
    mv x14, zero
    mv x15, zero
    mv x16, zero
    mv x17, zero
    mv x18, zero
    mv x19, zero
    mv x20, zero
    mv x21, zero
    mv x22, zero
    mv x23, zero
    mv x24, zero
    mv x25, zero
    mv x26, zero
    mv x27, zero
    mv x28, zero
    mv x29, zero
    mv x30, zero
    mv x31, zero

    /* Clear BSS */
    la t0, _sbss
    la t1, _ebss
bss_clear_loop:
    bge t0, t1, bss_clear_done
    sw zero, 0(t0)
    addi t0, t0, 4
    j bss_clear_loop
bss_clear_done:

    /* Call main() */
    call main

    /* Write exit code from main (in a0) to SIM_EXIT (0x10000004) */
    li t0, 0x10000004
    sw a0, 0(t0)

    /* Write exit code to tohost for Spike HTIF */
    slli a0, a0, 1
    ori a0, a0, 1
    la t1, tohost
    sw a0, 0(t1)

    /* Infinite loop if simulation continues */
halt_loop:
    wfi
    j halt_loop

.size _start, . - _start

.section .tohost, "aw", @progbits
.align 6
.global tohost
tohost:   .dword 0
.global fromhost
fromhost: .dword 0
