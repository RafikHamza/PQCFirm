/*
 * PQCFirm Failure-Reproduction Experiment
 * ==========================================
 *
 * Demonstrates the stack-risk side of PQC migration on an ESP32-S3 by
 * running ML-KEM-768 keypair/encaps/decaps inside a FreeRTOS task.
 *
 * Two configurations:
 *   CRASH_TINY_STACK (8 KB task stack)  — crash/panic expected
 *   SAFE            (96 KB task stack) — completion expected
 *
 * Build and run:
 *   pio run -e esp32s3-crash-tiny  --target upload
 *   pio run -e esp32s3-crash-large --target upload
 *
 * This file is an Arduino-framework sketch. Do NOT define app_main() here:
 * Arduino-ESP32 already provides app_main() and calls setup()/loop().
 */

#include <Arduino.h>
#include <stdio.h>
#include <string.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

extern "C" {
#include "kyber_internal/kem.h"
}

// ESP-IDF/Arduino-ESP32 reports the high-water mark in bytes in current
// ESP32 FreeRTOS APIs. Vanilla FreeRTOS ports may report StackType_t words.
static size_t stack_hwm_to_bytes(UBaseType_t hwm) {
#ifdef ESP_PLATFORM
    return (size_t)hwm;
#else
    return (size_t)hwm * sizeof(StackType_t);
#endif
}

static UBaseType_t measure_task_stack_hwm_raw(void) {
    return uxTaskGetStackHighWaterMark(NULL);
}

static volatile uint8_t g_task_success = 0;

static void mlkem_crash_task(void *pvParameters) {
    (void)pvParameters;

    printf("[FAILURE_REPRO] Starting ML-KEM-768 keypair/encaps/decaps...\n");
    fflush(stdout);

    uint8_t pk[MLKEM_INDCCA_PUBLICKEYBYTES];
    uint8_t sk[MLKEM_INDCCA_SECRETKEYBYTES];
    uint8_t ct[MLKEM_INDCCA_CIPHERTEXTBYTES];
    uint8_t ss[MLKEM_SSBYTES];
    uint8_t ss2[MLKEM_SSBYTES];

    int rc1 = crypto_kem_keypair(pk, sk);
    int rc2 = crypto_kem_enc(ct, ss, pk);
    int rc3 = crypto_kem_dec(ss2, ct, sk);

    if (rc1 != 0 || rc2 != 0 || rc3 != 0) {
        printf("[FAILURE_REPRO] ERROR: ML-KEM operation failed rc=(%d,%d,%d)\n", rc1, rc2, rc3);
        fflush(stdout);
        vTaskDelete(NULL);
    }

    if (memcmp(ss, ss2, MLKEM_SSBYTES) != 0) {
        printf("[FAILURE_REPRO] ERROR: shared secrets mismatch\n");
        fflush(stdout);
        vTaskDelete(NULL);
    }

    UBaseType_t hwm_raw = measure_task_stack_hwm_raw();
    size_t hwm_bytes = stack_hwm_to_bytes(hwm_raw);
    printf("[FAILURE_REPRO] Completed successfully: stack_hwm_raw=%lu stack_hwm_bytes=%lu\n",
           (unsigned long)hwm_raw, (unsigned long)hwm_bytes);
    printf("[FAILURE_REPRO] TEST PASSED\n");
    fflush(stdout);

    g_task_success = 1;
    vTaskDelete(NULL);
}

void setup(void) {
    Serial.begin(115200);
    delay(1000);

    printf("\n========================================\n");
    printf("  PQCFirm Failure-Reproduction Demo\n");
    printf("  ML-KEM-768 keypair/encaps/decaps\n");
#if defined(CRASH_TINY_STACK)
    printf("  Task stack: 8 KB (CRASH expected)\n");
    const uint32_t stack_bytes = 8192;
    const char *task_name = "mlkem_crash";
#else
    printf("  Task stack: 96 KB (SAFE expected)\n");
    const uint32_t stack_bytes = 98304;
    const char *task_name = "mlkem_safe";
#endif
    printf("========================================\n\n");
    fflush(stdout);

    BaseType_t ok = xTaskCreate(
        mlkem_crash_task,
        task_name,
        stack_bytes,
        NULL,
        5,
        NULL
    );

    if (ok != pdPASS) {
        printf("[FAILURE_REPRO] ERROR: Task creation failed for stack_bytes=%lu\n", (unsigned long)stack_bytes);
        fflush(stdout);
        return;
    }

    // Wait for the task to finish in the safe configuration, or for the CPU
    // panic/reboot in the tiny-stack configuration.
    delay(7000);

    if (g_task_success) {
        printf("[FAILURE_REPRO] Main observed task success.\n");
    } else {
        printf("[FAILURE_REPRO] NOTE: If this is the tiny-stack build and a Guru Meditation/stack panic appears, the crash reproduction succeeded.\n");
    }
    fflush(stdout);
}

void loop(void) {
    delay(1000);
}
