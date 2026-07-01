// R04: Unchecked cryptographic return value
// Defect: KEM decapsulation return value is ignored

void handle_key_exchange(void) {
    uint8_t shared_secret[32];
    uint8_t ciphertext[1088];
    uint8_t secret_key[2400];

    // Return value NOT checked - if decaps fails, shared_secret is garbage
    OQS_KEM_decaps(shared_secret, ciphertext, secret_key);

    // Use shared_secret without knowing if it's valid
    derive_session_key(shared_secret);
}