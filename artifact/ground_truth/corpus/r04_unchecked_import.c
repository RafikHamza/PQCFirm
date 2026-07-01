#include <stdint.h>
int do_import(const uint8_t *key, size_t len) { psa_import_key(key, len); return 0; }
int psa_import_key(const uint8_t *key, size_t len) { return -1; }
