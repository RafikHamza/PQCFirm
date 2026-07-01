#include <stdint.h>
#include <stdlib.h>
void *f(void *buf, size_t pk_len, size_t ct_len) { return realloc(buf, pk_len + ct_len); }
