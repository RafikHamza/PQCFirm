// R07: Return-path validation violation
// Defect: Crypto return value captured and returned directly without check

int handle_crypto_operation(void) {
    uint8_t ss[32], ct[1088], sk[2400];

    // Capture return value from cryptographic operation
    int ret = OQS_KEM_decaps(ss, ct, sk);

    // Return it directly without any validation check!
    // Should check ret != 0 before returning
    return ret;
}