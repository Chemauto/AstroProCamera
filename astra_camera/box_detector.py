"""Simple box detection and rough depth estimation for Astra Pro."""

from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np

from .camera import MAX_DEPTH, MIN_DEPTH


@dataclass
class BoxDetection:
    contour: np.ndarray
    bbox: tuple[int, int, int, int]
    area: float
    score: float


@dataclass
class BoxDistanceEstimate:
    z_mm: float
    range_mm: float
    xyz_mm: tuple[float, float, float]
    depth_center_xy: tuple[int, int]
    depth_roi: tuple[int, int, int, int]
    sample_count: int


def detect_box(color_image: np.ndarray) -> BoxDetection | None:
    """Detect the strongest box-like quadrilateral in the RGB frame."""
    gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 60, 160)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best: BoxDetection | None = None
    image_area = color_image.shape[0] * color_image.shape[1]
    min_area = max(3000, int(image_area * 0.015))

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue

        approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue

        x, y, w, h = cv2.boundingRect(approx)
        if w < 40 or h < 40:
            continue

        aspect = w / float(h)
        if not 0.4 <= aspect <= 2.5:
            continue

        fill_ratio = area / float(w * h)
        if fill_ratio < 0.6:
            continue

        score = area * fill_ratio
        candidate = BoxDetection(
            contour=approx,
            bbox=(x, y, w, h),
            area=float(area),
            score=float(score),
        )
        if best is None or candidate.score > best.score:
            best = candidate

    return best


def estimate_box_distance(
    depth_data: np.ndarray,
    color_shape: tuple[int, int, int] | tuple[int, int],
    detection: BoxDetection,
    camera_param: dict | None = None,
) -> BoxDistanceEstimate | None:
    """Estimate box distance from the depth map using rough RGB-depth mapping."""
    if depth_data is None or depth_data.ndim != 2:
        return None

    color_h, color_w = color_shape[:2]
    depth_h, depth_w = depth_data.shape
    x, y, w, h = detection.bbox

    center_x = x + w / 2.0
    center_y = y + h / 2.0
    depth_cx = _map_between_sizes(center_x, color_w, depth_w)
    depth_cy = _map_between_sizes(center_y, color_h, depth_h)

    roi_half_w = max(12, int(round(w / color_w * depth_w * 0.22)))
    roi_half_h = max(12, int(round(h / color_h * depth_h * 0.22)))
    align_margin = 16

    x0 = max(0, depth_cx - roi_half_w - align_margin)
    x1 = min(depth_w, depth_cx + roi_half_w + align_margin + 1)
    y0 = max(0, depth_cy - roi_half_h - align_margin)
    y1 = min(depth_h, depth_cy + roi_half_h + align_margin + 1)

    roi = depth_data[y0:y1, x0:x1]
    valid = roi[(roi > MIN_DEPTH) & (roi < MAX_DEPTH)]
    if valid.size == 0:
        return None

    z_mm = float(np.percentile(valid, 35))

    fx = fy = 0.0
    cx = depth_w / 2.0
    cy = depth_h / 2.0
    if camera_param is not None:
        fx = float(camera_param.get("fx", 0.0) or 0.0)
        fy = float(camera_param.get("fy", 0.0) or 0.0)
        cx = float(camera_param.get("cx", cx) or cx)
        cy = float(camera_param.get("cy", cy) or cy)

    if fx > 0 and fy > 0:
        x_mm = (depth_cx - cx) * z_mm / fx
        y_mm = (depth_cy - cy) * z_mm / fy
    else:
        x_mm = 0.0
        y_mm = 0.0

    range_mm = math.sqrt(x_mm * x_mm + y_mm * y_mm + z_mm * z_mm)

    return BoxDistanceEstimate(
        z_mm=z_mm,
        range_mm=range_mm,
        xyz_mm=(x_mm, y_mm, z_mm),
        depth_center_xy=(depth_cx, depth_cy),
        depth_roi=(x0, y0, x1, y1),
        sample_count=int(valid.size),
    )


def annotate_box_detection(
    color_image: np.ndarray,
    depth_image: np.ndarray,
    detection: BoxDetection | None,
    estimate: BoxDistanceEstimate | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw the box detection and the sampled depth region."""
    color_vis = color_image.copy()
    depth_vis = depth_image.copy()

    if detection is None:
        cv2.putText(color_vis, "No box candidate", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(depth_vis, "No box candidate", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return color_vis, depth_vis

    cv2.drawContours(color_vis, [detection.contour], -1, (0, 255, 0), 2)
    x, y, w, h = detection.bbox
    cv2.rectangle(color_vis, (x, y), (x + w, y + h), (0, 200, 255), 2)

    if estimate is None:
        label = "box detected, no depth"
        cv2.putText(color_vis, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(depth_vis, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return color_vis, depth_vis

    x0, y0, x1, y1 = estimate.depth_roi
    depth_cx, depth_cy = estimate.depth_center_xy
    z_text = f"box Z={estimate.z_mm:.0f}mm R={estimate.range_mm:.0f}mm"

    cv2.putText(color_vis, z_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(color_vis, "Approx from depth ROI", (10, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

    cv2.rectangle(depth_vis, (x0, y0), (x1, y1), (0, 255, 0), 2)
    _draw_crosshair(depth_vis, depth_cx, depth_cy)
    cv2.putText(depth_vis, z_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(depth_vis, f"ROI samples={estimate.sample_count}", (10, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    return color_vis, depth_vis


def _draw_crosshair(image: np.ndarray, x: int, y: int) -> None:
    cv2.drawMarker(image, (x, y), (0, 0, 0), markerType=cv2.MARKER_CROSS,
                   markerSize=16, thickness=3, line_type=cv2.LINE_AA)
    cv2.drawMarker(image, (x, y), (0, 255, 0), markerType=cv2.MARKER_CROSS,
                   markerSize=14, thickness=2, line_type=cv2.LINE_AA)


def _map_between_sizes(value: float, src_size: int, dst_size: int) -> int:
    if src_size <= 1 or dst_size <= 1:
        return 0
    mapped = int(round(value * (dst_size - 1) / (src_size - 1)))
    return int(np.clip(mapped, 0, dst_size - 1))
