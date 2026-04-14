#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OPENNI_LIB_DIR="${REPO_ROOT}/third_party/orbbec_openni2/lib"
OPENNI_DRIVER_DIR="${OPENNI_LIB_DIR}/OpenNI2/Drivers"

if [[ ! -f "${OPENNI_LIB_DIR}/libOpenNI2.so" ]]; then
  echo "Missing local Orbbec OpenNI runtime: ${OPENNI_LIB_DIR}/libOpenNI2.so"
  exit 1
fi

if [[ ! -d "${OPENNI_DRIVER_DIR}" ]]; then
  echo "Missing local Orbbec OpenNI drivers: ${OPENNI_DRIVER_DIR}"
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <command> [args...]"
  exit 1
fi

if [[ ! -e "${OPENNI_LIB_DIR}/libOpenNI2.so.0" ]]; then
  ln -sfn libOpenNI2.so "${OPENNI_LIB_DIR}/libOpenNI2.so.0"
fi

export OPENNI2_REDIST="${OPENNI_LIB_DIR}"
export OPENNI2_DRIVERS_PATH="${OPENNI_DRIVER_DIR}"
export LD_LIBRARY_PATH="${OPENNI_LIB_DIR}:${LD_LIBRARY_PATH:-}"

exec "$@"
