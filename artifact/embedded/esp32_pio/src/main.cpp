#include <Arduino.h>
#include <freertos/FreeRTOS.h>
// ============================================================
// Failure-Reproduction Demo Mode
// When FAILURE_REPRO_STACK_BYTES is defined, the firmware runs
// only the ML-KEM-768 stack crash test instead of full benchmarks.
// ESP-IDF/Arduino-ESP32 task stack arguments are documented here as bytes
// for this artifact. Verify this for the exact core/toolchain version used.
// ============================================================
#ifdef FAILURE_REPRO_STACK_BYTES
#include <freertos/task.h>
extern "C" {
#include "kyber_internal/kem.h"
}

static volatile int g_repro_done = 0;

static size_t stack_hwm_to_bytes(UBaseType_t hwm) {
#ifdef ESP_PLATFORM
    // ESP-IDF FreeRTOS reports task high-water marks in bytes.
    return (size_t)hwm;
#else
    // Vanilla FreeRTOS reports high-water marks in StackType_t words.
    return (size_t)hwm * sizeof(StackType_t);
#endif
}

static void failure_repro_task(void *pvParameters) {
    printf("[FAILURE_REPRO] Starting ML-KEM-768 decaps...\n");
    uint8_t pk[MLKEM_INDCCA_PUBLICKEYBYTES];
    uint8_t sk[MLKEM_INDCCA_SECRETKEYBYTES];
    uint8_t ct[MLKEM_INDCCA_CIPHERTEXTBYTES];
    uint8_t ss[MLKEM_SSBYTES];
    uint8_t ss2[MLKEM_SSBYTES];
    int ret = crypto_kem_keypair(pk, sk);
    ret = crypto_kem_enc(ct, ss, pk) || ret;
    ret = crypto_kem_dec(ss2, ct, sk) || ret;
    UBaseType_t hwm_raw = uxTaskGetStackHighWaterMark(NULL);
    size_t hwm_bytes = stack_hwm_to_bytes(hwm_raw);
    printf("[FAILURE_REPRO] PASS: stack_hwm_raw=%lu stack_hwm_bytes=%lu (ret=%d)\n",
           (unsigned long)hwm_raw, (unsigned long)hwm_bytes, ret);
    g_repro_done = 1;
    vTaskDelete(NULL);
}

void setup() {
    delay(1000);
    Serial.begin(115200);
    delay(500);
    printf("\n=== PQCFirm Failure Reproduction (ML-KEM-768) ===\n");
    uint32_t stack_kb = FAILURE_REPRO_STACK_BYTES / 1024;
    printf("Task stack argument: %lu bytes (%lu KB)\n",
           (unsigned long)FAILURE_REPRO_STACK_BYTES, (unsigned long)stack_kb);
    if (xTaskCreate(failure_repro_task, "failure_repro", FAILURE_REPRO_STACK_BYTES, NULL, 5, NULL) != pdPASS) {
        printf("[FAILURE_REPRO] Task creation failed!\n");
    }
}

void loop() {
    if (g_repro_done) {
        printf("[FAILURE_REPRO] TEST PASSED.\n");
        delay(10000);
    }
    delay(100);
}
#else
// ============================================================
// Normal full benchmark mode (original code)
// ============================================================
#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/ecdh.h"
#include "mbedtls/rsa.h"
#include "mbedtls/md.h"
#include "mbedtls/error.h"

extern "C" {
#include "kyber_internal/params.h"
#include "kyber_internal/kem.h"
#include "dilithium_internal/api.h"
#include "dilithium_internal/config.h"
}

#define QUOTE_IMPL(x) #x
#define QUOTE(x) QUOTE_IMPL(x)

#define ML_KEM_ALGO_NAME "ML_KEM_" QUOTE(MLK_CONFIG_PARAMETER_SET)
#define DILITHIUM_ALGO_NAME CRYPTO_ALGNAME

#define DILITHIUM_KEYPAIR DILITHIUM_NAMESPACE(keypair)
#define DILITHIUM_SIGNATURE DILITHIUM_NAMESPACE(signature)
#define DILITHIUM_VERIFY DILITHIUM_NAMESPACE(verify)
#define DILITHIUM_PK_BYTES DILITHIUM_NAMESPACE(PUBLICKEYBYTES)
#define DILITHIUM_SK_BYTES DILITHIUM_NAMESPACE(SECRETKEYBYTES)
#define DILITHIUM_SIG_BYTES DILITHIUM_NAMESPACE(BYTES)

// ------------------------------------------------------------
// Cycle counter (ESP32-S3 Xtensa LX7)
// ------------------------------------------------------------
static inline uint32_t get_ccount() {
    uint32_t ccount;
    asm volatile("rsr %0, ccount" : "=a"(ccount));
    return ccount;
}

static inline uint32_t cycles_delta(uint32_t start, uint32_t end) {
    return (uint32_t)(end - start);
}

static size_t stack_hwm_to_bytes(UBaseType_t hwm) {
#ifdef ESP_PLATFORM
    // ESP-IDF FreeRTOS reports task high-water marks in bytes.
    return (size_t)hwm;
#else
    // Vanilla FreeRTOS reports high-water marks in StackType_t words.
    return (size_t)hwm * sizeof(StackType_t);
#endif
}

// ------------------------------------------------------------
// Benchmark Configuration and Structure
// ------------------------------------------------------------
#define NUM_ITERATIONS 100

static int benchmark_iterations(const char *algo_name) {
    if (strcmp(algo_name, "ECDSA_P384") == 0) return 10;
    if (strcmp(algo_name, "ECDSA_P521") == 0) return 10;
    if (strcmp(algo_name, "ECDH_P384") == 0) return 1;
    if (strcmp(algo_name, "ECDH_P521") == 0) return 1;
    if (strcmp(algo_name, "RSA_PSS_2048") == 0) return 10;
    if (strcmp(algo_name, "RSA_OAEP_2048") == 0) return 2;
    return NUM_ITERATIONS;
}

// Mbed TLS Entropy/DRBG shared contexts
mbedtls_entropy_context entropy;
mbedtls_ctr_drbg_context ctr_drbg;

static bool init_rng() {
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    const char* pers = "pqcfirm_mcu_bench";
    int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy,
                                    (const unsigned char*)pers, strlen(pers));
    return ret == 0;
}

// ------------------------------------------------------------
// Fresh Task Execution Framework
// ------------------------------------------------------------
struct BenchParams {
    const char* algo;
    const char* op;
    int iterations;
    void (*run_func)(struct BenchParams* params);
    
    // Outputs
    uint32_t total_cycles;
    uint32_t min_cycles;
    uint32_t max_cycles;
    size_t stack_used;
    bool correctness;
    uint32_t* raw_cycles;
    
    // Inputs/Context pointers
    void* context;
    void* context2;
};

struct TaskParams {
    BenchParams* params;
    volatile bool done;
};

static void benchmark_runner_task(void *pvParameters) {
    TaskParams* tp = (TaskParams*)pvParameters;
    BenchParams* bp = tp->params;
    
    // Grab the initial watermark at task entry.
    UBaseType_t init_watermark_raw = uxTaskGetStackHighWaterMark(NULL);
    size_t init_watermark = stack_hwm_to_bytes(init_watermark_raw);
    
    // Execute the benchmark callback.
    bp->run_func(bp);
    
    // Grab the final watermark.
    UBaseType_t final_watermark_raw = uxTaskGetStackHighWaterMark(NULL);
    size_t final_watermark = stack_hwm_to_bytes(final_watermark_raw);
    
    if (final_watermark < init_watermark) {
        bp->stack_used = init_watermark - final_watermark;
    } else {
        bp->stack_used = 0;
    }
    
    tp->done = true;
    vTaskDelete(NULL);
}

static void run_benchmark_op(BenchParams* bp) {
    TaskParams tp;
    tp.params = bp;
    tp.done = false;
    bp->raw_cycles = (uint32_t*)malloc(bp->iterations * sizeof(uint32_t));
    if (!bp->raw_cycles) { Serial.println("OOM raw_cycles"); }
    
    Serial.printf("BENCHMARK_PHASE: %s %s\n", bp->algo, bp->op);
    
    // Spawn benchmark task with an explicit byte-sized stack argument for ESP-IDF/Arduino-ESP32.
    // Verify stack unit semantics if porting this firmware to vanilla FreeRTOS.
    BaseType_t ret = xTaskCreatePinnedToCore(
        benchmark_runner_task,
        "bench_run",
        32768,
        &tp,
        1,
        NULL,
        1
    );
    
    if (ret != pdPASS) {
        Serial.printf("Failed to create subtask for %s %s!\n", bp->algo, bp->op);
        bp->correctness = false;
        bp->stack_used = 0;
        return;
    }
    
    // Wait for the task to complete
    while (!tp.done) {
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    
    Serial.printf("BENCHMARK_PHASE_DONE: %s %s\n", bp->algo, bp->op);
}

static void print_bench_result(BenchParams* bp) {
    Serial.printf("BENCHMARK_JSON: %s %s\n", bp->algo, bp->op);
    Serial.print("{\"schema_version\":2,\"algo\":\"");
    Serial.print(bp->algo);
    Serial.print("\",\"op\":\"");
    Serial.print(bp->op);
    Serial.printf("\",\"avg_cycles\":%u,\"min_cycles\":%u,\"max_cycles\":%u,\"stack_used_bytes\":%u,\"correctness\":%s,\"raw_cycles\":[",
                  bp->total_cycles / bp->iterations, bp->min_cycles, bp->max_cycles, bp->stack_used, bp->correctness ? "true" : "false");
                  
    if (bp->raw_cycles) {
        for (int i = 0; i < bp->iterations; i++) {
            Serial.printf("%u%s", bp->raw_cycles[i], (i == bp->iterations - 1) ? "" : ",");
        }
        free(bp->raw_cycles);
        bp->raw_cycles = NULL;
    }
    Serial.println("]}");
}

// ------------------------------------------------------------
// ECDSA Generic Callbacks and Runner
// ------------------------------------------------------------
static void run_ecdsa_keygen(BenchParams* params) {
    mbedtls_ecdsa_context* ctx = (mbedtls_ecdsa_context*)params->context;
    mbedtls_ecp_group_id grp_id = (mbedtls_ecp_group_id)(uintptr_t)params->context2;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_ecdsa_genkey(ctx, grp_id, mbedtls_ctr_drbg_random, &ctr_drbg);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

struct EcdsaSignArgs {
    mbedtls_ecdsa_context* ctx;
    mbedtls_mpi* r;
    mbedtls_mpi* s;
    const uint8_t* hash;
    size_t hash_len;
};

static void run_ecdsa_sign(BenchParams* params) {
    EcdsaSignArgs* args = (EcdsaSignArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_ecdsa_sign(&args->ctx->grp, args->r, args->s, &args->ctx->d, args->hash, args->hash_len, mbedtls_ctr_drbg_random, &ctr_drbg);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_ecdsa_verify(BenchParams* params) {
    EcdsaSignArgs* args = (EcdsaSignArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_ecdsa_verify(&args->ctx->grp, args->hash, args->hash_len, &args->ctx->Q, args->r, args->s);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void benchmark_ecdsa_curve(mbedtls_ecp_group_id grp_id, const char* algo_name) {
    mbedtls_ecdsa_context ctx;
    mbedtls_ecdsa_init(&ctx);
    int iterations = benchmark_iterations(algo_name);
    
    // 1. KeyGen
    BenchParams bp_keygen;
    bp_keygen.algo = algo_name;
    bp_keygen.op = "KeyGen";
    bp_keygen.iterations = iterations;
    bp_keygen.run_func = run_ecdsa_keygen;
    bp_keygen.context = &ctx;
    bp_keygen.context2 = (void*)(uintptr_t)grp_id;
    
    run_benchmark_op(&bp_keygen);
    print_bench_result(&bp_keygen);
    
    if (!bp_keygen.correctness) {
        mbedtls_ecdsa_free(&ctx);
        return;
    }
    
    // Sign & Verify contexts
    uint8_t hash[32] = { 0xAA };
    mbedtls_mpi r, s;
    mbedtls_mpi_init(&r);
    mbedtls_mpi_init(&s);
    
    EcdsaSignArgs sign_args;
    sign_args.ctx = &ctx;
    sign_args.r = &r;
    sign_args.s = &s;
    sign_args.hash = hash;
    sign_args.hash_len = sizeof(hash);
    
    // 2. Sign
    BenchParams bp_sign;
    bp_sign.algo = algo_name;
    bp_sign.op = "Sign";
    bp_sign.iterations = iterations;
    bp_sign.run_func = run_ecdsa_sign;
    bp_sign.context = &sign_args;
    
    run_benchmark_op(&bp_sign);
    print_bench_result(&bp_sign);
    
    // 3. Verify
    BenchParams bp_verify;
    bp_verify.algo = algo_name;
    bp_verify.op = "Verify";
    bp_verify.iterations = iterations;
    bp_verify.run_func = run_ecdsa_verify;
    bp_verify.context = &sign_args;
    
    run_benchmark_op(&bp_verify);
    print_bench_result(&bp_verify);
    
    mbedtls_mpi_free(&r);
    mbedtls_mpi_free(&s);
    mbedtls_ecdsa_free(&ctx);
}

// ------------------------------------------------------------
// ECDH Generic Callbacks and Runner
// ------------------------------------------------------------
struct EcdhArgs {
    mbedtls_ecdh_context* client_ctx;
    mbedtls_ecdh_context* server_ctx;
};

static void run_ecdh_keygen(BenchParams* params) {
    EcdhArgs* args = (EcdhArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_ecdh_gen_public(&args->client_ctx->grp, &args->client_ctx->d, &args->client_ctx->Q, mbedtls_ctr_drbg_random, &ctr_drbg);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_ecdh_compute_secret(BenchParams* params) {
    EcdhArgs* args = (EcdhArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_ecdh_compute_shared(&args->client_ctx->grp, &args->client_ctx->z, &args->server_ctx->Q, &args->client_ctx->d, mbedtls_ctr_drbg_random, &ctr_drbg);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void benchmark_ecdh_curve(mbedtls_ecp_group_id grp_id, const char* algo_name) {
    mbedtls_ecdh_context client_ctx, server_ctx;
    mbedtls_ecdh_init(&client_ctx);
    mbedtls_ecdh_init(&server_ctx);
    
    int ret = mbedtls_ecp_group_load(&client_ctx.grp, grp_id);
    if (ret != 0) {
        Serial.printf("%s group load failed: -0x%04x\n", algo_name, -ret);
        mbedtls_ecdh_free(&client_ctx);
        mbedtls_ecdh_free(&server_ctx);
        return;
    }
    ret = mbedtls_ecp_group_load(&server_ctx.grp, grp_id);
    if (ret != 0) {
        Serial.printf("%s server group load failed: -0x%04x\n", algo_name, -ret);
        mbedtls_ecdh_free(&client_ctx);
        mbedtls_ecdh_free(&server_ctx);
        return;
    }
    
    int iterations = benchmark_iterations(algo_name);
    EcdhArgs ecdh_args;
    ecdh_args.client_ctx = &client_ctx;
    ecdh_args.server_ctx = &server_ctx;
    
    // 1. KeyGen
    BenchParams bp_keygen;
    bp_keygen.algo = algo_name;
    bp_keygen.op = "KeyGen";
    bp_keygen.iterations = iterations;
    bp_keygen.run_func = run_ecdh_keygen;
    bp_keygen.context = &ecdh_args;
    
    run_benchmark_op(&bp_keygen);
    print_bench_result(&bp_keygen);
    
    if (!bp_keygen.correctness) {
        mbedtls_ecdh_free(&client_ctx);
        mbedtls_ecdh_free(&server_ctx);
        return;
    }
    
    // Compute server side public key to allow ComputeSecret run
    mbedtls_ecdh_gen_public(&server_ctx.grp, &server_ctx.d, &server_ctx.Q, mbedtls_ctr_drbg_random, &ctr_drbg);
    
    // 2. ComputeSecret
    BenchParams bp_secret;
    bp_secret.algo = algo_name;
    bp_secret.op = "ComputeSecret";
    bp_secret.iterations = iterations;
    bp_secret.run_func = run_ecdh_compute_secret;
    bp_secret.context = &ecdh_args;
    
    run_benchmark_op(&bp_secret);
    print_bench_result(&bp_secret);
    
    mbedtls_ecdh_free(&client_ctx);
    mbedtls_ecdh_free(&server_ctx);
}

// ------------------------------------------------------------
// Specific Classical Benchmarks
// ------------------------------------------------------------
static void benchmark_ecdsa_p256() {
    benchmark_ecdsa_curve(MBEDTLS_ECP_DP_SECP256R1, "ECDSA_P256");
}

static void benchmark_ecdh_p256() {
    benchmark_ecdh_curve(MBEDTLS_ECP_DP_SECP256R1, "ECDH_P256");
}

static void benchmark_x25519() {
    benchmark_ecdh_curve(MBEDTLS_ECP_DP_CURVE25519, "X25519");
}

#if defined(MBEDTLS_ECP_DP_CURVE448)
static void benchmark_x448() {
    benchmark_ecdh_curve(MBEDTLS_ECP_DP_CURVE448, "X448");
}
#endif

// ------------------------------------------------------------
// RSA Benchmark Helpers
// ------------------------------------------------------------
struct RsaArgs {
    mbedtls_rsa_context* rsa;
    uint8_t* hash;
    size_t hash_len;
    uint8_t* sig;
    uint8_t* plaintext;
    uint8_t* ciphertext;
    uint8_t* decrypted;
    size_t* olen;
};

static void run_rsa_keygen(BenchParams* params) {
    RsaArgs* args = (RsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_rsa_gen_key(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, 2048, 65537);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_rsa_pss_sign(BenchParams* params) {
    RsaArgs* args = (RsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_rsa_pkcs1_sign(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PRIVATE, MBEDTLS_MD_SHA256, 0, args->hash, args->sig);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_rsa_pss_verify(BenchParams* params) {
    RsaArgs* args = (RsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_rsa_pkcs1_verify(args->rsa, NULL, NULL, MBEDTLS_RSA_PUBLIC, MBEDTLS_MD_SHA256, 0, args->hash, args->sig);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void benchmark_rsa_pss() {
    mbedtls_rsa_context rsa;
    mbedtls_rsa_init(&rsa, MBEDTLS_RSA_PKCS_V21, MBEDTLS_MD_SHA256);
    int iterations = benchmark_iterations("RSA_PSS_2048");
    
    uint8_t hash[32] = { 0xBA };
    uint8_t sig[512] = {0};
    
    RsaArgs rsa_args;
    rsa_args.rsa = &rsa;
    rsa_args.hash = hash;
    rsa_args.hash_len = sizeof(hash);
    rsa_args.sig = sig;
    
    // 1. KeyGen
    BenchParams bp_keygen;
    bp_keygen.algo = "RSA_PSS_2048";
    bp_keygen.op = "KeyGen";
    bp_keygen.iterations = iterations;
    bp_keygen.run_func = run_rsa_keygen;
    bp_keygen.context = &rsa_args;
    
    run_benchmark_op(&bp_keygen);
    print_bench_result(&bp_keygen);
    
    if (!bp_keygen.correctness) {
        mbedtls_rsa_free(&rsa);
        return;
    }
    
    // 2. Sign
    BenchParams bp_sign;
    bp_sign.algo = "RSA_PSS_2048";
    bp_sign.op = "Sign";
    bp_sign.iterations = iterations;
    bp_sign.run_func = run_rsa_pss_sign;
    bp_sign.context = &rsa_args;
    
    run_benchmark_op(&bp_sign);
    print_bench_result(&bp_sign);
    
    // 3. Verify
    BenchParams bp_verify;
    bp_verify.algo = "RSA_PSS_2048";
    bp_verify.op = "Verify";
    bp_verify.iterations = iterations;
    bp_verify.run_func = run_rsa_pss_verify;
    bp_verify.context = &rsa_args;
    
    run_benchmark_op(&bp_verify);
    print_bench_result(&bp_verify);
    
    mbedtls_rsa_free(&rsa);
}

// ------------------------------------------------------------
// RSA OAEP Benchmark
// ------------------------------------------------------------
static void run_rsa_oaep_encrypt(BenchParams* params) {
    RsaArgs* args = (RsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_rsa_rsaes_oaep_encrypt(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PUBLIC, NULL, 0, 32, args->plaintext, args->ciphertext);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_rsa_oaep_decrypt(BenchParams* params) {
    RsaArgs* args = (RsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = mbedtls_rsa_rsaes_oaep_decrypt(args->rsa, mbedtls_ctr_drbg_random, &ctr_drbg, MBEDTLS_RSA_PRIVATE, NULL, 0, args->olen, args->ciphertext, args->decrypted, 256);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void benchmark_rsa_oaep() {
    mbedtls_rsa_context rsa;
    mbedtls_rsa_init(&rsa, MBEDTLS_RSA_PKCS_V21, MBEDTLS_MD_SHA256);
    int iterations = benchmark_iterations("RSA_OAEP_2048");
    
    uint8_t plaintext[32] = { 0xCD };
    uint8_t ciphertext[256] = {0};
    uint8_t decrypted[256] = {0};
    size_t olen = 0;
    
    RsaArgs rsa_args;
    rsa_args.rsa = &rsa;
    rsa_args.plaintext = plaintext;
    rsa_args.ciphertext = ciphertext;
    rsa_args.decrypted = decrypted;
    rsa_args.olen = &olen;
    
    // 1. KeyGen
    BenchParams bp_keygen;
    bp_keygen.algo = "RSA_OAEP_2048";
    bp_keygen.op = "KeyGen";
    bp_keygen.iterations = iterations;
    bp_keygen.run_func = run_rsa_keygen;
    bp_keygen.context = &rsa_args;
    
    run_benchmark_op(&bp_keygen);
    print_bench_result(&bp_keygen);
    
    if (!bp_keygen.correctness) {
        mbedtls_rsa_free(&rsa);
        return;
    }
    
    // 2. Encrypt
    BenchParams bp_enc;
    bp_enc.algo = "RSA_OAEP_2048";
    bp_enc.op = "Encrypt";
    bp_enc.iterations = iterations;
    bp_enc.run_func = run_rsa_oaep_encrypt;
    bp_enc.context = &rsa_args;
    
    run_benchmark_op(&bp_enc);
    print_bench_result(&bp_enc);
    
    // 3. Decrypt
    BenchParams bp_dec;
    bp_dec.algo = "RSA_OAEP_2048";
    bp_dec.op = "Decrypt";
    bp_dec.iterations = iterations;
    bp_dec.run_func = run_rsa_oaep_decrypt;
    bp_dec.context = &rsa_args;
    
    run_benchmark_op(&bp_dec);
    
    // verify correctness of Decrypt manually
    bp_dec.correctness = (bp_dec.correctness && olen == sizeof(plaintext) && memcmp(plaintext, decrypted, sizeof(plaintext)) == 0);
    print_bench_result(&bp_dec);
    
    mbedtls_rsa_free(&rsa);
}

// ------------------------------------------------------------
// ML-KEM Benchmarks
// ------------------------------------------------------------
struct MlkemArgs {
    uint8_t* pk;
    uint8_t* sk;
    uint8_t* ct;
    uint8_t* ss_enc;
    uint8_t* ss_dec;
};

static void run_mlkem_keygen(BenchParams* params) {
    MlkemArgs* args = (MlkemArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = crypto_kem_keypair(args->pk, args->sk);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_mlkem_encaps(BenchParams* params) {
    MlkemArgs* args = (MlkemArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = crypto_kem_enc(args->ct, args->ss_enc, args->pk);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_mlkem_decaps(BenchParams* params) {
    MlkemArgs* args = (MlkemArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = crypto_kem_dec(args->ss_dec, args->ct, args->sk);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void benchmark_ml_kem() {
    uint8_t* pk = (uint8_t*)malloc(MLKEM_INDCCA_PUBLICKEYBYTES);
    uint8_t* sk = (uint8_t*)malloc(MLKEM_INDCCA_SECRETKEYBYTES);
    uint8_t* ct = (uint8_t*)malloc(MLKEM_INDCCA_CIPHERTEXTBYTES);
    uint8_t ss_enc[MLKEM_SSBYTES] = {0};
    uint8_t ss_dec[MLKEM_SSBYTES] = {0};
    
    if (!pk || !sk || !ct) {
        Serial.println("ML-KEM Memory allocation failed!");
        if (pk) free(pk);
        if (sk) free(sk);
        if (ct) free(ct);
        return;
    }
    
    MlkemArgs args;
    args.pk = pk;
    args.sk = sk;
    args.ct = ct;
    args.ss_enc = ss_enc;
    args.ss_dec = ss_dec;
    
    // 1. KeyGen
    BenchParams bp_keygen;
    bp_keygen.algo = ML_KEM_ALGO_NAME;
    bp_keygen.op = "KeyGen";
    bp_keygen.iterations = NUM_ITERATIONS;
    bp_keygen.run_func = run_mlkem_keygen;
    bp_keygen.context = &args;
    
    run_benchmark_op(&bp_keygen);
    print_bench_result(&bp_keygen);
    
    if (!bp_keygen.correctness) {
        free(pk);
        free(sk);
        free(ct);
        return;
    }
    
    // 2. Encaps
    BenchParams bp_enc;
    bp_enc.algo = ML_KEM_ALGO_NAME;
    bp_enc.op = "Encaps";
    bp_enc.iterations = NUM_ITERATIONS;
    bp_enc.run_func = run_mlkem_encaps;
    bp_enc.context = &args;
    
    run_benchmark_op(&bp_enc);
    print_bench_result(&bp_enc);
    
    // 3. Decaps
    BenchParams bp_dec;
    bp_dec.algo = ML_KEM_ALGO_NAME;
    bp_dec.op = "Decaps";
    bp_dec.iterations = NUM_ITERATIONS;
    bp_dec.run_func = run_mlkem_decaps;
    bp_dec.context = &args;
    
    run_benchmark_op(&bp_dec);
    
    bool ss_match = (memcmp(ss_enc, ss_dec, MLKEM_SSBYTES) == 0);
    bp_dec.correctness = (bp_dec.correctness && ss_match);
    print_bench_result(&bp_dec);
    
    free(pk);
    free(sk);
    free(ct);
}

// ------------------------------------------------------------
// ML-DSA Benchmarks
// ------------------------------------------------------------
struct MldsaArgs {
    uint8_t* pk;
    uint8_t* sk;
    uint8_t* sig;
    size_t* siglen;
    uint8_t* msg;
    size_t msglen;
};

static void run_mldsa_keygen(BenchParams* params) {
    MldsaArgs* args = (MldsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        DILITHIUM_KEYPAIR(args->pk, args->sk);
        uint32_t t1 = get_ccount();
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_mldsa_sign(BenchParams* params) {
    MldsaArgs* args = (MldsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        *args->siglen = DILITHIUM_SIG_BYTES;
        uint32_t t0 = get_ccount();
        DILITHIUM_SIGNATURE(args->sig, args->siglen, args->msg, args->msglen, args->sk);
        uint32_t t1 = get_ccount();
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void run_mldsa_verify(BenchParams* params) {
    MldsaArgs* args = (MldsaArgs*)params->context;
    params->min_cycles = -1;
    params->max_cycles = 0;
    params->total_cycles = 0;
    params->correctness = true;
    
    for (int i = 0; i < params->iterations; i++) {
        uint32_t t0 = get_ccount();
        int ret = DILITHIUM_VERIFY(args->sig, *args->siglen, args->msg, args->msglen, args->pk);
        uint32_t t1 = get_ccount();
        if (ret != 0) {
            params->correctness = false;
        }
        uint32_t diff = cycles_delta(t0, t1);
        params->total_cycles += diff; if (params->raw_cycles) params->raw_cycles[i] = diff;
        if (diff < params->min_cycles) params->min_cycles = diff;
        if (diff > params->max_cycles) params->max_cycles = diff;
    }
}

static void benchmark_ml_dsa() {
    uint8_t* pk = (uint8_t*)malloc(DILITHIUM_PK_BYTES);
    uint8_t* sk = (uint8_t*)malloc(DILITHIUM_SK_BYTES);
    uint8_t* sig = (uint8_t*)malloc(DILITHIUM_SIG_BYTES);
    size_t siglen = DILITHIUM_SIG_BYTES;
    uint8_t msg[32] = { 0x55 };
    
    if (!pk || !sk || !sig) {
        Serial.println("ML-DSA Memory allocation failed!");
        if (pk) free(pk);
        if (sk) free(sk);
        if (sig) free(sig);
        return;
    }
    
    MldsaArgs args;
    args.pk = pk;
    args.sk = sk;
    args.sig = sig;
    args.siglen = &siglen;
    args.msg = msg;
    args.msglen = sizeof(msg);
    
    // 1. KeyGen
    BenchParams bp_keygen;
    bp_keygen.algo = DILITHIUM_ALGO_NAME;
    bp_keygen.op = "KeyGen";
    bp_keygen.iterations = NUM_ITERATIONS;
    bp_keygen.run_func = run_mldsa_keygen;
    bp_keygen.context = &args;
    
    run_benchmark_op(&bp_keygen);
    print_bench_result(&bp_keygen);
    
    // 2. Sign
    BenchParams bp_sign;
    bp_sign.algo = DILITHIUM_ALGO_NAME;
    bp_sign.op = "Sign";
    bp_sign.iterations = NUM_ITERATIONS;
    bp_sign.run_func = run_mldsa_sign;
    bp_sign.context = &args;
    
    run_benchmark_op(&bp_sign);
    print_bench_result(&bp_sign);
    
    // 3. Verify
    BenchParams bp_verify;
    bp_verify.algo = DILITHIUM_ALGO_NAME;
    bp_verify.op = "Verify";
    bp_verify.iterations = NUM_ITERATIONS;
    bp_verify.run_func = run_mldsa_verify;
    bp_verify.context = &args;
    
    run_benchmark_op(&bp_verify);
    print_bench_result(&bp_verify);
    
    free(pk);
    free(sk);
    free(sig);
}

// ------------------------------------------------------------
// Master Benchmark task
// ------------------------------------------------------------
static void bench_task(void *arg) {
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(2000)); // Allow serial monitor to open

    Serial.println("\n--- Starting PQCFirm Embedded Benchmarks ---");
    
    if (!init_rng()) {
        Serial.println("RNG Initialization failed!");
        vTaskDelete(NULL);
        return;
    }

    Serial.println("\n--- Running Classical Benchmarks ---");
    benchmark_ecdsa_p256();
    benchmark_ecdsa_curve(MBEDTLS_ECP_DP_SECP384R1, "ECDSA_P384");
    benchmark_ecdsa_curve(MBEDTLS_ECP_DP_SECP521R1, "ECDSA_P521");
    benchmark_ecdh_p256();
    benchmark_ecdh_curve(MBEDTLS_ECP_DP_SECP384R1, "ECDH_P384");
    benchmark_ecdh_curve(MBEDTLS_ECP_DP_SECP521R1, "ECDH_P521");
    benchmark_x25519();
#if defined(MBEDTLS_ECP_DP_CURVE448)
    benchmark_x448();
#endif
    benchmark_rsa_pss();
    benchmark_rsa_oaep();

    Serial.println("\n--- Running PQC Benchmarks ---");
    benchmark_ml_kem();
    benchmark_ml_dsa();

    Serial.println("\n--- Benchmarks Complete ---");
    vTaskDelete(NULL);
}

void setup() {
    Serial.begin(115200);
    
    // Spawns the driver task with a small stack size (4KB) since it only orchestrates subtasks
    xTaskCreatePinnedToCore(
        bench_task,
        "bench_task",
        4096,
        NULL,
        1,
        NULL,
        1
    );
}

void loop() {
    delay(1000);
}
#endif
