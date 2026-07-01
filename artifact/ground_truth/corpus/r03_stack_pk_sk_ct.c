#include <stdint.h>
#define MLKEM_INDCCA_PUBLICKEYBYTES 1184
#define MLKEM_INDCCA_SECRETKEYBYTES 2400
#define MLKEM_INDCCA_CIPHERTEXTBYTES 1088
void kem_task(void) {
    uint8_t pk[MLKEM_INDCCA_PUBLICKEYBYTES];
    uint8_t sk[MLKEM_INDCCA_SECRETKEYBYTES];
    uint8_t ct[MLKEM_INDCCA_CIPHERTEXTBYTES];
    (void)pk; (void)sk; (void)ct;
}
