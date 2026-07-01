#include <stdint.h>
int f(void) { int res = ml_kem_decaps(0, 0, 0); return res; }
int ml_kem_decaps(uint8_t *ss, const uint8_t *ct, const uint8_t *sk) { return -1; }
