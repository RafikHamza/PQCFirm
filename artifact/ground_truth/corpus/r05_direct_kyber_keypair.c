#include <stdint.h>
int f(uint8_t *pk, uint8_t *sk) { return kyber_keypair(pk, sk); }
int kyber_keypair(uint8_t *pk, uint8_t *sk) { return 0; }
