#include <stdint.h>
#define TLS_RSA_WITH_AES 1
#define TLS_ECDHE_ECDSA_WITH_AES 2
int select_suite(int suite) {
    switch (suite) {
        case TLS_RSA_WITH_AES: return 1;
        case TLS_ECDHE_ECDSA_WITH_AES: return 1;
        default: return 0;
    }
}
