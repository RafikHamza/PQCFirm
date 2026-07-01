#include <stdint.h>
int f(const uint8_t *key, size_t len) { int ret = psa_import_key(key, len); return ret; }
int psa_import_key(const uint8_t *key, size_t len) { return -1; }
