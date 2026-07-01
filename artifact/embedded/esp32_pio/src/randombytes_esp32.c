#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "bootloader_random.h"
#include "esp_system.h"

#include "mbedtls/hmac_drbg.h"
#include "mbedtls/md.h"

static mbedtls_hmac_drbg_context vh_drbg_ctx;
static bool vh_drbg_ready = false;

static void vh_drbg_init_once(void) {
    if (vh_drbg_ready) {
        return;
    }

    // Ensure the SAR ADC entropy source is enabled when Wi-Fi/Bluetooth are off.
    bootloader_random_enable();

    uint8_t seed[32];
    esp_fill_random(seed, sizeof(seed));

    const mbedtls_md_info_t *md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    mbedtls_hmac_drbg_init(&vh_drbg_ctx);

    if (md != NULL && mbedtls_hmac_drbg_seed_buf(&vh_drbg_ctx, md, seed, sizeof(seed)) == 0) {
        vh_drbg_ready = true;
    }

    // Wipe seed material regardless of initialization success.
    memset(seed, 0, sizeof(seed));
}

void randombytes(uint8_t *out, size_t outlen) {
    if (outlen == 0 || out == NULL) {
        return;
    }

    vh_drbg_init_once();

    if (vh_drbg_ready && mbedtls_hmac_drbg_random(&vh_drbg_ctx, out, outlen) == 0) {
        return;
    }

    // Fallback: direct hardware TRNG if DRBG initialization fails.
    esp_fill_random(out, outlen);
}
