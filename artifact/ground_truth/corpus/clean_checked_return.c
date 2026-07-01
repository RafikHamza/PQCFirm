#include <stdint.h>
int f(void) { int ret = OQS_KEM_keypair(0, 0); if (ret != 0) return ret; return 0; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return 0; }
