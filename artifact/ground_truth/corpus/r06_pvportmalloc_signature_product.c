#include <stdint.h>
void *pvPortMalloc(size_t n);
void *f(size_t signature_len, size_t batch_count) { return pvPortMalloc(signature_len * batch_count); }
