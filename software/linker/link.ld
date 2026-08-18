/* link.ld — Bare-metal linker script for rv32-ooo */
OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
  RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 1M
}

SECTIONS
{
  . = 0x80000000;

  .text : {
    *(.text.init)
    *(.text .text.*)
  } > RAM

  .rodata : {
    . = ALIGN(4);
    *(.rodata .rodata.*)
  } > RAM

  .data : {
    . = ALIGN(4);
    _sdata = .;
    *(.data .data.*)
    *(.sdata .sdata.*)
    . = ALIGN(4);
    _edata = .;
  } > RAM

  .bss : {
    . = ALIGN(4);
    _sbss = .;
    *(.bss .bss.*)
    *(.sbss .sbss.*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > RAM

  .tohost : {
    . = ALIGN(64);
    *(.tohost)
  } > RAM

  /* Stack at top of 1MB RAM */
  . = ALIGN(16);
  _stack_bottom = .;
  _stack_top = 0x80100000;
  PROVIDE(__stack_top = _stack_top);
}
