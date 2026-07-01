#!/usr/bin/env python3
"""Generate the PQCFirm curated rule-sensitivity corpus.

The corpus is intentionally aligned with the seven rule families implemented by
``artifact/tool/pqcfirm/rules.py``. It is a seeded, controlled rule-sensitivity
check, not a production recall benchmark.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "corpus"
MANIFEST_FILE = ROOT / "ground_truth_manifest.csv"

CASES: list[dict[str, str]] = []

def add(rule: str, case_id: str, desc: str, code: str, expected: bool = True) -> None:
    CASES.append({
        "case_id": case_id,
        "file": f"{case_id}.c",
        "rule": rule,
        "expected_detection": "true" if expected else "false",
        "defect_type": rule.lower() if expected else "none",
        "description": desc,
        "source_type": "seeded_current_rule" if expected else "clean_negative",
        "code": code.strip() + "\n",
    })

# R01: hardcoded small key/certificate/handshake/signature buffers
add("R01", "r01_short_public_key", "Short public-key buffer", r'''
#include <stdint.h>
#define PUBLIC_KEY_BYTES 32
uint8_t public_key[PUBLIC_KEY_BYTES];
''')
add("R01", "r01_short_signature", "Short signature output buffer", r'''
#include <stdint.h>
#define SIGNATURE_BYTES 64
uint8_t signature[SIGNATURE_BYTES];
''')
add("R01", "r01_short_psk", "Short PSK/key storage", r'''
#include <stdint.h>
#define PSK_MAX_LEN 64
uint8_t psk_key[PSK_MAX_LEN];
''')
add("R01", "r01_small_certificate", "Certificate buffer below PQC certificate scale", r'''
#include <stdint.h>
#define CERTIFICATE_BUFFER_SIZE 1024
uint8_t certificate[CERTIFICATE_BUFFER_SIZE];
''')
add("R01", "r01_small_handshake", "Handshake buffer below hybrid/PQC handshake scale", r'''
#include <stdint.h>
#define HANDSHAKE_BUFFER_SIZE 2048
uint8_t handshake_message[HANDSHAKE_BUFFER_SIZE];
''')

# R02: classical-only algorithm selection without PQC cases
add("R02", "r02_ecdsa_if_chain", "Classical signature branch lacks ML-DSA", r'''
#include <stdint.h>
#define ALG_ECDSA_P256 1
#define ALG_ECDSA_P384 2
int verify_sig(int alg) {
    if (alg == ALG_ECDSA_P256) return verify_ecdsa_p256();
    else if (alg == ALG_ECDSA_P384) return verify_ecdsa_p384();
    return -1;
}
int verify_ecdsa_p256(void) { return 0; }
int verify_ecdsa_p384(void) { return 0; }
''')
add("R02", "r02_ecdh_if_chain", "Classical key-exchange branch lacks ML-KEM", r'''
#include <stdint.h>
#define KEX_ECDH_P256 10
#define KEX_ECDH_P384 11
int do_kex(int alg) {
    if (alg == KEX_ECDH_P256) return ecdh_p256();
    if (alg == KEX_ECDH_P384) return ecdh_p384();
    return -1;
}
int ecdh_p256(void) { return 0; }
int ecdh_p384(void) { return 0; }
''')
add("R02", "r02_rsa_switch", "Classical switch lacks PQC branch", r'''
#include <stdint.h>
#define KEX_RSA 1
#define KEX_ECDHE 2
int select_kex(int alg) {
    switch (alg) {
        case KEX_RSA: return setup_rsa();
        case KEX_ECDHE: return setup_ecdhe();
        default: return -1;
    }
}
int setup_rsa(void) { return 0; }
int setup_ecdhe(void) { return 0; }
''')
add("R02", "r02_cipher_suite_switch", "Classical TLS ciphersuite switch", r'''
#include <stdint.h>
#define TLS_RSA_WITH_AES 1
#define TLS_ECDHE_ECDSA_WITH_AES 2
int select_suite(int suite) {
    switch (suite) {
        case TLS_RSA_WITH_AES: return 1;
        case TLS_ECDHE_ECDSA_WITH_AES: return 1;
        default: return 0;
    }
}
''')
add("R02", "r02_curve_selection", "Curve-only selection lacks PQC option", r'''
#include <stdint.h>
#define CURVE_P256 23
#define CURVE_P384 24
int set_curve(int curve) {
    if (curve == CURVE_P256) return 0;
    else if (curve == CURVE_P384) return 0;
    return -1;
}
''')

# R03: large stack-allocated crypto buffers
add("R03", "r03_stack_pk_sk_ct", "ML-KEM buffers on stack", r'''
#include <stdint.h>
#define MLKEM_INDCCA_PUBLICKEYBYTES 1184
#define MLKEM_INDCCA_SECRETKEYBYTES 2400
#define MLKEM_INDCCA_CIPHERTEXTBYTES 1088
void kem_task(void) {
    uint8_t pk[MLKEM_INDCCA_PUBLICKEYBYTES];
    uint8_t sk[MLKEM_INDCCA_SECRETKEYBYTES];
    uint8_t ct[MLKEM_INDCCA_CIPHERTEXTBYTES];
    (void)pk; (void)sk; (void)ct;
}
''')
add("R03", "r03_stack_signature", "Large signature buffer on stack", r'''
#include <stdint.h>
void sign_task(void) {
    uint8_t signature[3309];
    (void)signature;
}
''')
add("R03", "r03_stack_secret", "Large secret buffer on stack", r'''
#include <stdint.h>
void secret_task(void) {
    uint8_t secret_key[4096];
    (void)secret_key;
}
''')
add("R03", "r03_stack_ciphertext", "Large ciphertext buffer on stack", r'''
#include <stdint.h>
void decaps_task(void) {
    uint8_t ciphertext[1568];
    (void)ciphertext;
}
''')
add("R03", "r03_stack_fallback_key", "Stack fallback after heap failure", r'''
#include <stdint.h>
#include <stdlib.h>
void fallback_task(void) {
    uint8_t fallback_key[4096];
    (void)fallback_key;
}
''')

# R04: discarded status-returning cryptographic calls
add("R04", "r04_unchecked_keypair", "Unchecked keypair result", r'''
#include <stdint.h>
int setup(void) { OQS_KEM_keypair(0, 0); return 0; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return -1; }
''')
add("R04", "r04_unchecked_sign", "Unchecked sign result", r'''
#include <stdint.h>
int do_sign(void) { crypto_sign_signature(0, 0, 0, 0, 0); return 0; }
int crypto_sign_signature(uint8_t *s, size_t *sl, const uint8_t *m, size_t ml, const uint8_t *sk) { return -1; }
''')
add("R04", "r04_unchecked_verify", "Unchecked verify result", r'''
#include <stdint.h>
int do_verify(void) { psa_verify_hash(0, 0, 0, 0, 0, 0); return 0; }
int psa_verify_hash(const uint8_t *pk, size_t pk_len, const uint8_t *m, size_t ml, const uint8_t *s, size_t sl) { return -1; }
''')
add("R04", "r04_unchecked_import", "Unchecked import result", r'''
#include <stdint.h>
int do_import(const uint8_t *key, size_t len) { psa_import_key(key, len); return 0; }
int psa_import_key(const uint8_t *key, size_t len) { return -1; }
''')
add("R04", "r04_unchecked_handshake", "Unchecked handshake step", r'''
#include <stdint.h>
int step(void *ssl) { mbedtls_ssl_handshake_step(ssl); return 0; }
int mbedtls_ssl_handshake_step(void *ssl) { return -1; }
''')

# R05: direct algorithm-specific API calls
add("R05", "r05_direct_kyber_keypair", "Direct Kyber keypair call", r'''
#include <stdint.h>
int f(uint8_t *pk, uint8_t *sk) { return kyber_keypair(pk, sk); }
int kyber_keypair(uint8_t *pk, uint8_t *sk) { return 0; }
''')
add("R05", "r05_direct_dilithium_sign", "Direct Dilithium sign call", r'''
#include <stdint.h>
int f(void) { return dilithium_sign(0, 0, 0, 0, 0); }
int dilithium_sign(uint8_t *s, size_t *sl, const uint8_t *m, size_t ml, const uint8_t *sk) { return 0; }
''')
add("R05", "r05_direct_sphincs_verify", "Direct SPHINCS verify call", r'''
#include <stdint.h>
int f(void) { return sphincs_verify(0, 0, 0, 0); }
int sphincs_verify(const uint8_t *s, size_t sl, const uint8_t *m, size_t ml) { return 0; }
''')
add("R05", "r05_direct_falcon_decaps", "Direct Falcon decapsulation-like call", r'''
#include <stdint.h>
int f(void) { return falcon_decaps(0, 0); }
int falcon_decaps(uint8_t *out, const uint8_t *in) { return 0; }
''')
add("R05", "r05_direct_mceliece_encaps", "Direct McEliece encapsulation call", r'''
#include <stdint.h>
int f(void) { return mceliece_encaps(0, 0, 0); }
int mceliece_encaps(uint8_t *ct, uint8_t *ss, const uint8_t *pk) { return 0; }
''')

# R06: unchecked heap allocation size arithmetic on crypto sizes
add("R06", "r06_malloc_key_sig_sum", "malloc with unchecked key/signature sum", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(size_t key_len, size_t sig_len) { return malloc(key_len + sig_len); }
''')
add("R06", "r06_calloc_keys_product", "calloc with unchecked key product", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(size_t n_keys, size_t key_len) { return calloc(n_keys * key_len, 1); }
''')
add("R06", "r06_realloc_pk_ct_sum", "realloc with unchecked public-key/ciphertext sum", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(void *buf, size_t pk_len, size_t ct_len) { return realloc(buf, pk_len + ct_len); }
''')
add("R06", "r06_pvportmalloc_signature_product", "RTOS allocation with signature product", r'''
#include <stdint.h>
void *pvPortMalloc(size_t n);
void *f(size_t signature_len, size_t batch_count) { return pvPortMalloc(signature_len * batch_count); }
''')
add("R06", "r06_malloc_secret_tag_sum", "malloc with unchecked secret/tag sum", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(size_t secret_len, size_t tag_len) { return malloc(secret_len + tag_len); }
''')

# R07: crypto result captured and returned without validation
add("R07", "r07_return_keypair_status", "Returned keypair status without validation", r'''
#include <stdint.h>
int f(uint8_t *pk, uint8_t *sk) { int ret = OQS_KEM_keypair(pk, sk); return ret; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return -1; }
''')
add("R07", "r07_return_sign_status", "Returned sign status without validation", r'''
#include <stdint.h>
int f(void) { int status = crypto_sign_signature(0, 0, 0, 0, 0); return status; }
int crypto_sign_signature(uint8_t *s, size_t *sl, const uint8_t *m, size_t ml, const uint8_t *sk) { return -1; }
''')
add("R07", "r07_return_verify_status", "Returned verify status without validation", r'''
#include <stdint.h>
int f(void) { int rc = psa_verify_hash(0, 0, 0, 0, 0, 0); return rc; }
int psa_verify_hash(const uint8_t *pk, size_t pk_len, const uint8_t *m, size_t ml, const uint8_t *s, size_t sl) { return -1; }
''')
add("R07", "r07_return_decaps_status", "Returned decapsulation status without validation", r'''
#include <stdint.h>
int f(void) { int res = ml_kem_decaps(0, 0, 0); return res; }
int ml_kem_decaps(uint8_t *ss, const uint8_t *ct, const uint8_t *sk) { return -1; }
''')
add("R07", "r07_return_import_status", "Returned import status without validation", r'''
#include <stdint.h>
int f(const uint8_t *key, size_t len) { int ret = psa_import_key(key, len); return ret; }
int psa_import_key(const uint8_t *key, size_t len) { return -1; }
''')

# Clean negatives
add("R00", "clean_dynamic_buffer", "Clean dynamic buffer management", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(size_t n) { if (n == 0) return 0; return malloc(n); }
''', False)
add("R00", "clean_pqc_algorithm_branch", "Clean selection includes a PQC option", r'''
#define ALG_ECDSA 1
#define ALG_ML_KEM 2
int f(int alg) {
    switch (alg) {
        case ALG_ECDSA: return 1;
        case ALG_ML_KEM: return 1;
        default: return 0;
    }
}
''', False)
add("R00", "clean_heap_crypto_buffer", "Clean heap allocation without unchecked arithmetic", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(size_t required) { if (required > 1000000) return 0; return malloc(required); }
''', False)
add("R00", "clean_checked_return", "Clean checked cryptographic return", r'''
#include <stdint.h>
int f(void) { int ret = OQS_KEM_keypair(0, 0); if (ret != 0) return ret; return 0; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return 0; }
''', False)
add("R00", "clean_generic_api", "Clean generic algorithm API", r'''
#include <stdint.h>
int f(int alg) { return crypto_dispatch(alg); }
int crypto_dispatch(int alg) { return alg; }
''', False)
add("R00", "clean_safe_allocation", "Clean allocation after overflow check", r'''
#include <stdint.h>
#include <stdlib.h>
void *f(size_t key_len, size_t sig_len) { if (key_len > 4096 || sig_len > 4096) return 0; size_t total = key_len; total += sig_len; return malloc(total); }
''', False)
add("R00", "clean_validated_return_path", "Clean return path validates status", r'''
#include <stdint.h>
int f(uint8_t *pk, uint8_t *sk) { int ret = OQS_KEM_keypair(pk, sk); if (ret != 0) return -1; return 0; }
int OQS_KEM_keypair(uint8_t *pk, uint8_t *sk) { return 0; }
''', False)

def generate() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    for old in CORPUS_DIR.glob('*.c'):
        old.unlink()
    fieldnames = ['case_id', 'file', 'rule', 'expected_detection', 'defect_type', 'description', 'source_type']
    rows = []
    for c in CASES:
        (CORPUS_DIR / c['file']).write_text(c['code'], encoding='utf-8')
        rows.append({k: c[k] for k in fieldnames})
        print(f"  Created: {c['file']}")
    with MANIFEST_FILE.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    defective = sum(1 for c in rows if c['expected_detection'] == 'true')
    clean = sum(1 for c in rows if c['expected_detection'] == 'false')
    print(f"\nGenerated {len(rows)} cases ({defective} defective, {clean} clean)")
    print(f"Manifest: {MANIFEST_FILE}")

if __name__ == '__main__':
    generate()
