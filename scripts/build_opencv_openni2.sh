#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CONDA_PREFIX:-}" ]]; then
  echo "CONDA_PREFIX is not set. Activate the target conda environment first."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-$CONDA_PREFIX/bin/python}"
PIP_BIN="${PIP_BIN:-$CONDA_PREFIX/bin/pip}"
OPENCV_VERSION="${OPENCV_VERSION:-4.12.0.88}"
OPENNI2_INCLUDE_DIR="${OPENNI2_INCLUDE_DIR:-/usr/include/openni2}"
OPENNI2_LIBRARY="${OPENNI2_LIBRARY:-/usr/lib/x86_64-linux-gnu/libOpenNI2.so}"
BUILD_LOG_DIR="${BUILD_LOG_DIR:-$(pwd)/output}"
BUILD_LOG_FILE="${BUILD_LOG_DIR}/opencv_openni2_build.log"

mkdir -p "${BUILD_LOG_DIR}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python not found: ${PYTHON_BIN}"
  exit 1
fi

if [[ ! -f "${OPENNI2_LIBRARY}" ]]; then
  echo "OpenNI2 library not found: ${OPENNI2_LIBRARY}"
  exit 1
fi

if [[ ! -d "${OPENNI2_INCLUDE_DIR}" ]]; then
  echo "OpenNI2 include directory not found: ${OPENNI2_INCLUDE_DIR}"
  exit 1
fi

export CMAKE_ARGS="-DWITH_OPENNI2=ON -DOpenNI2_INCLUDE_DIR=${OPENNI2_INCLUDE_DIR} -DOpenNI2_LIBRARY=${OPENNI2_LIBRARY}"
export MAKEFLAGS="-j$(nproc)"

echo "Building opencv-python ${OPENCV_VERSION} with OpenNI2 support"
echo "Python: ${PYTHON_BIN}"
echo "OpenNI2 include: ${OPENNI2_INCLUDE_DIR}"
echo "OpenNI2 library: ${OPENNI2_LIBRARY}"
echo "Build log: ${BUILD_LOG_FILE}"

"${PIP_BIN}" install --upgrade pip setuptools wheel 2>&1 | tee "${BUILD_LOG_FILE}"
"${PIP_BIN}" install --force-reinstall --no-binary opencv-python --no-cache-dir "opencv-python==${OPENCV_VERSION}" 2>&1 | tee -a "${BUILD_LOG_FILE}"

"${PYTHON_BIN}" - <<'PY'
import cv2

print("cv2 version:", cv2.__version__)
for line in cv2.getBuildInformation().splitlines():
    if "OpenNI2:" in line or "Orbbec:" in line:
        print(line)

cap = cv2.VideoCapture(cv2.CAP_OPENNI2_ASTRA)
print("CAP_OPENNI2_ASTRA opened:", cap.isOpened())
cap.release()
PY
