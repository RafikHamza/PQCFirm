#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT_DIR/external"
cd "$ROOT_DIR/external"
if [ ! -d mbedtls ]; then
  git clone https://github.com/Mbed-TLS/mbedtls.git
fi
cd mbedtls
git fetch --tags
# Mbed TLS 3.6.0 release tag
git checkout v3.6.0
git submodule update --init --recursive
printf 'Mbed TLS source ready at: %s
' "$PWD"
