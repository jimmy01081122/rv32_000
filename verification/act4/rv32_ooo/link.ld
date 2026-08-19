/* Linker script for RV32 OoO Core ACT4 architectural test suite */
RAM_ORIGIN = 0x80000000;
RAM_LENGTH = 0x00100000; /* 1 MB */
TEST_BASE  = RAM_ORIGIN;
NUM_HARTS  = 1;
STACK_SIZE = 0x8000;

OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

MEMORY
{
  ram (rwx) : ORIGIN = RAM_ORIGIN, LENGTH = RAM_LENGTH
}

PROVIDE(__stack_size = STACK_SIZE);
PROVIDE(__num_harts = NUM_HARTS);

SECTIONS
{
  .text.init TEST_BASE : {
    *(.text.init)
  } > ram

  .text.rvtest . : {
    *(.text.rvtest)
    *(.text.rvtest.*)
  } > ram

  . = ALIGN(0x1000);
  .tohost . : {
    *(.tohost)
  } > ram

  . = ALIGN(0x1000);
  .rodata . : {
    *(.rodata)
    *(.rodata.*)
    *(.srodata)
    *(.srodata.*)
  } > ram

  .data . : {
    *(.data)
    *(.data.*)
    *(.sdata)
    *(.sdata.*)
  } > ram

  . = ALIGN(16);
  .bss . : {
    __bss_start = .;
    *(.sbss)
    *(.sbss.*)
    *(.bss)
    *(.bss.*)
    *(COMMON)
    . = ALIGN(16);
    __bss_end = .;
  } > ram

  . = ALIGN(16);
  __stack_bottom = .;
  . += __stack_size * __num_harts;
  __stack_top = .;

  . = ALIGN(0x1000);
  .text.rvmodel . : {
    *(.text.rvmodel)
    *(.text.rvmodel.*)
    *(.text)
    *(.text.*)
  } > ram

  . = ALIGN(0x1000);
  _end = .;
}
