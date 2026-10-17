/* Diagnose unexpected newlib system calls in the bare-metal benchmark port. */
#include <stddef.h>
#include "sim_mmio.h"

static void unexpected_syscall(void) {
    sim_puts("\n[Embench] unexpected newlib system call\n");
    sim_exit(2);
}

int _close(int fd) {
    (void)fd;
    unexpected_syscall();
    return -1;
}

int _lseek(int fd, int offset, int whence) {
    (void)fd;
    (void)offset;
    (void)whence;
    unexpected_syscall();
    return -1;
}

int _read(int fd, char *buffer, int count) {
    (void)fd;
    (void)buffer;
    (void)count;
    unexpected_syscall();
    return -1;
}

int _write(int fd, const char *buffer, int count) {
    (void)fd;
    (void)buffer;
    (void)count;
    unexpected_syscall();
    return -1;
}

void *_sbrk(ptrdiff_t increment) {
    (void)increment;
    unexpected_syscall();
    return (void *)-1;
}
