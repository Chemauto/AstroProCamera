"""Astra Pro camera wrapper using OpenCV OpenNI2 depth + UVC color."""

from __future__ import annotations

import time

import cv2
import numpy as np


MIN_DEPTH = 20      # mm
MAX_DEPTH = 10000   # mm

OPENNI_OUTPUT_MODES = {
    (640, 480, 30): cv2.CAP_OPENNI_VGA_30HZ,
    (320, 240, 30): cv2.CAP_OPENNI_QVGA_30HZ,
    (320, 240, 60): cv2.CAP_OPENNI_QVGA_60HZ,
}


class AstraCamera:
    """High-level wrapper for Astra Pro.

    Astra Pro depth works reliably through OpenCV's `CAP_OPENNI2_ASTRA`
    backend after the Orbbec OpenNI runtime is installed. RGB is provided
    through the UVC `/dev/videoX` interface.
    """

    def __init__(
        self,
        color_video_index: int = 2,
        color_width: int = 640,
        color_height: int = 480,
        depth_width: int = 640,
        depth_height: int = 480,
        depth_fps: int = 30,
    ):
        self._color_video_index = color_video_index
        self._color_width = color_width
        self._color_height = color_height
        self._depth_width = depth_width
        self._depth_height = depth_height
        self._depth_fps = depth_fps

        self._depth_cap: cv2.VideoCapture | None = None
        self._color_cap: cv2.VideoCapture | None = None
        self._opened = False
        self._last_depth_shape = (depth_height, depth_width)

    def open(self):
        """Open the Astra Pro depth and color streams."""
        if self._opened:
            return

        self._open_depth_stream()
        self._open_color_stream()
        self._opened = True

    def close(self):
        """Release camera resources."""
        if self._depth_cap is not None:
            self._depth_cap.release()
            self._depth_cap = None
        if self._color_cap is not None:
            self._color_cap.release()
            self._color_cap = None
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened

    def get_frames(self, timeout_ms: int = 1000) -> dict | None:
        """Return the latest depth frame plus the latest UVC color frame."""
        if not self._opened:
            raise RuntimeError("Camera is not opened. Call open() first.")

        depth_data = None
        depth_mask = None
        deadline = time.monotonic() + timeout_ms / 1000.0

        while time.monotonic() < deadline:
            if self._depth_cap is None or not self._depth_cap.grab():
                continue

            ok_depth, depth = self._depth_cap.retrieve(None, cv2.CAP_OPENNI_DEPTH_MAP)
            ok_mask, mask = self._depth_cap.retrieve(None, cv2.CAP_OPENNI_VALID_DEPTH_MASK)
            if not ok_depth or depth is None:
                continue

            depth_data = self._sanitize_depth(depth)
            if ok_mask and mask is not None:
                depth_mask = mask.astype(np.uint8, copy=False)
            self._last_depth_shape = depth_data.shape
            break

        color_image = None
        if self._color_cap is not None and self._color_cap.isOpened():
            ret, frame = self._color_cap.read()
            if ret:
                color_image = frame

        if depth_data is None and color_image is None:
            return None

        return {
            "color": color_image,
            "depth": depth_data,
            "depth_raw": depth_data,
            "depth_mask": depth_mask,
            "timestamp": int(time.time() * 1000),
        }

    def get_depth_at(self, depth_data: np.ndarray, x: int, y: int) -> float:
        """Return a robust depth estimate near pixel `(x, y)` in mm."""
        if depth_data is None or depth_data.ndim != 2:
            return 0.0

        height, width = depth_data.shape
        if not (0 <= x < width and 0 <= y < height):
            return 0.0

        for radius in (2, 4, 8, 12):
            x0 = max(0, x - radius)
            x1 = min(width, x + radius + 1)
            y0 = max(0, y - radius)
            y1 = min(height, y + radius + 1)
            roi = depth_data[y0:y1, x0:x1]
            valid = roi[(roi > MIN_DEPTH) & (roi < MAX_DEPTH)]
            if valid.size:
                return float(np.median(valid))

        return 0.0

    def get_camera_param(self):
        """Return best-effort depth camera parameters from OpenNI2."""
        if self._depth_cap is None:
            raise RuntimeError("Camera is not opened. Call open() first.")

        focal_length = self._get_openni_property(
            cv2.CAP_OPENNI_DEPTH_GENERATOR_FOCAL_LENGTH,
            cv2.CAP_PROP_OPENNI_FOCAL_LENGTH,
        )
        baseline = self._get_openni_property(
            cv2.CAP_OPENNI_DEPTH_GENERATOR_BASELINE,
            cv2.CAP_PROP_OPENNI_BASELINE,
        )

        height, width = self._last_depth_shape
        return {
            "width": width,
            "height": height,
            "fx": focal_length,
            "fy": focal_length,
            "cx": width / 2.0,
            "cy": height / 2.0,
            "baseline": baseline,
        }

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _open_depth_stream(self) -> None:
        self._depth_cap = cv2.VideoCapture(cv2.CAP_OPENNI2_ASTRA)
        if not self._depth_cap.isOpened():
            raise RuntimeError(
                "Failed to open OpenCV OpenNI2 Astra backend. "
                "Install the Orbbec OpenNI runtime with "
                "`sudo bash scripts/install_orbbec_openni_runtime.sh`."
            )

        requested_mode = OPENNI_OUTPUT_MODES.get(
            (self._depth_width, self._depth_height, self._depth_fps)
        )
        default_mode = OPENNI_OUTPUT_MODES[(640, 480, 30)]
        if requested_mode is not None and requested_mode != default_mode:
            self._depth_cap.set(cv2.CAP_PROP_OPENNI_OUTPUT_MODE, requested_mode)

        for _ in range(5):
            self._depth_cap.grab()

        ok_depth, depth = self._depth_cap.retrieve(None, cv2.CAP_OPENNI_DEPTH_MAP)
        if ok_depth and depth is not None:
            self._last_depth_shape = depth.shape
            print(
                f"Depth stream opened: {depth.shape[1]}x{depth.shape[0]} "
                "via OpenCV CAP_OPENNI2_ASTRA"
            )
        else:
            print("Depth stream opened via OpenCV CAP_OPENNI2_ASTRA")

    def _open_color_stream(self) -> None:
        self._color_cap = cv2.VideoCapture(self._color_video_index)
        if self._color_cap.isOpened():
            self._color_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._color_width)
            self._color_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._color_height)
            actual_w = int(self._color_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._color_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Color stream opened: {actual_w}x{actual_h} via /dev/video{self._color_video_index}")
        else:
            print(f"Warning: failed to open /dev/video{self._color_video_index} for color stream")

    def _get_openni_property(self, *properties: int) -> float:
        if self._depth_cap is None:
            return 0.0

        for prop in properties:
            try:
                value = float(self._depth_cap.get(prop))
            except Exception:
                continue
            if np.isfinite(value) and value > 0:
                return value
        return 0.0

    def _sanitize_depth(self, depth: np.ndarray) -> np.ndarray:
        depth_mm = np.asarray(depth, dtype=np.uint16)
        return np.where(
            (depth_mm > MIN_DEPTH) & (depth_mm < MAX_DEPTH),
            depth_mm,
            0,
        ).astype(np.uint16)
