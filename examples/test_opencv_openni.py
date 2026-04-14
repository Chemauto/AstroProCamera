"""Minimal OpenCV OpenNI2 Astra depth test."""

import cv2
import numpy as np


def robust_center_depth(depth: np.ndarray) -> float:
    h, w = depth.shape
    x = w // 2
    y = h // 2
    for radius in (2, 4, 8, 12):
        roi = depth[max(0, y - radius):min(h, y + radius + 1),
                    max(0, x - radius):min(w, x + radius + 1)]
        valid = roi[roi > 0]
        if valid.size:
            return float(np.median(valid))
    return 0.0


def main():
    cap = cv2.VideoCapture(cv2.CAP_OPENNI2_ASTRA)
    if not cap.isOpened():
        print("Failed to open OpenCV OpenNI2 Astra backend.")
        return

    for _ in range(15):
        cap.grab()

    ok, depth = cap.retrieve(None, cv2.CAP_OPENNI_DEPTH_MAP)
    ok_color, color = cap.retrieve(None, cv2.CAP_OPENNI_BGR_IMAGE)
    ok_mask, mask = cap.retrieve(None, cv2.CAP_OPENNI_VALID_DEPTH_MASK)

    print("depth ok:", ok, "color ok:", ok_color, "mask ok:", ok_mask)
    if depth is not None:
        print("depth shape:", depth.shape, "dtype:", depth.dtype)
        vals = depth[depth > 0]
        if vals.size:
            center = robust_center_depth(depth)
            print("depth min/max/median:", int(vals.min()), int(vals.max()), float(np.median(vals)))
            print("center-area depth:", center, "mm")
    if color is not None:
        print("color shape:", color.shape, "dtype:", color.dtype)
    else:
        print("OpenNI2 backend depth works. Astra Pro RGB should be read from /dev/videoX via OpenCV VideoCapture.")

    cap.release()


if __name__ == "__main__":
    main()
