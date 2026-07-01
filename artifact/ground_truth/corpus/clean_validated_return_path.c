#include <stdint.h>
int f(uint8_t *pk, uint8_t *sk) { int ret = OQS_KEM_keypair(pk, sk); if (ret != 0) return -1; return 0; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return 0; }
