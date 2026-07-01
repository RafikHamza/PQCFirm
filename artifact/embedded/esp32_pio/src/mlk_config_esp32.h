#pragma once

// Minimal mlkem-native configuration for the ESP32-S3 PlatformIO build.
// This avoids liboqs integration, while keeping the standard ML-KEM API.

// Parameter set: ML-KEM-768 (override via build flags if needed)
#ifndef MLK_CONFIG_PARAMETER_SET
#define MLK_CONFIG_PARAMETER_SET 768
#endif

// Namespace all mlkem-native symbols with a simple prefix.
// This must be consistent across all compiled kyber_internal sources.
#define MLK_CONFIG_NAMESPACE_PREFIX mlkem

// Use the Kyber-internal FIPS202 headers shipped with the artifact.
// They rely on OQS_SHA3_* symbols, which are provided by src/tiny_sha3.c.
#define MLK_CONFIG_FIPS202_CUSTOM_HEADER "fips202.h"

// x4 SHAKE API: use scalar fallback to avoid liboqs dependencies.
#define MLK_CONFIG_FIPS202X4_CUSTOM_HEADER "fips202x4_stub.h"

// IMPORTANT: do NOT define MLK_CONFIG_CUSTOM_RANDOMBYTES here.
// We provide a plain randombytes() in esp32_pio/src/randombytes_esp32.c.
