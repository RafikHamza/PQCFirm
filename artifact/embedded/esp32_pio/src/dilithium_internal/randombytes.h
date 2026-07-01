#ifndef DILITHIUM_RANDOMBYTES_H
#define DILITHIUM_RANDOMBYTES_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void randombytes(uint8_t *out, size_t outlen);

#ifdef __cplusplus
}
#endif

#endif
