#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENDORED_LIB_DIR="${REPO_ROOT}/third_party/orbbec_openni2/lib"
VENDORED_DRIVER_DIR="${VENDORED_LIB_DIR}/OpenNI2/Drivers"
VENDORED_RULES_FILE="${REPO_ROOT}/third_party/orbbec_openni2/rules/orbbec-usb.rules"

SDK_ROOT="${SDK_ROOT:-}"
SDK_LIB_DIR=""
SDK_DRIVER_DIR=""
RULES_SCRIPT=""
RULES_FILE=""

if [[ -n "${SDK_ROOT}" ]]; then
  SDK_LIB_DIR="${SDK_ROOT}/sdk/libs"
  SDK_DRIVER_DIR="${SDK_LIB_DIR}/OpenNI2/Drivers"
  RULES_SCRIPT="${SDK_ROOT}/rules/install.sh"
fi

if [[ -f "${VENDORED_LIB_DIR}/libOpenNI2.so" && -f "${VENDORED_DRIVER_DIR}/liborbbec.so" ]]; then
  RUNTIME_LIB_DIR="${VENDORED_LIB_DIR}"
  RUNTIME_DRIVER_DIR="${VENDORED_DRIVER_DIR}"
  RULES_FILE="${VENDORED_RULES_FILE}"
elif [[ -n "${SDK_ROOT}" && -f "${SDK_LIB_DIR}/libOpenNI2.so" && -f "${SDK_DRIVER_DIR}/liborbbec.so" ]]; then
  RUNTIME_LIB_DIR="${SDK_LIB_DIR}"
  RUNTIME_DRIVER_DIR="${SDK_DRIVER_DIR}"
else
  echo "Missing Orbbec OpenNI runtime. Populate third_party/orbbec_openni2 or set SDK_ROOT."
  exit 1
fi

install -d /usr/local/lib/OpenNI2/Drivers
install -m 0644 "${RUNTIME_LIB_DIR}/libOpenNI2.so" /usr/local/lib/libOpenNI2.so
ln -sfn /usr/local/lib/libOpenNI2.so /usr/local/lib/libOpenNI2.so.0

if [[ -f "${RUNTIME_LIB_DIR}/OpenNI.ini" ]]; then
  install -m 0644 "${RUNTIME_LIB_DIR}/OpenNI.ini" /usr/local/lib/OpenNI.ini
fi

install -m 0644 "${RUNTIME_DRIVER_DIR}/liborbbec.so" /usr/local/lib/OpenNI2/Drivers/liborbbec.so
install -m 0644 "${RUNTIME_DRIVER_DIR}/libOniFile.so" /usr/local/lib/OpenNI2/Drivers/libOniFile.so
install -m 0644 "${RUNTIME_DRIVER_DIR}/orbbec.ini" /usr/local/lib/OpenNI2/Drivers/orbbec.ini
install -m 0644 "${RUNTIME_DRIVER_DIR}/OniFile.ini" /usr/local/lib/OpenNI2/Drivers/OniFile.ini

if [[ -f "${RULES_FILE}" ]]; then
  install -d /etc/udev/rules.d
  install -m 0644 "${RULES_FILE}" /etc/udev/rules.d/558-orbbec-usb.rules
elif [[ -n "${RULES_SCRIPT}" && -f "${RULES_SCRIPT}" ]]; then
  bash "${RULES_SCRIPT}"
else
  echo "Warning: no Orbbec udev rules file found."
fi

if command -v udevadm >/dev/null 2>&1; then
  udevadm control --reload-rules || true
  udevadm trigger || true
fi

ldconfig

echo "Installed Orbbec OpenNI runtime to /usr/local/lib"
echo "Drivers installed to /usr/local/lib/OpenNI2/Drivers"
echo "udev rules installed to /etc/udev/rules.d/558-orbbec-usb.rules"
