// fibonacci.c — Fibonacci recursive & iterative test
#include "sim_mmio.h"

int fib_recursive(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    return fib_recursive(n - 1) + fib_recursive(n - 2);
}

int fib_iterative(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    int a = 0, b = 1;
    for (int i = 2; i <= n; i++) {
        int c = a + b;
        a = b;
        b = c;
    }
    return b;
}

int main(void) {
    sim_puts("Running fibonacci test...\n");

    // fib(10) = 55
    if (fib_iterative(10) != 55) return 1;
    if (fib_recursive(10) != 55) return 2;

    // fib(12) = 144
    if (fib_iterative(12) != 144) return 3;
    if (fib_recursive(12) != 144) return 4;

    sim_puts("fibonacci PASSED!\n");
    return 0;
}
