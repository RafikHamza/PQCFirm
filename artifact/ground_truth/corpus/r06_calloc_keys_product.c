#include <stdint.h>
#include <stdlib.h>
void *f(size_t n_keys, size_t key_len) { return calloc(n_keys * key_len, 1); }
