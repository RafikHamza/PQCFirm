#include "kyber_internal/sha3.h"
#include "kyber_internal/sha3x4.h"
#include <string.h>
#include <stdint.h>

/* Keccak-f[1600] constants */
static const uint64_t KeccakF_RoundConstants[24] = {
    0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808aULL,
    0x8000000080008000ULL, 0x000000000000808bULL, 0x0000000080000001ULL,
    0x8000000080008081ULL, 0x8000000000008009ULL, 0x000000000000008aULL,
    0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000aULL,
    0x000000008000808bULL, 0x800000000000008bULL, 0x8000000000008089ULL,
    0x8000000000008003ULL, 0x8000000000008002ULL, 0x8000000000000080ULL,
    0x000000000000800aULL, 0x800000008000000aULL, 0x8000000080008081ULL,
    0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL
};

#define ROL64(a, offset) ((((uint64_t)a) << offset) ^ (((uint64_t)a) >> (64 - offset)))

static void keccak_f1600_state_permute(uint64_t state[25]) {
    int round;
    uint64_t aba, abe, abi, abo, abu;
    uint64_t aga, age, agi, ago, agu;
    uint64_t aka, ake, aki, ako, aku;
    uint64_t ama, ame, ami, amo, amu;
    uint64_t asa, ase, asi, aso, asu;
    uint64_t bca, bce, bci, bco, bcu;
    uint64_t da, de, di, d_o, du;
    uint64_t eba, ebe, ebi, ebo, ebu;
    uint64_t ega, ege, egi, ego, egu;
    uint64_t eka, eke, eki, eko, eku;
    uint64_t ema, eme, emi, emo, emu;
    uint64_t esa, ese, esi, eso, esu;

    // Copy state to local variables
    aba = state[ 0]; abe = state[ 1]; abi = state[ 2]; abo = state[ 3]; abu = state[ 4];
    aga = state[ 5]; age = state[ 6]; agi = state[ 7]; ago = state[ 8]; agu = state[ 9];
    aka = state[10]; ake = state[11]; aki = state[12]; ako = state[13]; aku = state[14];
    ama = state[15]; ame = state[16]; ami = state[17]; amo = state[18]; amu = state[19];
    asa = state[20]; ase = state[21]; asi = state[22]; aso = state[23]; asu = state[24];

    for (round = 0; round < 24; round += 2) {
        // Round 2*round
        bca = aba^aga^aka^ama^asa;
        bce = abe^age^ake^ame^ase;
        bci = abi^agi^aki^ami^asi;
        bco = abo^ago^ako^amo^aso;
        bcu = abu^agu^aku^amu^asu;

        da = bcu ^ ROL64(bce, 1);
        de = bca ^ ROL64(bci, 1);
        di = bce ^ ROL64(bco, 1);
        d_o = bci ^ ROL64(bcu, 1);
        du = bco ^ ROL64(bca, 1);

        aba ^= da; bca = aba;
        age ^= de; bce = ROL64(age, 44);
        aki ^= di; bci = ROL64(aki, 43);
        amo ^= d_o; bco = ROL64(amo, 21);
        asu ^= du; bcu = ROL64(asu, 14);
        eba = bca ^ ((~bce) & bci);
        eba ^= KeccakF_RoundConstants[round];
        ebe = bce ^ ((~bci) & bco);
        ebi = bci ^ ((~bco) & bcu);
        ebo = bco ^ ((~bcu) & bca);
        ebu = bcu ^ ((~bca) & bce);

        abo ^= d_o; bca = ROL64(abo, 28);
        agu ^= du; bce = ROL64(agu, 20);
        aka ^= da; bci = ROL64(aka, 3);
        ame ^= de; bco = ROL64(ame, 45);
        asi ^= di; bcu = ROL64(asi, 61);
        ega = bca ^ ((~bce) & bci);
        ege = bce ^ ((~bci) & bco);
        egi = bci ^ ((~bco) & bcu);
        ego = bco ^ ((~bcu) & bca);
        egu = bcu ^ ((~bca) & bce);

        abe ^= de; bca = ROL64(abe, 1);
        agi ^= di; bce = ROL64(agi, 6);
        ako ^= d_o; bci = ROL64(ako, 25);
        amu ^= du; bco = ROL64(amu, 8);
        asa ^= da; bcu = ROL64(asa, 18);
        eka = bca ^ ((~bce) & bci);
        eke = bce ^ ((~bci) & bco);
        eki = bci ^ ((~bco) & bcu);
        eko = bco ^ ((~bcu) & bca);
        eku = bcu ^ ((~bca) & bce);

        abu ^= du; bca = ROL64(abu, 27);
        ago ^= d_o; bce = ROL64(ago, 36);
        ake ^= de; bci = ROL64(ake, 10);
        ami ^= di; bco = ROL64(ami, 15);
        aso ^= da; bcu = ROL64(aso, 56);
        ema = bca ^ ((~bce) & bci);
        eme = bce ^ ((~bci) & bco);
        emi = bci ^ ((~bco) & bcu);
        emo = bco ^ ((~bcu) & bca);
        emu = bcu ^ ((~bca) & bce);

        abi ^= di; bca = ROL64(abi, 62);
        aga ^= da; bce = ROL64(aga, 55);
        aku ^= du; bci = ROL64(aku, 39);
        ama ^= d_o; bco = ROL64(ama, 41);
        ase ^= de; bcu = ROL64(ase, 2);
        esa = bca ^ ((~bce) & bci);
        ese = bce ^ ((~bci) & bco);
        esi = bci ^ ((~bco) & bcu);
        eso = bco ^ ((~bcu) & bca);
        esu = bcu ^ ((~bca) & bce);

        // Round 2*round + 1
        bca = eba^ega^eka^ema^esa;
        bce = ebe^ege^eke^eme^ese;
        bci = ebi^egi^eki^emi^esi;
        bco = ebo^ego^eko^emo^eso;
        bcu = ebu^egu^eku^emu^esu;

        da = bcu ^ ROL64(bce, 1);
        de = bca ^ ROL64(bci, 1);
        di = bce ^ ROL64(bco, 1);
        d_o = bci ^ ROL64(bcu, 1);
        du = bco ^ ROL64(bca, 1);

        eba ^= da; bca = eba;
        ege ^= de; bce = ROL64(ege, 44);
        eki ^= di; bci = ROL64(eki, 43);
        emo ^= d_o; bco = ROL64(emo, 21);
        esu ^= du; bcu = ROL64(esu, 14);
        aba = bca ^ ((~bce) & bci);
        aba ^= KeccakF_RoundConstants[round+1];
        abe = bce ^ ((~bci) & bco);
        abi = bci ^ ((~bco) & bcu);
        abo = bco ^ ((~bcu) & bca);
        abu = bcu ^ ((~bca) & bce);

        ebo ^= d_o; bca = ROL64(ebo, 28);
        egu ^= du; bce = ROL64(egu, 20);
        eka ^= da; bci = ROL64(eka, 3);
        eme ^= de; bco = ROL64(eme, 45);
        esi ^= di; bcu = ROL64(esi, 61);
        aga = bca ^ ((~bce) & bci);
        age = bce ^ ((~bci) & bco);
        agi = bci ^ ((~bco) & bcu);
        ago = bco ^ ((~bcu) & bca);
        agu = bcu ^ ((~bca) & bce);

        ebe ^= de; bca = ROL64(ebe, 1);
        egi ^= di; bce = ROL64(egi, 6);
        eko ^= d_o; bci = ROL64(eko, 25);
        emu ^= du; bco = ROL64(emu, 8);
        esa ^= da; bcu = ROL64(esa, 18);
        aka = bca ^ ((~bce) & bci);
        ake = bce ^ ((~bci) & bco);
        aki = bci ^ ((~bco) & bcu);
        ako = bco ^ ((~bcu) & bca);
        aku = bcu ^ ((~bca) & bce);

        ebu ^= du; bca = ROL64(ebu, 27);
        ego ^= d_o; bce = ROL64(ego, 36);
        eke ^= de; bci = ROL64(eke, 10);
        emi ^= di; bco = ROL64(emi, 15);
        eso ^= da; bcu = ROL64(eso, 56);
        ama = bca ^ ((~bce) & bci);
        ame = bce ^ ((~bci) & bco);
        ami = bci ^ ((~bco) & bcu);
        amo = bco ^ ((~bcu) & bca);
        amu = bcu ^ ((~bca) & bce);

        ebi ^= di; bca = ROL64(ebi, 62);
        ega ^= da; bce = ROL64(ega, 55);
        eku ^= du; bci = ROL64(eku, 39);
        ema ^= d_o; bco = ROL64(ema, 41);
        ese ^= de; bcu = ROL64(ese, 2);
        asa = bca ^ ((~bce) & bci);
        ase = bce ^ ((~bci) & bco);
        asi = bci ^ ((~bco) & bcu);
        aso = bco ^ ((~bcu) & bca);
        asu = bcu ^ ((~bca) & bce);
    }

    state[ 0] = aba; state[ 1] = abe; state[ 2] = abi; state[ 3] = abo; state[ 4] = abu;
    state[ 5] = aga; state[ 6] = age; state[ 7] = agi; state[ 8] = ago; state[ 9] = agu;
    state[10] = aka; state[11] = ake; state[12] = aki; state[13] = ako; state[14] = aku;
    state[15] = ama; state[16] = ame; state[17] = ami; state[18] = amo; state[19] = amu;
    state[20] = asa; state[21] = ase; state[22] = asi; state[23] = aso; state[24] = asu;
}

/* Helper functions */
static void keccak_inc_init(uint64_t *s, int *p) {
    memset(s, 0, 25 * sizeof(uint64_t));
    *p = 0;
}

static void keccak_inc_absorb(uint64_t *s, int *p, unsigned int r, const uint8_t *in, size_t inlen) {
    size_t i;
    while (inlen > 0) {
        if (*p == 0 && inlen >= r) {
            // Fast path
            for (i = 0; i < r / 8; i++) {
                s[i] ^= ((uint64_t *)in)[i];
            }
            in += r;
            inlen -= r;
            keccak_f1600_state_permute(s);
        } else {
            size_t len = r - *p;
            if (len > inlen) len = inlen;
            for (i = 0; i < len; i++) {
                ((uint8_t *)s)[*p + i] ^= in[i];
            }
            *p += len;
            in += len;
            inlen -= len;
            if ((unsigned int)*p == r) {
                keccak_f1600_state_permute(s);
                *p = 0;
            }
        }
    }
}

static void keccak_inc_finalize(uint64_t *s, int *p, unsigned int r, uint8_t domain) {
    ((uint8_t *)s)[*p] ^= domain;
    ((uint8_t *)s)[r - 1] ^= 0x80;
    keccak_f1600_state_permute(s);
    *p = 0;
}

static void keccak_inc_squeeze(uint64_t *s, int *p, unsigned int r, uint8_t *out, size_t outlen) {
    size_t i;
    while (outlen > 0) {
        size_t len = r - *p;
        if (len > outlen) len = outlen;
        for (i = 0; i < len; i++) {
            out[i] = ((uint8_t *)s)[*p + i];
        }
        *p += len;
        out += len;
        outlen -= len;
        if ((unsigned int)*p == r) {
            keccak_f1600_state_permute(s);
            *p = 0;
        }
    }
}

/* SHA3-256 */
void OQS_SHA3_sha3_256_inc_init(OQS_SHA3_sha3_256_inc_ctx *state) {
    keccak_inc_init(state->s, &state->p);
}

void OQS_SHA3_sha3_256_inc_absorb(OQS_SHA3_sha3_256_inc_ctx *state, const uint8_t *input, size_t inlen) {
    keccak_inc_absorb(state->s, &state->p, OQS_SHA3_SHA3_256_RATE, input, inlen);
}

void OQS_SHA3_sha3_256_inc_finalize(uint8_t *output, OQS_SHA3_sha3_256_inc_ctx *state) {
    keccak_inc_finalize(state->s, &state->p, OQS_SHA3_SHA3_256_RATE, 0x06);
    keccak_inc_squeeze(state->s, &state->p, OQS_SHA3_SHA3_256_RATE, output, 32);
}

void OQS_SHA3_sha3_256_inc_ctx_release(OQS_SHA3_sha3_256_inc_ctx *state) {
    (void)state;
}

void OQS_SHA3_sha3_256(uint8_t *output, const uint8_t *input, size_t inplen) {
    OQS_SHA3_sha3_256_inc_ctx ctx;
    OQS_SHA3_sha3_256_inc_init(&ctx);
    OQS_SHA3_sha3_256_inc_absorb(&ctx, input, inplen);
    OQS_SHA3_sha3_256_inc_finalize(output, &ctx);
}

/* SHA3-512 */
#define OQS_SHA3_SHA3_512_RATE 72
void OQS_SHA3_sha3_512_inc_init(OQS_SHA3_sha3_512_inc_ctx *state) {
    keccak_inc_init(state->s, &state->p);
}
void OQS_SHA3_sha3_512_inc_absorb(OQS_SHA3_sha3_512_inc_ctx *state, const uint8_t *input, size_t inlen) {
    keccak_inc_absorb(state->s, &state->p, OQS_SHA3_SHA3_512_RATE, input, inlen);
}
void OQS_SHA3_sha3_512_inc_finalize(uint8_t *output, OQS_SHA3_sha3_512_inc_ctx *state) {
    keccak_inc_finalize(state->s, &state->p, OQS_SHA3_SHA3_512_RATE, 0x06);
    keccak_inc_squeeze(state->s, &state->p, OQS_SHA3_SHA3_512_RATE, output, 64);
}
void OQS_SHA3_sha3_512_inc_ctx_release(OQS_SHA3_sha3_512_inc_ctx *state) { (void)state; }
void OQS_SHA3_sha3_512(uint8_t *output, const uint8_t *input, size_t inplen) {
    OQS_SHA3_sha3_512_inc_ctx ctx;
    OQS_SHA3_sha3_512_inc_init(&ctx);
    OQS_SHA3_sha3_512_inc_absorb(&ctx, input, inplen);
    OQS_SHA3_sha3_512_inc_finalize(output, &ctx);
}

/* SHAKE128 */
#define OQS_SHA3_SHAKE128_RATE 168
void OQS_SHA3_shake128_inc_init(OQS_SHA3_shake128_inc_ctx *state) {
    keccak_inc_init(state->s, &state->p);
}
void OQS_SHA3_shake128_inc_absorb(OQS_SHA3_shake128_inc_ctx *state, const uint8_t *input, size_t inlen) {
    keccak_inc_absorb(state->s, &state->p, OQS_SHA3_SHAKE128_RATE, input, inlen);
}
void OQS_SHA3_shake128_inc_finalize(OQS_SHA3_shake128_inc_ctx *state) {
    keccak_inc_finalize(state->s, &state->p, OQS_SHA3_SHAKE128_RATE, 0x1F);
}
void OQS_SHA3_shake128_inc_squeeze(uint8_t *output, size_t outlen, OQS_SHA3_shake128_inc_ctx *state) {
    keccak_inc_squeeze(state->s, &state->p, OQS_SHA3_SHAKE128_RATE, output, outlen);
}
void OQS_SHA3_shake128_inc_ctx_release(OQS_SHA3_shake128_inc_ctx *state) { (void)state; }
void OQS_SHA3_shake128_inc_ctx_reset(OQS_SHA3_shake128_inc_ctx *state) {
    keccak_inc_init(state->s, &state->p);
}
void OQS_SHA3_shake128_inc_ctx_clone(OQS_SHA3_shake128_inc_ctx *dest, const OQS_SHA3_shake128_inc_ctx *src) {
    *dest = *src;
}

void OQS_SHA3_shake128(uint8_t *output, size_t outlen, const uint8_t *input, size_t inlen) {
    OQS_SHA3_shake128_inc_ctx ctx;
    OQS_SHA3_shake128_inc_init(&ctx);
    OQS_SHA3_shake128_inc_absorb(&ctx, input, inlen);
    OQS_SHA3_shake128_inc_finalize(&ctx);
    OQS_SHA3_shake128_inc_squeeze(output, outlen, &ctx);
}

/* SHAKE256 */
#define OQS_SHA3_SHAKE256_RATE 136
void OQS_SHA3_shake256_inc_init(OQS_SHA3_shake256_inc_ctx *state) {
    keccak_inc_init(state->s, &state->p);
}
void OQS_SHA3_shake256_inc_absorb(OQS_SHA3_shake256_inc_ctx *state, const uint8_t *input, size_t inlen) {
    keccak_inc_absorb(state->s, &state->p, OQS_SHA3_SHAKE256_RATE, input, inlen);
}
void OQS_SHA3_shake256_inc_finalize(OQS_SHA3_shake256_inc_ctx *state) {
    keccak_inc_finalize(state->s, &state->p, OQS_SHA3_SHAKE256_RATE, 0x1F);
}
void OQS_SHA3_shake256_inc_squeeze(uint8_t *output, size_t outlen, OQS_SHA3_shake256_inc_ctx *state) {
    keccak_inc_squeeze(state->s, &state->p, OQS_SHA3_SHAKE256_RATE, output, outlen);
}
void OQS_SHA3_shake256_inc_ctx_release(OQS_SHA3_shake256_inc_ctx *state) { (void)state; }
void OQS_SHA3_shake256_inc_ctx_reset(OQS_SHA3_shake256_inc_ctx *state) {
    keccak_inc_init(state->s, &state->p);
}
void OQS_SHA3_shake256_inc_ctx_clone(OQS_SHA3_shake256_inc_ctx *dest, const OQS_SHA3_shake256_inc_ctx *src) {
    *dest = *src;
}

void OQS_SHA3_shake256(uint8_t *output, size_t outlen, const uint8_t *input, size_t inlen) {
    OQS_SHA3_shake256_inc_ctx ctx;
    OQS_SHA3_shake256_inc_init(&ctx);
    OQS_SHA3_shake256_inc_absorb(&ctx, input, inlen);
    OQS_SHA3_shake256_inc_finalize(&ctx);
    OQS_SHA3_shake256_inc_squeeze(output, outlen, &ctx);
}

/* SHAKE128 x4 */
void OQS_SHA3_shake128_x4_inc_init(OQS_SHA3_shake128_x4_inc_ctx *state) {
    for (int i = 0; i < 4; i++) {
        memset(state->s[i], 0, 25 * sizeof(uint64_t));
    }
    state->p = 0;
}

void OQS_SHA3_shake128_x4_inc_absorb(OQS_SHA3_shake128_x4_inc_ctx *state, const uint8_t *in0, const uint8_t *in1, const uint8_t *in2, const uint8_t *in3, size_t inlen) {
    int p = state->p;
    keccak_inc_absorb(state->s[0], &p, OQS_SHA3_SHAKE128_RATE, in0, inlen);
    p = state->p;
    keccak_inc_absorb(state->s[1], &p, OQS_SHA3_SHAKE128_RATE, in1, inlen);
    p = state->p;
    keccak_inc_absorb(state->s[2], &p, OQS_SHA3_SHAKE128_RATE, in2, inlen);
    p = state->p;
    keccak_inc_absorb(state->s[3], &p, OQS_SHA3_SHAKE128_RATE, in3, inlen);
    state->p = p;
}

void OQS_SHA3_shake128_x4_inc_finalize(OQS_SHA3_shake128_x4_inc_ctx *state) {
    int p = state->p;
    keccak_inc_finalize(state->s[0], &p, OQS_SHA3_SHAKE128_RATE, 0x1F);
    p = state->p;
    keccak_inc_finalize(state->s[1], &p, OQS_SHA3_SHAKE128_RATE, 0x1F);
    p = state->p;
    keccak_inc_finalize(state->s[2], &p, OQS_SHA3_SHAKE128_RATE, 0x1F);
    p = state->p;
    keccak_inc_finalize(state->s[3], &p, OQS_SHA3_SHAKE128_RATE, 0x1F);
    state->p = p;
}

void OQS_SHA3_shake128_x4_inc_squeeze(uint8_t *out0, uint8_t *out1, uint8_t *out2, uint8_t *out3, size_t outlen, OQS_SHA3_shake128_x4_inc_ctx *state) {
    int p = state->p;
    keccak_inc_squeeze(state->s[0], &p, OQS_SHA3_SHAKE128_RATE, out0, outlen);
    p = state->p;
    keccak_inc_squeeze(state->s[1], &p, OQS_SHA3_SHAKE128_RATE, out1, outlen);
    p = state->p;
    keccak_inc_squeeze(state->s[2], &p, OQS_SHA3_SHAKE128_RATE, out2, outlen);
    p = state->p;
    keccak_inc_squeeze(state->s[3], &p, OQS_SHA3_SHAKE128_RATE, out3, outlen);
    state->p = p;
}

void OQS_SHA3_shake128_x4_inc_ctx_release(OQS_SHA3_shake128_x4_inc_ctx *state) { (void)state; }
void OQS_SHA3_shake128_x4_inc_ctx_reset(OQS_SHA3_shake128_x4_inc_ctx *state) {
    OQS_SHA3_shake128_x4_inc_init(state);
}
void OQS_SHA3_shake128_x4_inc_ctx_clone(OQS_SHA3_shake128_x4_inc_ctx *dest, const OQS_SHA3_shake128_x4_inc_ctx *src) {
    *dest = *src;
}

void OQS_SHA3_shake128_x4(uint8_t *out0, uint8_t *out1, uint8_t *out2, uint8_t *out3, size_t outlen, const uint8_t *in0, const uint8_t *in1, const uint8_t *in2, const uint8_t *in3, size_t inlen) {
    OQS_SHA3_shake128_x4_inc_ctx ctx;
    OQS_SHA3_shake128_x4_inc_init(&ctx);
    OQS_SHA3_shake128_x4_inc_absorb(&ctx, in0, in1, in2, in3, inlen);
    OQS_SHA3_shake128_x4_inc_finalize(&ctx);
    OQS_SHA3_shake128_x4_inc_squeeze(out0, out1, out2, out3, outlen, &ctx);
}

/* SHAKE256 x4 */
void OQS_SHA3_shake256_x4_inc_init(OQS_SHA3_shake256_x4_inc_ctx *state) {
    for (int i = 0; i < 4; i++) {
        memset(state->s[i], 0, 25 * sizeof(uint64_t));
    }
    state->p = 0;
}

void OQS_SHA3_shake256_x4_inc_absorb(OQS_SHA3_shake256_x4_inc_ctx *state, const uint8_t *in0, const uint8_t *in1, const uint8_t *in2, const uint8_t *in3, size_t inlen) {
    int p = state->p;
    keccak_inc_absorb(state->s[0], &p, OQS_SHA3_SHAKE256_RATE, in0, inlen);
    p = state->p;
    keccak_inc_absorb(state->s[1], &p, OQS_SHA3_SHAKE256_RATE, in1, inlen);
    p = state->p;
    keccak_inc_absorb(state->s[2], &p, OQS_SHA3_SHAKE256_RATE, in2, inlen);
    p = state->p;
    keccak_inc_absorb(state->s[3], &p, OQS_SHA3_SHAKE256_RATE, in3, inlen);
    state->p = p;
}

void OQS_SHA3_shake256_x4_inc_finalize(OQS_SHA3_shake256_x4_inc_ctx *state) {
    int p = state->p;
    keccak_inc_finalize(state->s[0], &p, OQS_SHA3_SHAKE256_RATE, 0x1F);
    p = state->p;
    keccak_inc_finalize(state->s[1], &p, OQS_SHA3_SHAKE256_RATE, 0x1F);
    p = state->p;
    keccak_inc_finalize(state->s[2], &p, OQS_SHA3_SHAKE256_RATE, 0x1F);
    p = state->p;
    keccak_inc_finalize(state->s[3], &p, OQS_SHA3_SHAKE256_RATE, 0x1F);
    state->p = p;
}

void OQS_SHA3_shake256_x4_inc_squeeze(uint8_t *out0, uint8_t *out1, uint8_t *out2, uint8_t *out3, size_t outlen, OQS_SHA3_shake256_x4_inc_ctx *state) {
    int p = state->p;
    keccak_inc_squeeze(state->s[0], &p, OQS_SHA3_SHAKE256_RATE, out0, outlen);
    p = state->p;
    keccak_inc_squeeze(state->s[1], &p, OQS_SHA3_SHAKE256_RATE, out1, outlen);
    p = state->p;
    keccak_inc_squeeze(state->s[2], &p, OQS_SHA3_SHAKE256_RATE, out2, outlen);
    p = state->p;
    keccak_inc_squeeze(state->s[3], &p, OQS_SHA3_SHAKE256_RATE, out3, outlen);
    state->p = p;
}

void OQS_SHA3_shake256_x4_inc_ctx_release(OQS_SHA3_shake256_x4_inc_ctx *state) { (void)state; }
void OQS_SHA3_shake256_x4_inc_ctx_reset(OQS_SHA3_shake256_x4_inc_ctx *state) {
    OQS_SHA3_shake256_x4_inc_init(state);
}
void OQS_SHA3_shake256_x4_inc_ctx_clone(OQS_SHA3_shake256_x4_inc_ctx *dest, const OQS_SHA3_shake256_x4_inc_ctx *src) {
    *dest = *src;
}

void OQS_SHA3_shake256_x4(uint8_t *out0, uint8_t *out1, uint8_t *out2, uint8_t *out3, size_t outlen, const uint8_t *in0, const uint8_t *in1, const uint8_t *in2, const uint8_t *in3, size_t inlen) {
    OQS_SHA3_shake256_x4_inc_ctx ctx;
    OQS_SHA3_shake256_x4_inc_init(&ctx);
    OQS_SHA3_shake256_x4_inc_absorb(&ctx, in0, in1, in2, in3, inlen);
    OQS_SHA3_shake256_x4_inc_finalize(&ctx);
    OQS_SHA3_shake256_x4_inc_squeeze(out0, out1, out2, out3, outlen, &ctx);
}
