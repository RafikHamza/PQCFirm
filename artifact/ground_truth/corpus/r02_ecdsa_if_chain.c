#include <stdint.h>
#define ALG_ECDSA_P256 1
#define ALG_ECDSA_P384 2
int verify_sig(int alg) {
    if (alg == ALG_ECDSA_P256) return verify_ecdsa_p256();
    else if (alg == ALG_ECDSA_P384) return verify_ecdsa_p384();
    return -1;
}
int verify_ecdsa_p256(void) { return 0; }
int verify_ecdsa_p384(void) { return 0; }
