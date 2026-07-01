#include <stdint.h>
#include <stdlib.h>
void *f(size_t secret_len, size_t tag_len) { return malloc(secret_len + tag_len); }
