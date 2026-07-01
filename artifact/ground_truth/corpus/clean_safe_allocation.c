#include <stdint.h>
#include <stdlib.h>
void *f(size_t key_len, size_t sig_len) { if (key_len > 4096 || sig_len > 4096) return 0; size_t total = key_len; total += sig_len; return malloc(total); }
