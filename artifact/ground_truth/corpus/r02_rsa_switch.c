#include <stdint.h>
#define KEX_RSA 1
#define KEX_ECDHE 2
int select_kex(int alg) {
    switch (alg) {
        case KEX_RSA: return setup_rsa();
        case KEX_ECDHE: return setup_ecdhe();
        default: return -1;
    }
}
int setup_rsa(void) { return 0; }
int setup_ecdhe(void) { return 0; }
