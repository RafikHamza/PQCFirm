// R06: Unsafe heap allocation using key-size arithmetic without overflow check
// Defect: malloc(pk_len + sk_len) could overflow if sizes are large (PQC keys)

#include <stdlib.h>

void unsafe_key_allocation(void) {
    size_t pk_len = 1184;  // ML-KEM-768 public key size
    size_t sk_len = 2400;  // ML-KEM-768 secret key size

    // Integer overflow possible: pk_len + sk_len could wrap around
    uint8_t *key_material = (uint8_t *)malloc(pk_len + sk_len);

    // Using the allocated buffer for PQC key operations
    memcpy(key_material, public_key, pk_len);
    memcpy(key_material + pk_len, secret_key, sk_len);
}