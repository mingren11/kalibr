#!/bin/bash

set -euo pipefail

show_usage() {
  cat <<'EOF'
Usage:
  ./build_kalibr_x5.sh [--clean] <install_dir> [build_dir]

Example:
  ./build_kalibr_x5.sh /LooperHub/tros_ws/install/kalibr
  ./build_kalibr_x5.sh --clean /LooperHub/tros_ws/install/kalibr
  ./build_kalibr_x5.sh /userdata/kalibr_install build_standalone_x5
EOF
}

DO_CLEAN=0
if [[ "${1:-}" == "--clean" ]]; then
  DO_CLEAN=1
  shift
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  show_usage
  exit 1
fi

KALIBR_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TROS_WS="$(cd "${KALIBR_SRC}/../.." && pwd)"
SYSROOT_DIR="$(cd "${TROS_WS}/../sysroot_docker" && pwd)"
INSTALL_DIR="$1"
BUILD_DIR_INPUT="${2:-build_standalone_x5}"

if [[ "${BUILD_DIR_INPUT}" = /* ]]; then
  BUILD_DIR="${BUILD_DIR_INPUT}"
else
  BUILD_DIR="${KALIBR_SRC}/${BUILD_DIR_INPUT}"
fi

export TARGET_ARCH=aarch64
export TARGET_TRIPLE=aarch64-linux-gnu
export CROSS_COMPILE="/usr/bin/${TARGET_TRIPLE}-"

if [[ ! -x "${CROSS_COMPILE}g++" ]]; then
  echo "Error: cross compiler not found: ${CROSS_COMPILE}g++"
  exit 1
fi

if [[ ! -d "${SYSROOT_DIR}/usr_x5" ]]; then
  echo "Error: X5 sysroot not found: ${SYSROOT_DIR}/usr_x5"
  exit 1
fi

if [[ -f /opt/ros/humble/setup.bash ]]; then
  # Some CMake packages are resolved from the ROS cross-build environment.
  set +u
  source /opt/ros/humble/setup.bash
  set -u
fi

rm -f "${SYSROOT_DIR}/usr"
ln -s "${SYSROOT_DIR}/usr_x5" "${SYSROOT_DIR}/usr"

export PKG_CONFIG_PATH="${SYSROOT_DIR}/usr/lib/aarch64-linux-gnu/pkgconfig"

mkdir -p "${BUILD_DIR}"
if [[ ${DO_CLEAN} -eq 1 ]]; then
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}"
fi

echo "Building kalibr for X5"
echo "  Source:  ${KALIBR_SRC}"
echo "  Build:   ${BUILD_DIR}"
echo "  Install: ${INSTALL_DIR}"
echo "  Sysroot: ${SYSROOT_DIR}/usr -> ${SYSROOT_DIR}/usr_x5"
if [[ ${DO_CLEAN} -eq 1 ]]; then
  echo "  Clean:   enabled"
fi

mkdir -p "${INSTALL_DIR}" 2>/dev/null || {
  echo "Error: cannot create install directory: ${INSTALL_DIR}"
  echo "Check that the parent directory exists and is writable by the current user."
  exit 1
}

if [[ ! -w "${INSTALL_DIR}" ]]; then
  echo "Error: install directory is not writable: ${INSTALL_DIR}"
  echo "If this path was created by root before, fix it in the Docker container:"
  echo "  sudo chown -R \$(id -u):\$(id -g) \"${INSTALL_DIR}\""
  exit 1
fi

cmake -S "${KALIBR_SRC}" -B "${BUILD_DIR}" \
  -DCMAKE_TOOLCHAIN_FILE="${TROS_WS}/robot_dev_config/aarch64_toolchainfile.cmake" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF \
  -DKALIBR_INSTALL_TO_BUILD=OFF \
  -DCMAKE_INSTALL_PREFIX="${INSTALL_DIR}"

cmake --build "${BUILD_DIR}" -j"$(nproc)"
cmake --install "${BUILD_DIR}"

echo "Done: ${INSTALL_DIR}"
