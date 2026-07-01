#include <stdint.h>
#define KEX_ECDH_P256 10
#define KEX_ECDH_P384 11
int do_kex(int alg) {
    if (alg == KEX_ECDH_P256) return ecdh_p256();
    if (alg == KEX_ECDH_P384) return ecdh_p384();
    return -1;
}
int ecdh_p256(void) { return 0; }
int ecdh_p384(void) { return 0; }
