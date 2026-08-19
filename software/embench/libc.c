/* libc.c — Minimal self-contained libc support for Embench-IoT benchmarks */
#include <stddef.h>
#include <stdint.h>

void *memset(void *s, int c, size_t n) {
    unsigned char *p = (unsigned char *)s;
    unsigned char val = (unsigned char)c;
    size_t i;
    for (i = 0; i < n; i++) {
        p[i] = val;
    }
    return s;
}

void *memcpy(void *dest, const void *src, size_t n) {
    unsigned char *d = (unsigned char *)dest;
    const unsigned char *s = (const unsigned char *)src;
    size_t i;
    for (i = 0; i < n; i++) {
        d[i] = s[i];
    }
    return dest;
}

void *memmove(void *dest, const void *src, size_t n) {
    unsigned char *d = (unsigned char *)dest;
    const unsigned char *s = (const unsigned char *)src;
    size_t i;
    if (d < s) {
        for (i = 0; i < n; i++) {
            d[i] = s[i];
        }
    } else if (d > s) {
        for (i = n; i > 0; i--) {
            d[i - 1] = s[i - 1];
        }
    }
    return dest;
}

int memcmp(const void *s1, const void *s2, size_t n) {
    const unsigned char *p1 = (const unsigned char *)s1;
    const unsigned char *p2 = (const unsigned char *)s2;
    size_t i;
    for (i = 0; i < n; i++) {
        if (p1[i] != p2[i]) {
            return p1[i] - p2[i];
        }
    }
    return 0;
}

size_t strlen(const char *s) {
    size_t len = 0;
    while (s[len] != '\0') {
        len++;
    }
    return len;
}

char *strcpy(char *dest, const char *src) {
    char *d = dest;
    while ((*d++ = *src++) != '\0') ;
    return dest;
}

int strcmp(const char *s1, const char *s2) {
    while (*s1 && (*s1 == *s2)) {
        s1++;
        s2++;
    }
    return *(const unsigned char *)s1 - *(const unsigned char *)s2;
}

int strncmp(const char *s1, const char *s2, size_t n) {
    size_t i;
    for (i = 0; i < n; i++) {
        if (s1[i] != s2[i] || s1[i] == '\0' || s2[i] == '\0') {
            return (unsigned char)s1[i] - (unsigned char)s2[i];
        }
    }
    return 0;
}

char *strchr(const char *s, int c) {
    while (*s != (char)c) {
        if (!*s++) {
            return NULL;
        }
    }
    return (char *)s;
}

/* ctype table for newlib/slre */
static const char ctype_b[128] = {
    0,0,0,0,0,0,0,0,0,8,8,8,8,8,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    8,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,
    4,4,4,4,4,4,4,4,4,4,16,16,16,16,16,16,
    16,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,1,16,16,16,16,16,
    16,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,
    2,2,2,2,2,2,2,2,2,2,2,16,16,16,16,0
};
const char *_ctype_ = ctype_b;

void exit(int status) {
    (void)status;
    while (1) ;
}

void abort(void) {
    while (1) ;
}

/* Heap bump allocator for benchmarks that use malloc */
static uint8_t heap_mem[256 * 1024] __attribute__((aligned(16)));
static size_t heap_offset = 0;

void *malloc(size_t size) {
    void *ptr;
    size = (size + 15) & ~15; // 16-byte alignment
    if (heap_offset + size > sizeof(heap_mem)) {
        return NULL;
    }
    ptr = &heap_mem[heap_offset];
    heap_offset += size;
    return ptr;
}

void *calloc(size_t nmemb, size_t size) {
    size_t total = nmemb * size;
    void *ptr = malloc(total);
    if (ptr) {
        memset(ptr, 0, total);
    }
    return ptr;
}

void free(void *ptr) {
    (void)ptr;
}

/* Floating point math helpers using bitwise sign clear */
float fabsf(float x) {
    union { float f; uint32_t i; } u;
    u.f = x;
    u.i &= 0x7FFFFFFFUL;
    return u.f;
}

double fabs(double x) {
    union { double d; uint64_t i; } u;
    u.d = x;
    u.i &= 0x7FFFFFFFFFFFFFFFULL;
    return u.d;
}
