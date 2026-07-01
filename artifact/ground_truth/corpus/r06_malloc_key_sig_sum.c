#include <stdint.h>
#include <stdlib.h>
void *f(size_t key_len, size_t sig_len) { return malloc(key_len + sig_len); }
