// R03: Large stack-allocated crypto buffer
// Defect: 8KB buffer on stack in crypto context, exceeds typical FreeRTOS task stack

void process_crypto(void) {
    uint8_t crypto_stack_buf[8192];
    // Using this buffer for ML-KEM operations
    OQS_KEM_encaps(ct, ss, pk, crypto_stack_buf);
}
