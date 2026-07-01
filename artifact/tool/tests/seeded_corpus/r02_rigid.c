// R02: Rigid algorithm selection without PQC branches
// Defect: switch statement selects only classical algorithms, no PQC cases

void select_cipher(int algo) {
    switch (algo) {
        case 0:  // AES-128
            aes128_init();
            break;
        case 1:  // AES-256
            aes256_init();
            break;
        case 2:  // ChaCha20
            chacha20_init();
            break;
        // Missing: ML-KEM, ML-DSA, or any PQC algorithm case
    }
}