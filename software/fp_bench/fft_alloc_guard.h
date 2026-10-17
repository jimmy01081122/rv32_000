/* KissFFT must use supplied state and separate input/output buffers. */
#ifndef FP_FFT_ALLOC_GUARD_H
#define FP_FFT_ALLOC_GUARD_H
#ifndef __ASSEMBLER__
#include <stddef.h>
void *fp_fft_malloc(size_t size);
void fp_fft_free(void *pointer);
#endif
#endif
