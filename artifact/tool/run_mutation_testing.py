import os
import sys
import shutil
import json

# Add tool directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tool.pqcfirm.scanner import Scanner

# Define the path to main.cpp relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
MAIN_CPP_PATH = os.path.abspath(os.path.join(script_dir, "..", "embedded", "esp32_pio", "src", "main.cpp"))
TEMP_CPP_PATH = os.path.abspath(os.path.join(script_dir, "..", "embedded", "esp32_pio", "src", "main_mutated.cpp"))

# Mutation definitions
# Each mutation is a dict containing:
# - 'name': Description of the mutant
# - 'rule': Expected rule ID to trigger
# - 'target': Substring to replace in main.cpp
# - 'replacement': Substring to replace it with
MUTATIONS = [
    # --- R04: Unchecked Return Values (13 Mutants) ---
    {
        "name": "R04 mutant 1: unchecked keypair in setup",
        "rule": "R04",
        "target": "int ret = crypto_kem_keypair(pk, sk);",
        "replacement": "crypto_kem_keypair(pk, sk);"
    },
    {
        "name": "R04 mutant 2: unchecked enc in setup",
        "rule": "R04",
        "target": "ret = crypto_kem_enc(ct, ss, pk) || ret;",
        "replacement": "crypto_kem_enc(ct, ss, pk);"
    },
    {
        "name": "R04 mutant 3: unchecked dec in setup",
        "rule": "R04",
        "target": "ret = crypto_kem_dec(ss2, ct, sk) || ret;",
        "replacement": "crypto_kem_dec(ss2, ct, sk);"
    },
    {
        "name": "R04 mutant 4: unchecked ECDSA keygen",
        "rule": "R04",
        "target": "int ret = mbedtls_ecdsa_genkey(ctx, grp_id, mbedtls_ctr_drbg_random, &ctr_drbg);",
        "replacement": "mbedtls_ecdsa_genkey(ctx, grp_id, mbedtls_ctr_drbg_random, &ctr_drbg);"
    },
    {
        "name": "R04 mutant 5: unchecked ECDSA sign",
        "rule": "R04",
        "target": "int ret = mbedtls_ecdsa_sign(&args->ctx->grp, args->r, args->s, &args->ctx->d, args->hash, args->hash_len, mbedtls_ctr_drbg_random, &ctr_drbg);",
        "replacement": "mbedtls_ecdsa_sign(&args->ctx->grp, args->r, args->s, &args->ctx->d, args->hash, args->hash_len, mbedtls_ctr_drbg_random, &ctr_drbg);"
    },
    {
        "name": "R04 mutant 6: unchecked ECDSA verify",
        "rule": "R04",
        "target": "int ret = mbedtls_ecdsa_verify(&args->ctx->grp, args->hash, args->hash_len, &args->ctx->Q, args->r, args->s);",
        "replacement": "mbedtls_ecdsa_verify(&args->ctx->grp, args->hash, args->hash_len, &args->ctx->Q, args->r, args->s);"
    },
    {
        "name": "R04 mutant 7: unchecked ECDH gen public",
        "rule": "R04",
        "target": "int ret = mbedtls_ecdh_gen_public(&args->client_ctx->grp, &args->client_ctx->d, &args->client_ctx->Q, mbedtls_ctr_drbg_random, &ctr_drbg);",
        "replacement": "mbedtls_ecdh_gen_public(&args->client_ctx->grp, &args->client_ctx->d, &args->client_ctx->Q, mbedtls_ctr_drbg_random, &ctr_drbg);"
    },
    {
        "name": "R04 mutant 8: unchecked ECDH compute shared",
        "rule": "R04",
        "target": "int ret = mbedtls_ecdh_compute_shared(&args->client_ctx->grp, &args->client_ctx->z, &args->server_ctx->Q, &args->client_ctx->d, mbedtls_ctr_drbg_random, &ctr_drbg);",
        "replacement": "mbedtls_ecdh_compute_shared(&args->client_ctx->grp, &args->client_ctx->z, &args->server_ctx->Q, &args->client_ctx->d, mbedtls_ctr_drbg_random, &ctr_drbg);"
    },
    {
        "name": "R04 mutant 9: unchecked RSA gen key",
        "rule": "R04",
        "target": "int ret = mbedtls_rsa_gen_key(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, 2048, 65537);",
        "replacement": "mbedtls_rsa_gen_key(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, 2048, 65537);"
    },
    {
        "name": "R04 mutant 10: unchecked RSA sign",
        "rule": "R04",
        "target": "int ret = mbedtls_rsa_pkcs1_sign(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PRIVATE, MBEDTLS_MD_SHA256, 0, args->hash, args->sig);",
        "replacement": "mbedtls_rsa_pkcs1_sign(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PRIVATE, MBEDTLS_MD_SHA256, 0, args->hash, args->sig);"
    },
    {
        "name": "R04 mutant 11: unchecked RSA verify",
        "rule": "R04",
        "target": "int ret = mbedtls_rsa_pkcs1_verify(args->rsa, NULL, NULL, MBEDTLS_RSA_PUBLIC, MBEDTLS_MD_SHA256, 0, args->hash, args->sig);",
        "replacement": "mbedtls_rsa_pkcs1_verify(args->rsa, NULL, NULL, MBEDTLS_RSA_PUBLIC, MBEDTLS_MD_SHA256, 0, args->hash, args->sig);"
    },
    {
        "name": "R04 mutant 12: unchecked RSA OAEP encrypt",
        "rule": "R04",
        "target": "int ret = mbedtls_rsa_rsaes_oaep_encrypt(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PUBLIC, NULL, 0, 32, args->plaintext, args->ciphertext);",
        "replacement": "mbedtls_rsa_rsaes_oaep_encrypt(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PUBLIC, NULL, 0, 32, args->plaintext, args->ciphertext);"
    },
    {
        "name": "R04 mutant 13: unchecked RSA OAEP decrypt",
        "rule": "R04",
        "target": "int ret = mbedtls_rsa_rsaes_oaep_decrypt(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PRIVATE, NULL, 0, args->olen, args->ciphertext, args->decrypted, 256);",
        "replacement": "mbedtls_rsa_rsaes_oaep_decrypt(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PRIVATE, NULL, 0, args->olen, args->ciphertext, args->decrypted, 256);"
    },

    # --- R01: Hardcoded Buffer Sizes (14 Mutants) ---
    {
        "name": "R01 mutant 1: short public key buffer inside test_ecdsa",
        "rule": "R01",
        "target": "uint8_t hash[32] = { 0xAA };",
        "replacement": "uint8_t public_key[32] = { 0xAA };"
    },
    {
        "name": "R01 mutant 2: short secret key buffer inside test_rsa_sig",
        "rule": "R01",
        "target": "uint8_t hash[32] = { 0xBA };",
        "replacement": "uint8_t secret_key[32] = { 0xBA };"
    },
    {
        "name": "R01 mutant 3: short authentication key buffer inside test_dilithium",
        "rule": "R01",
        "target": "uint8_t msg[32] = { 0x55 };",
        "replacement": "uint8_t authentication_key[32] = { 0x55 };"
    },
    {
        "name": "R01 mutant 4: injected post-quantum public key buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t pqc_pk[64]; (void)pqc_pk;"
    },
    {
        "name": "R01 mutant 5: injected post-quantum ciphertext buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t pqc_ct[128]; (void)pqc_ct;"
    },
    {
        "name": "R01 mutant 6: injected post-quantum signature buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t pqc_sig[256]; (void)pqc_sig;"
    },
    {
        "name": "R01 mutant 7: injected generic pqc key buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t post_quantum_key[16]; (void)post_quantum_key;"
    },
    {
        "name": "R01 mutant 8: injected pqc secret key buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t pqc_secret[32]; (void)pqc_secret;"
    },
    {
        "name": "R01 mutant 9: injected kem ciphertext buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t kem_ciphertext[64]; (void)kem_ciphertext;"
    },
    {
        "name": "R01 mutant 10: injected dsa signature buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t dsa_signature[128]; (void)dsa_signature;"
    },
    {
        "name": "R01 mutant 11: injected oqs public key buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t oqs_public_key[256]; (void)oqs_public_key;"
    },
    {
        "name": "R01 mutant 12: injected oqs secret key buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t oqs_secret_key[128]; (void)oqs_secret_key;"
    },
    {
        "name": "R01 mutant 13: injected hybrid secret buffer",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t hybrid_secret[64]; (void)hybrid_secret;"
    },
    {
        "name": "R01 mutant 14: short key array",
        "rule": "R01",
        "target": "void setup() {",
        "replacement": "void setup() { uint8_t verification_key[32]; (void)verification_key;"
    },

    # --- R05: Algorithm-Specific APIs (6 Mutants) ---
    {
        "name": "R05 mutant 1: direct Kyber keypair call",
        "rule": "R05",
        "target": "void setup() {",
        "replacement": "void setup() { kyber_keypair();"
    },
    {
        "name": "R05 mutant 2: direct Dilithium sign call",
        "rule": "R05",
        "target": "void setup() {",
        "replacement": "void setup() { dilithium_sign();"
    },
    {
        "name": "R05 mutant 3: direct SPHINCS verify call",
        "rule": "R05",
        "target": "void setup() {",
        "replacement": "void setup() { sphincs_verify();"
    },
    {
        "name": "R05 mutant 4: direct Falcon decaps call",
        "rule": "R05",
        "target": "void setup() {",
        "replacement": "void setup() { falcon_decaps();"
    },
    {
        "name": "R05 mutant 5: direct McEliece encaps call",
        "rule": "R05",
        "target": "void setup() {",
        "replacement": "void setup() { mceliece_encaps();"
    },
    {
        "name": "R05 mutant 6: direct HQC keygen call",
        "rule": "R05",
        "target": "void setup() {",
        "replacement": "void setup() { hqc_keygen();"
    },

    # --- R02: Rigid Algorithm Selection (4 Mutants) ---
    {
        "name": "R02 mutant 1: switch statement with classical crypto",
        "rule": "R02",
        "target": "void setup() {",
        "replacement": "void setup() { int algo = 1; switch(algo) { case 1: /* RSA */ break; case 2: /* ECDSA */ break; }"
    },
    {
        "name": "R02 mutant 2: if-else chain with classical check",
        "rule": "R02",
        "target": "void setup() {",
        "replacement": "void setup() { const char* alg = \"ECDH\"; if (strcmp(alg, \"ECDH\") == 0) {} else if (strcmp(alg, \"RSA\") == 0) {}"
    },
    {
        "name": "R02 mutant 3: switch checking symmetric ciphers",
        "rule": "R02",
        "target": "void setup() {",
        "replacement": "void setup() { int type = 1; switch(type) { case 1: /* AES */ break; case 2: /* DES */ break; }"
    },
    {
        "name": "R02 mutant 4: if-else chain for classical algorithms",
        "rule": "R02",
        "target": "void setup() {",
        "replacement": "void setup() { const char* curve = \"P256\"; if (strcmp(curve, \"P256\") == 0) {} else if (strcmp(curve, \"P384\") == 0) {}"
    },

    # --- R07: Return Path Contract Violation (3 Mutants) ---
    {
        "name": "R07 mutant 1: unsafe keypair wrapper returning unvalidated variable",
        "rule": "R07",
        "target": "void setup() {",
        "replacement": "int unsafe_keypair() { int status = crypto_kem_keypair(NULL, NULL); return status; } void setup() {"
    },
    {
        "name": "R07 mutant 2: unsafe sign wrapper returning unvalidated variable",
        "rule": "R07",
        "target": "void setup() {",
        "replacement": "int unsafe_sign() { int rc = mbedtls_ecdsa_sign(NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL); return rc; } void setup() {"
    },
    {
        "name": "R07 mutant 3: unsafe verify wrapper returning unvalidated variable",
        "rule": "R07",
        "target": "void setup() {",
        "replacement": "int unsafe_verify() { int val = mbedtls_ecdsa_verify(NULL, NULL, 0, NULL, NULL, NULL); return val; } void setup() {"
    }
]

def main():
    if not os.path.exists(MAIN_CPP_PATH):
        print(f"Error: {MAIN_CPP_PATH} not found.")
        sys.exit(1)

    print("=" * 60)
    print("RUNNING MUTATION TESTING HARNESS FOR PQCFIRM")
    print("=" * 60)
    print(f"Base file: {MAIN_CPP_PATH}")
    print(f"Total Mutants to Inject: {len(MUTATIONS)}")
    print("-" * 60)

    # Read base main.cpp content
    with open(MAIN_CPP_PATH, "r", encoding="utf-8") as f:
        base_content = f.read()

    detected_count = 0
    scanner = Scanner()

    for idx, mut in enumerate(MUTATIONS):
        mut_name = mut["name"]
        rule_expected = mut["rule"]
        target = mut["target"]
        replacement = mut["replacement"]

        # Verify target exists in base content
        if target not in base_content:
            print(f"Error: Target text not found in base content for mutant '{mut_name}'")
            continue

        # Inject mutation
        mutated_content = base_content.replace(target, replacement, 1)

        # Write mutated content to temp file
        with open(TEMP_CPP_PATH, "w", encoding="utf-8") as f:
            f.write(mutated_content)

        # Scan the mutated file
        findings = scanner.scan_file(TEMP_CPP_PATH)

        # Check if the expected rule triggered
        detected = False
        for f in findings:
            if f.rule_id == rule_expected:
                detected = True
                break

        status = "PASSED (Detected)" if detected else "FAILED (Missed)"
        if detected:
            detected_count += 1
            print(f"Mutant {idx+1:02d}: {status} - {mut_name}")
        else:
            print(f"Mutant {idx+1:02d}: {status} - {mut_name} (Expected rule {rule_expected})")

    # Clean up mutated file
    if os.path.exists(TEMP_CPP_PATH):
        os.remove(TEMP_CPP_PATH)

    score = (detected_count / len(MUTATIONS)) if MUTATIONS else 0.0
    print("-" * 60)
    print("MUTATION SUMMARY:")
    print(f"  Total Mutants:            {len(MUTATIONS)}")
    print(f"  Detected:                 {detected_count}")
    print(f"  Missed:                   {len(MUTATIONS) - detected_count}")
    print(f"  Mutation-detection score: {score*100:.1f}%")
    print(f"Detected {detected_count}/{len(MUTATIONS)} injected mutants under the mutation model; this is not a production recall estimate.")
    print("=" * 60)

    # Output mutation_summary.json
    results_dir = os.path.abspath(os.path.join(script_dir, "..", "results"))
    os.makedirs(results_dir, exist_ok=True)
    summary_file = os.path.join(results_dir, "mutation_summary.json")
    summary_data = {
        "mutants_total": len(MUTATIONS),
        "mutants_detected": detected_count,
        "mutation_detection_score": score,
        "production_recall_estimate": False
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
        f.write("\n")

if __name__ == "__main__":
    main()
