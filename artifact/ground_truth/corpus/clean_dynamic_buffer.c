#include <stdint.h>
#include <stdlib.h>
void *f(size_t n) { if (n == 0) return 0; return malloc(n); }
