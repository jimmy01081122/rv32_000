.file "lsu_fault.S"
/* Environment-only access-fault fixture; no Spike comparison for injected faults.
 * CASE: 0=SW, 1=SB(+1), 2=SH(+2), 3=FSW, 4=LW, 5=FLW.
 * The handler skips the fault and its younger instructions, then checks recovery.
 */
.section .text.init
.globl _start
_start:
    li t0, 0x6000
    csrs mstatus, t0
    la t0, handler
    csrw mtvec, t0
    la s0, fault_pc
    la s1, fault_word
#if CASE == 1
    addi s1, s1, 1
#elif CASE == 2
    addi s1, s1, 2
#endif
    la s2, resume
#if CASE >= 4
    li s3, 5
#else
    li s3, 7
#endif
    li s4, 0
    li s5, 0x12345
    li s6, 0x31415926
    li s7, 0
    fmv.w.x ft1, s6
    fmv.w.x ft0, s6
    la a1, younger_word
    li a0, 0x76543210
.globl fault_pc
fault_pc:
#if CASE == 0
    sw a0, 0(s1)
#elif CASE == 1
    sb a0, 0(s1)
#elif CASE == 2
    sh a0, 0(s1)
#elif CASE == 3
    fsw ft0, 0(s1)
#elif CASE == 4
    lw s5, 0(s1)
#elif CASE == 5
    flw ft1, 0(s1)
#endif
.globl younger_register_pc
younger_register_pc:
    addi s7, s7, 1
.globl younger_store_pc
younger_store_pc:
    sw a0, 0(a1)
    j fail
resume:
    li t0, 1
    bne s4, t0, fail
    bnez s7, fail
    li t0, 0x12345
    bne s5, t0, fail
    fmv.x.w t0, ft1
    bne t0, s6, fail
    la a2, fault_word
    lw t0, 0(a2)
    li t1, 0x11223344
    bne t0, t1, fail
    /* A fresh store/load after MRET catches stale SQ ownership or reissue. */
    li t1, 0x55667788
    sw t1, 0(a2)
    lw t0, 0(a2)
    bne t0, t1, fail
    la a2, younger_word
    lw t0, 0(a2)
    bnez t0, fail
    li a0, 0
    j finish
.balign 4
handler:
    csrr t0, mcause
    bne t0, s3, fail
    csrr t0, mepc
    bne t0, s0, fail
    csrr t0, mtval
    bne t0, s1, fail
    bnez s7, fail
    la t0, younger_word
    lw t1, 0(t0)
    bnez t1, fail
    addi s4, s4, 1
    csrw mepc, s2
    mret
fail:
    li a0, 1
finish:
    li t0, 0x10000004
    sw a0, 0(t0)
    wfi
    j finish
.section .data
.balign 4
.globl fault_word
fault_word: .word 0x11223344
.globl younger_word
younger_word: .word 0
