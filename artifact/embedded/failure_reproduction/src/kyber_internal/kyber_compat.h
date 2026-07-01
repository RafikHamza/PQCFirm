#ifndef KYBER_COMPAT_H
#define KYBER_COMPAT_H

#include "params.h"
#include "poly.h"
#include "poly_k.h"
#include "polyvec.h"
#include "sampling.h"
#include "symmetric.h"
#include <string.h>

void randombytes(uint8_t *out, size_t outlen);

// Type mappings
#define poly mlk_poly
#define polyvec mlk_polyvec

// Function mappings
#define poly_add mlk_poly_add
#define poly_sub mlk_poly_sub
#define polyvec_add mlk_polyvec_add
#define polyvec_reduce mlk_polyvec_reduce
#define polyvec_invntt_tomont mlk_polyvec_invntt_tomont
#define polyvec_tobytes mlk_polyvec_tobytes
#define polyvec_decompress mlk_polyvec_decompress_du
#define polyvec_ntt mlk_polyvec_ntt
#define polyvec_frombytes mlk_polyvec_frombytes
#define poly_basemul_montgomery mlk_poly_basemul_montgomery
#define polyvec_pointwise_acc_montgomery mlk_polyvec_pointwise_acc_montgomery

// poly_getnoise_eta1 mapping
// For ML-KEM-768, eta1=2. We implement it manually because mlk_poly_getnoise_eta2 is guarded out for K=3.
static inline void poly_getnoise_eta1(mlk_poly *r, const uint8_t seed[MLKEM_SYMBYTES], uint8_t nonce) {
    uint8_t buf[MLKEM_ETA1 * MLKEM_N / 4];
    uint8_t extkey[MLKEM_SYMBYTES + 1];

    memcpy(extkey, seed, MLKEM_SYMBYTES);
    extkey[MLKEM_SYMBYTES] = nonce;
    
    mlk_prf_eta1(buf, extkey);
    mlk_poly_cbd2(r, buf);
}

// poly_uniform mapping
// Wraps mlk_poly_rej_uniform which expects seed || nonce in a buffer.
static inline void poly_uniform(mlk_poly *r, const uint8_t *seed, uint16_t nonce) {
    uint8_t buf[MLKEM_SYMBYTES + 2];
    memcpy(buf, seed, MLKEM_SYMBYTES);
    buf[MLKEM_SYMBYTES] = nonce & 0xFF;
    buf[MLKEM_SYMBYTES+1] = (nonce >> 8) & 0xFF;
    mlk_poly_rej_uniform(r, buf);
}

// Constant mappings
#define KYBER_SYMBYTES MLKEM_SYMBYTES
#define KYBER_POLYVECBYTES MLKEM_POLYVECBYTES
#define KYBER_POLYBYTES MLKEM_POLYBYTES
#define KYBER_K MLKEM_K
#define KYBER_POLYVECCOMPRESSEDBYTES MLKEM_POLYVECCOMPRESSEDBYTES_DU

#define poly_ntt mlk_poly_ntt
#define poly_invntt_tomont mlk_poly_invntt_tomont
#define poly_reduce mlk_poly_reduce
#define poly_tobytes mlk_poly_tobytes
#define poly_frombytes mlk_poly_frombytes
#define poly_tomsg mlk_poly_tomsg
#define poly_decompress mlk_poly_decompress_dv

#include "indcpa.h"
#define indcpa_enc mlk_indcpa_enc

#endif // KYBER_COMPAT_H
