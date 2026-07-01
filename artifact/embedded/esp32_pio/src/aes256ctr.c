#include "aes256ctr.h"
#include "dilithium_internal/config.h"
#include <stdlib.h>
#include <string.h>
#include "mbedtls/aes.h"

#define dilithium_aes256ctr_init DILITHIUM_NAMESPACE(dilithium_aes256ctr_init)

static void aes256ctr_increment_counter(uint8_t counter[AES256CTR_BLOCKBYTES]) {
    for (int i = AES256CTR_BLOCKBYTES - 1; i >= 0; i--) {
        if (++counter[i] != 0) {
            break;
        }
    }
}

void dilithium_aes256ctr_init(aes256ctr_ctx *state, const uint8_t key[32], uint16_t nonce) {
    mbedtls_aes_context *aes = (mbedtls_aes_context *)malloc(sizeof(mbedtls_aes_context));
    if (!aes) {
        state->aes_ctx = NULL;
        return;
    }
    mbedtls_aes_init(aes);
    mbedtls_aes_setkey_enc(aes, key, 256);
    state->aes_ctx = aes;
    memset(state->buffer, 0, AES256CTR_BLOCKBYTES);
    state->idx = 0;
    memset(state->counter, 0, AES256CTR_BLOCKBYTES);
    state->counter[14] = (uint8_t)(nonce & 0xff);
    state->counter[15] = (uint8_t)(nonce >> 8);
}

void aes256ctr_squeezeblocks(uint8_t *out, size_t nblocks, aes256ctr_ctx *state) {
    if (!state->aes_ctx) {
        return;
    }
    mbedtls_aes_context *aes = (mbedtls_aes_context *)state->aes_ctx;
    for (size_t i = 0; i < nblocks; i++) {
        mbedtls_aes_crypt_ecb(aes, MBEDTLS_AES_ENCRYPT, state->counter, state->buffer);
        memcpy(out + i * AES256CTR_BLOCKBYTES, state->buffer, AES256CTR_BLOCKBYTES);
        aes256ctr_increment_counter(state->counter);
    }
}

void aes256_ctx_release(aes256ctr_ctx *state) {
    if (!state->aes_ctx) {
        return;
    }
    mbedtls_aes_context *aes = (mbedtls_aes_context *)state->aes_ctx;
    mbedtls_aes_free(aes);
    free(aes);
    state->aes_ctx = NULL;
    memset(state->counter, 0, AES256CTR_BLOCKBYTES);
    memset(state->buffer, 0, AES256CTR_BLOCKBYTES);
    state->idx = 0;
}
