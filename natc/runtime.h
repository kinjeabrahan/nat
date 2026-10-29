#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>

static _Noreturn inline void nat_fail(int line, int column, const char *message) {
    fprintf(stderr, "%s:%d:%d: %s\n", nat_source, line, column, message);
    exit(1);
}
static inline int64_t nat_add(int64_t a, int64_t b, int l, int c) {
    int64_t r;
    if (__builtin_add_overflow(a,b,&r)) nat_fail(l,c,"Desbordamiento Int64.");
    return r;
}
static inline int64_t nat_sub(int64_t a, int64_t b, int l, int c) {
    int64_t r;
    if (__builtin_sub_overflow(a,b,&r)) nat_fail(l,c,"Desbordamiento Int64.");
    return r;
}
static inline int64_t nat_mul(int64_t a, int64_t b, int l, int c) {
    int64_t r;
    if (__builtin_mul_overflow(a,b,&r)) nat_fail(l,c,"Desbordamiento Int64.");
    return r;
}
static inline int64_t nat_mod(int64_t a, int64_t b, int l, int c) {
    if (!b) nat_fail(l,c,"Resto por cero.");
    if (a == INT64_MIN && b == -1) return 0;
    return a % b;
}
static inline int64_t nat_input(int argc, char **argv, int l, int c) {
    if (argc != 2) nat_fail(l,c,"Se requiere un argumento entero decimal.");
    const char *p = argv[1];
    if (*p == '-') p++;
    if (!*p) nat_fail(l,c,"Entrada Int64 no valida.");
    for (; *p; p++) if (*p < '0' || *p > '9') nat_fail(l,c,"Entrada Int64 no valida.");
    errno = 0;
    char *end;
    intmax_t r = strtoimax(argv[1], &end, 10);
    if (errno == ERANGE || *end || r < INT64_MIN || r > INT64_MAX)
        nat_fail(l,c,"Entrada fuera de Int64.");
    return (int64_t)r;
}

static int nat_argc;
static char **nat_argv;
static unsigned nat_depth;
static inline void nat_enter(int l, int c) {
    if (++nat_depth > 128) nat_fail(l,c,"Limite de llamadas alcanzado (128).");
}
static inline int64_t nat_read_byte(int l, int c) {
    int b = getchar();
    if (b == EOF && ferror(stdin)) nat_fail(l,c,"Error de lectura de entrada.");
    return b == EOF ? INT64_C(-1) : (int64_t)(unsigned char)b;
}
