// qsort.c — QuickSort recursive benchmark on 32 elements
#include "sim_mmio.h"

static int data[32] = {
    88, 12, 45, 99, 2, 67, 34, 21,
    76, 54, 11,  9, 3, 90, 81, 23,
    56, 78, 65, 43, 1, 98, 87, 66,
    55, 44, 33, 22, 5, 10, 19, 72
};

static void swap(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;
}

static int partition(int arr[], int low, int high) {
    int pivot = arr[high];
    int i = (low - 1);

    for (int j = low; j < high; j++) {
        if (arr[j] <= pivot) {
            i++;
            swap(&arr[i], &arr[j]);
        }
    }
    swap(&arr[i + 1], &arr[high]);
    return (i + 1);
}

static void quick_sort(int arr[], int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quick_sort(arr, low, pi - 1);
        quick_sort(arr, pi + 1, high);
    }
}

int main(void) {
    sim_puts("Running quicksort test...\n");

    quick_sort(data, 0, 31);

    // Verify monotonically non-decreasing
    for (int i = 0; i < 31; i++) {
        if (data[i] > data[i + 1]) {
            sim_puts("Error: Sorting failed at index ");
            sim_putc('0' + (i / 10));
            sim_putc('0' + (i % 10));
            sim_puts("\n");
            return 1;
        }
    }

    sim_puts("qsort: PASS!\n");
    return 0;
}
