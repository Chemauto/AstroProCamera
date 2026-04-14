"""Depth image processing utilities: colormap, point cloud generation."""

import numpy as np
import cv2

from ._sdk_loader import preload_orbbecsdk

preload_orbbecsdk()

from pyorbbecsdk import (
    PointCloudFilter,
    OBFormat,
)


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


def depth_to_pointcloud(depth_frame, color_image=None, camera_param=None):
    """Generate point cloud from depth frame using pyorbbecsdk PointCloudFilter.

    Args:
        depth_frame: pyorbbecsdk DepthFrame
        color_image: optional BGR numpy array for colored point cloud
        camera_param: camera parameters (from pipeline.get_camera_param())

    Returns:
        pyorbbecsdk PointsFrame, or None on failure.
    """
    pc_filter = PointCloudFilter()
    if camera_param is not None:
        pc_filter.set_camera_param(camera_param)

    has_color = color_image is not None
    point_format = OBFormat.RGB_POINT if has_color else OBFormat.POINT
    pc_filter.set_create_point_format(point_format)

    return pc_filter.process(depth_frame)


def depth_to_pointcloud_numpy(depth_data: np.ndarray, camera_intrinsics: dict) -> dict:
    """Convert depth array to 3D point cloud using camera intrinsics.

    This is a pure numpy implementation that doesn't depend on pyorbbecsdk
    point cloud filter, useful when the SDK filter doesn't support the device.

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
