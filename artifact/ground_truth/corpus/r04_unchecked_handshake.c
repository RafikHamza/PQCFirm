#include <stdint.h>
int step(void *ssl) { mbedtls_ssl_handshake_step(ssl); return 0; }
int mbedtls_ssl_handshake_step(void *ssl) { return -1; }
