import os

from SCons.Script import Import

Import("env")

project_dir = env["PROJECT_DIR"]
project_src = os.path.join(project_dir, "src")
artifact_root = os.path.abspath(os.path.join(project_dir, ".."))
artifact_src = os.path.join(artifact_root, "src")
kyber_src = os.path.join(artifact_src, "kyber_internal")

# Ensure both project-local and artifact headers are visible
env.Append(CPPPATH=[project_src, artifact_src, kyber_src])

# Build the artifact sources in addition to the PlatformIO project sources.
# We intentionally do NOT compile kyber_internal/sha3.c or sha3x4.c because
# those depend on liboqs; instead we compile src/tiny_sha3.c which provides
# the needed OQS_SHA3_* API.
src_filter = [
    "+<vh_mlkem.c>",
    "+<tiny_sha3.c>",
    "+<kyber_internal/*.c>",
    "-<kyber_internal/fips202x4.c>",
    "-<kyber_internal/sha3.c>",
    "-<kyber_internal/sha3x4.c>",
]

env.BuildSources(os.path.join("$BUILD_DIR", "vhmlkem_artifact"), artifact_src, src_filter=src_filter)
