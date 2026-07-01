#include <stdint.h>
int f(int alg) { return crypto_dispatch(alg); }
int crypto_dispatch(int alg) { return alg; }
