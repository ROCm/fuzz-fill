#!/usr/bin/env bash

set -euo pipefail

CMAKE_VERSION="${1:-4.4.3}"
PREFIX="${2:-/usr/local}"

url="https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.sh"
installer="$(mktemp /tmp/cmake-installer.XXXXXX.sh)"

echo "Installing CMake ${CMAKE_VERSION} into ${PREFIX} (from ${url})"
curl -fsSL "$url" -o "$installer"
chmod +x "$installer"
"$installer" --skip-license --prefix="$PREFIX"
rm -f "$installer"

cmake --version
