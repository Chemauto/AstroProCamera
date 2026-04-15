"""Depth image processing utilities: colormap, point cloud generation."""

import numpy as np
import cv2


def depth_to_colormap(depth_data: np.ndarray, colormap=cv2.COLORMAP_JET) -> np.ndarray:
    """Convert uint16 depth array to a colored visualization (BGR).

    Args:
        depth_data: uint16 array (H, W), values in mm.
        colormap: OpenCV colormap enum.

    Returns:
        BGR uint8 array (H, W, 3).
    """
    normalized = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    colored = cv2.applyColorMap(normalized, colormap)
    return colored


def depth_to_pointcloud_numpy(depth_data: np.ndarray, camera_intrinsics: dict) -> dict:
    """Convert depth array to 3D point cloud using camera intrinsics.

    Args:
        depth_data: uint16 array (H, W) in mm
        camera_intrinsics: dict with keys "fx", "fy", "cx", "cy"
            (focal lengths and principal point)

    Returns:
        dict with "points" (N, 3) float32 array where invalid points are (0,0,0)
    """
    h, w = depth_data.shape
    fx = camera_intrinsics.get("fx", 570.0)
    fy = camera_intrinsics.get("fy", 570.0)
    cx = camera_intrinsics.get("cx", w / 2.0)
    cy = camera_intrinsics.get("cy", h / 2.0)

    # Create pixel coordinate grids
    u, v = np.meshgrid(np.arange(w), np.arange(h))

    # Convert to 3D: Z * (u - cx) / fx, Z * (v - cy) / fy, Z
    z = depth_data.astype(np.float32)
    x = z * (u - cx) / fx
    y = z * (v - cy) / fy

    points = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    return {"points": points}
