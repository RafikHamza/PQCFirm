#define ALG_ECDSA 1
#define ALG_ML_KEM 2
int f(int alg) {
    switch (alg) {
        case ALG_ECDSA: return 1;
        case ALG_ML_KEM: return 1;
        default: return 0;
    }
}
