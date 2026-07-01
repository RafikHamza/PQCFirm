#include <stdint.h>
int f(void) { int status = crypto_sign_signature(0, 0, 0, 0, 0); return status; }
int crypto_sign_signature(uint8_t *s, size_t *sl, const uint8_t *m, size_t ml, const uint8_t *sk) { return -1; }
