#include <stdint.h>
int f(uint8_t *pk, uint8_t *sk) { int ret = OQS_KEM_keypair(pk, sk); return ret; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return -1; }
