#include <stdint.h>
#define CURVE_P256 23
#define CURVE_P384 24
int set_curve(int curve) {
    if (curve == CURVE_P256) return 0;
    else if (curve == CURVE_P384) return 0;
    return -1;
}
