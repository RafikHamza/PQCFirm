// R05: Algorithm-specific API usage instead of generic crypto-agile interface
// Defect: Direct call to kyber-specific KEM function, not generic OQS_KEM_decaps

void perform_kem(void) {
    uint8_t ss[32], ct[1088], sk[2400];

    // Using algorithm-specific API - not crypto-agile
    // Should use generic OQS_KEM_decaps() with algorithm parameter
    OQS_KEM_kyber_768_decaps(ss, ct, sk);
}