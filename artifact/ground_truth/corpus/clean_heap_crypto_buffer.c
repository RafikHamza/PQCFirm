#include <stdint.h>
#include <stdlib.h>
void *f(size_t required) { if (required > 1000000) return 0; return malloc(required); }
