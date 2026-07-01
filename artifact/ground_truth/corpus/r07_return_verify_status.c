#include <stdint.h>
int f(void) { int rc = psa_verify_hash(0, 0, 0, 0, 0, 0); return rc; }
int psa_verify_hash(const uint8_t *pk, size_t pk_len, const uint8_t *m, size_t ml, const uint8_t *s, size_t sl) { return -1; }
