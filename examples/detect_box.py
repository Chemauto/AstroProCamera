"""Detect a box-like object and estimate its distance from the camera."""

from __future__ import annotations

import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from astra_camera import AstraCamera
from astra_camera.box_detector import (
    annotate_box_detection,
    detect_box,
    estimate_box_distance,
)
from astra_camera.depth_processor import depth_to_colormap


ESC_KEY = 27


def main():
    with AstraCamera() as cam:
        display = DisplayWindow("Astra Pro Box Detect", width=1280, height=480)
        try:
            camera_param = cam.get_camera_param()
        except Exception:
            camera_param = None
        print("Box detect started. Press 'q' or ESC to exit.")

        while True:
            frames = cam.get_frames(timeout_ms=1000)
            if frames is None:
                continue

            color = frames["color"]
            depth = frames["depth"]
            if color is None or depth is None:
                continue

            detection = detect_box(color)
            estimate = estimate_box_distance(depth, color.shape, detection, camera_param) if detection else None

            depth_vis = depth_to_colormap(depth)
            color_vis, depth_vis = annotate_box_detection(color, depth_vis, detection, estimate)

            if detection is not None and estimate is not None:
                x_mm, y_mm, z_mm = estimate.xyz_mm
                print(
                    f"box approx -> X={x_mm:.0f}mm Y={y_mm:.0f}mm "
                    f"Z={z_mm:.0f}mm R={estimate.range_mm:.0f}mm",
                    end="\r",
                    flush=True,
                )

            combined = np.hstack((color_vis, depth_vis))
            if not display.show(combined):
                print()
                break


class DisplayWindow:
    def __init__(self, title: str, width: int, height: int):
        self._title = title
        self._width = width
        self._height = height
        self._mode = None
        self._root = None
        self._label = None
        self._photo = None

    def show(self, image: np.ndarray) -> bool:
        frame = cv2.resize(image, (self._width, self._height))

        if self._mode is None:
            self._init_backend()

        if self._mode == "opencv":
            cv2.imshow(self._title, frame)
            key = cv2.waitKey(1)
            return key not in (ord("q"), ESC_KEY)

        if self._mode == "tk":
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ppm = self._rgb_to_ppm(rgb)
            try:
                self._photo = self._tk.PhotoImage(data=ppm, format="PPM")
                self._label.configure(image=self._photo)
                self._label.image = self._photo
                self._root.update_idletasks()
                self._root.update()
            except self._tk.TclError:
                self._running = False
            return bool(self._running)

        raise RuntimeError("Display backend not initialized")

    def _init_backend(self):
        try:
            cv2.namedWindow(self._title, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self._title, self._width, self._height)
            self._mode = "opencv"
            return
        except cv2.error:
            pass

        import tkinter as tk

        self._tk = tk
        self._root = tk.Tk()
        self._root.title(self._title)
        self._root.geometry(f"{self._width}x{self._height}")
        self._root.resizable(False, False)
        self._running = True
        self._root.bind("<KeyPress-q>", self._stop)
        self._root.bind("<Escape>", self._stop)
        self._root.protocol("WM_DELETE_WINDOW", self._stop)
        self._label = tk.Label(self._root)
        self._label.pack()
        self._mode = "tk"

    def _stop(self, _event=None):
        self._running = False
        if self._root is not None and self._root.winfo_exists():
            self._root.destroy()

    def _rgb_to_ppm(self, rgb: np.ndarray) -> bytes:
        height, width = rgb.shape[:2]
        header = f"P6 {width} {height} 255 ".encode("ascii")
        return header + rgb.tobytes()


if __name__ == "__main__":
    main()
