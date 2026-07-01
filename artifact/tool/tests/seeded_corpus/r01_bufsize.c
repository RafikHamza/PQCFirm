// R01: Hardcoded buffer/key size too small for PQC
// Defect: AES_KEY_SIZE = 32 bytes is too small for PQC key material
// In PQC context, buffer needs to hold ML-KEM-768 public key (1184 bytes)

#define AES_KEY_SIZE 32

/* In a PQC migration, this buffer is used to store a public key,
 * but the size is still the classical 32-byte AES key length */
uint8_t public_key[AES_KEY_SIZE];

void init_keys(void) {
    // Using the buffer in a PQC context - buffer too small!
    OQS_KEM_keypair(alg, public_key, secret_key);
}