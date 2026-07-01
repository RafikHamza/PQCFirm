/*
 * VH-ML-KEM Artifact (Anonymous Submission)
 * File: kyber_internal/fips202x4_stub.h
 * Purpose: Minimal FIPS202-x4 API for builds without liboqs.
 *
 * This is a portability shim: implement the small subset of the mlkem-native
 * x4 API using four independent scalar SHAKE instances.
 */

#ifndef VH_FIPS202X4_STUB_H
#define VH_FIPS202X4_STUB_H

#include <stddef.h>
#include <stdint.h>

#include "fips202.h"  // provides OQS_SHA3_* scalar SHAKE + rates

typedef struct {
    shake128incctx s[4];
} mlk_shake128x4ctx;

static inline void mlk_shake128x4_init(mlk_shake128x4ctx *ctx) {
    OQS_SHA3_shake128_inc_init(&ctx->s[0]);
    OQS_SHA3_shake128_inc_init(&ctx->s[1]);
    OQS_SHA3_shake128_inc_init(&ctx->s[2]);
    OQS_SHA3_shake128_inc_init(&ctx->s[3]);
}

static inline void mlk_shake128x4_absorb_once(mlk_shake128x4ctx *ctx,
                                             const uint8_t *in0,
                                             const uint8_t *in1,
                                             const uint8_t *in2,
                                             const uint8_t *in3,
                                             size_t inlen) {
    OQS_SHA3_shake128_inc_ctx_reset(&ctx->s[0]);
    OQS_SHA3_shake128_inc_ctx_reset(&ctx->s[1]);
    OQS_SHA3_shake128_inc_ctx_reset(&ctx->s[2]);
    OQS_SHA3_shake128_inc_ctx_reset(&ctx->s[3]);

    OQS_SHA3_shake128_inc_absorb(&ctx->s[0], in0, inlen);
    OQS_SHA3_shake128_inc_absorb(&ctx->s[1], in1, inlen);
    OQS_SHA3_shake128_inc_absorb(&ctx->s[2], in2, inlen);
    OQS_SHA3_shake128_inc_absorb(&ctx->s[3], in3, inlen);

    OQS_SHA3_shake128_inc_finalize(&ctx->s[0]);
    OQS_SHA3_shake128_inc_finalize(&ctx->s[1]);
    OQS_SHA3_shake128_inc_finalize(&ctx->s[2]);
    OQS_SHA3_shake128_inc_finalize(&ctx->s[3]);
}

static inline void mlk_shake128x4_squeezeblocks(uint8_t *out0,
                                               uint8_t *out1,
                                               uint8_t *out2,
                                               uint8_t *out3,
                                               size_t nblocks,
                                               mlk_shake128x4ctx *ctx) {
    const size_t outlen = nblocks * (size_t)OQS_SHA3_SHAKE128_RATE;
    OQS_SHA3_shake128_inc_squeeze(out0, outlen, &ctx->s[0]);
    OQS_SHA3_shake128_inc_squeeze(out1, outlen, &ctx->s[1]);
    OQS_SHA3_shake128_inc_squeeze(out2, outlen, &ctx->s[2]);
    OQS_SHA3_shake128_inc_squeeze(out3, outlen, &ctx->s[3]);
}

static inline void mlk_shake128x4_release(mlk_shake128x4ctx *ctx) {
    OQS_SHA3_shake128_inc_ctx_release(&ctx->s[0]);
    OQS_SHA3_shake128_inc_ctx_release(&ctx->s[1]);
    OQS_SHA3_shake128_inc_ctx_release(&ctx->s[2]);
    OQS_SHA3_shake128_inc_ctx_release(&ctx->s[3]);
}

static inline void mlk_shake256x4(uint8_t *out0,
                                 uint8_t *out1,
                                 uint8_t *out2,
                                 uint8_t *out3,
                                 size_t outlen,
                                 const uint8_t *in0,
                                 const uint8_t *in1,
                                 const uint8_t *in2,
                                 const uint8_t *in3,
                                 size_t inlen) {
    OQS_SHA3_shake256(out0, outlen, in0, inlen);
    OQS_SHA3_shake256(out1, outlen, in1, inlen);
    OQS_SHA3_shake256(out2, outlen, in2, inlen);
    OQS_SHA3_shake256(out3, outlen, in3, inlen);
}

#endif /* VH_FIPS202X4_STUB_H */
