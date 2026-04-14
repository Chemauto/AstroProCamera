"""Utility functions for saving images, depth data, and point clouds."""

import os
import struct
import numpy as np
import cv2


def save_color_image(image: np.ndarray, path: str):
    """Save a BGR color image to file."""
    _ensure_dir(path)
    cv2.imwrite(path, image)
    print(f"Color image saved: {path}")


def save_depth_raw(depth_data: np.ndarray, path: str):
    """Save raw depth data as numpy .npy file."""
    _ensure_dir(path)
    np.save(path, depth_data)
    print(f"Raw depth saved: {path}")


def save_depth_png(depth_data: np.ndarray, path: str, colormap=cv2.COLORMAP_JET):
    """Save depth as a colored PNG image for visualization."""
    _ensure_dir(path)
    normalized = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    colored = cv2.applyColorMap(normalized, colormap)
    cv2.imwrite(path, colored)
    print(f"Depth image saved: {path}")


def save_depth_raw_png(depth_data: np.ndarray, path: str):
    """Save raw uint16 depth data as 16-bit PNG (lossless)."""
    _ensure_dir(path)
    cv2.imwrite(path, depth_data)
    print(f"Raw depth PNG saved: {path}")


def save_pointcloud_ply(points: np.ndarray, colors: np.ndarray = None, path: str = "output/cloud.ply"):
    """Save point cloud to PLY file.

    Args:
        points: (N, 3) float32 array of 3D coordinates
        colors: optional (N, 3) uint8 array of RGB colors
        path: output file path
    """
    _ensure_dir(path)
    num_points = points.shape[0]
    has_color = colors is not None and colors.shape[0] == num_points

    with open(path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {num_points}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        if has_color:
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
        f.write("end_header\n")

        for i in range(num_points):
            x, y, z = points[i]
            if has_color:
                r, g, b = int(colors[i][0]), int(colors[i][1]), int(colors[i][2])
                f.write(f"{x:.4f} {y:.4f} {z:.4f} {r} {g} {b}\n")
            else:
                f.write(f"{x:.4f} {y:.4f} {z:.4f}\n")

    print(f"Point cloud saved: {path}")


def save_pointcloud_numpy(points: np.ndarray, colors: np.ndarray | None = None, path: str = "output/cloud.npz"):
    """Save point cloud as compressed numpy file."""
    _ensure_dir(path)
    if colors is not None:
        np.savez_compressed(path, points=points, colors=colors)
    else:
        np.savez_compressed(path, points=points)
    print(f"Point cloud numpy saved: {path}")


def _ensure_dir(path: str):
    """Create parent directories if they don't exist."""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
