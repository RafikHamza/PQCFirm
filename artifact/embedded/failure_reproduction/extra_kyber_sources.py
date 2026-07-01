"""Add shared ML-KEM sources to the failure-reproduction PlatformIO build.

The failure-reproduction project lives next to the main ESP32-S3 benchmark project,
so PlatformIO will not automatically compile the shared kyber_internal C files.
This script explicitly adds only the source files needed for ML-KEM-768 and the
small SHA3/randomness shims used by the main benchmark firmware.
"""
from pathlib import Path
Import("env")  # type: ignore  # PlatformIO/SCons injects this symbol

project_dir = Path(env.subst("$PROJECT_DIR")).resolve()
embedded_dir = project_dir.parent
shared_src = embedded_dir / "esp32_pio" / "src"
kyber_dir = shared_src / "kyber_internal"

# Sources required by mlkem-native for keypair/encaps/decaps.  Do not compile
# kyber_internal/sha3.c or sha3x4.c here; those are liboqs callback wrappers.
# The artifact uses tiny_sha3.c instead to avoid an external liboqs dependency.
kyber_sources = [
    "compress.c",
    "debug.c",
    "fips202.c",
    "indcpa.c",
    "kem.c",
    "poly.c",
    "poly_k.c",
    "sampling.c",
    "verify.c",
]

for src in kyber_sources:
    env.BuildSources(str(Path("$BUILD_DIR") / "kyber_internal"), str(kyber_dir / src))

for src in ["randombytes_esp32.c", "tiny_sha3.c"]:
    env.BuildSources(str(Path("$BUILD_DIR") / "esp32_shared"), str(shared_src / src))
