#ifndef AES256CTR_H
#define AES256CTR_H

#include <stddef.h>
#include <stdint.h>

#define AES256CTR_BLOCKBYTES 16

typedef struct {
    void *aes_ctx;
    uint8_t counter[AES256CTR_BLOCKBYTES];
    uint8_t buffer[AES256CTR_BLOCKBYTES];
    size_t idx;
} aes256ctr_ctx;

void aes256ctr_init(aes256ctr_ctx *state, const uint8_t key[32], uint16_t nonce);
void aes256ctr_squeezeblocks(uint8_t *out, size_t nblocks, aes256ctr_ctx *state);
void aes256_ctx_release(aes256ctr_ctx *state);

#endif
