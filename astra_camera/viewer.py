"""Real-time preview window for Astra Pro camera."""

import cv2
import numpy as np

from .camera import AstraCamera
from .depth_processor import depth_to_colormap


ESC_KEY = 27


class AstraViewer:
    """Real-time viewer showing color and depth side by side.

    Usage:
        viewer = AstraViewer()
        viewer.run()
    """

    def __init__(self, camera: AstraCamera | None = None,
                 window_width=1280, window_height=480,
                 callback=None):
        """
        Args:
            camera: existing AstraCamera instance (created if None)
            window_width: display window width
            window_height: display window height
            callback: optional function(frames_dict) called each frame
        """
        self._own_camera = camera is None
        self._camera = camera if camera is not None else AstraCamera()
        self._window_width = window_width
        self._window_height = window_height
        self._callback = callback
        self._selected_depth_xy: tuple[int, int] | None = None
        self._depth_view: dict | None = None

    def run(self):
        """Start the viewer loop. Press 'q' or ESC to exit."""
        if self._own_camera:
            self._camera.open()

        try:
            self._run_opencv()
        except KeyboardInterrupt:
            pass
        finally:
            if self._own_camera:
                self._camera.close()
            print("Viewer stopped.")

    def _run_opencv(self):
        try:
            cv2.namedWindow("Astra Pro Viewer", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Astra Pro Viewer", self._window_width, self._window_height)
            cv2.setMouseCallback("Astra Pro Viewer", self._on_opencv_mouse)
        except cv2.error:
            self._run_tkinter()
            return

        print("Astra Pro viewer started. Click on the depth image to measure. Press 'q' or ESC to exit.")
        try:
            while True:
                frames = self._camera.get_frames(timeout_ms=1000)
                if frames is None:
                    continue

                combined = self._compose_frame(frames)
                cv2.imshow("Astra Pro Viewer", combined)

                if self._callback:
                    self._callback(frames)

                key = cv2.waitKey(1)
                if key == ord('q') or key == ESC_KEY:
                    break
        finally:
            cv2.destroyAllWindows()

    def _run_tkinter(self):
        import tkinter as tk

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            raise RuntimeError(
                "OpenCV GUI support is unavailable, and tkinter could not connect "
                "to the current X display."
            ) from exc

        root.title("Astra Pro Viewer")
        root.geometry(f"{self._window_width}x{self._window_height}")
        root.resizable(False, False)

        image_label = tk.Label(root)
        image_label.pack()

        state = {"running": True, "photo": None}

        def stop(_event=None):
            state["running"] = False
            if root.winfo_exists():
                root.destroy()

        root.bind("<KeyPress-q>", stop)
        root.bind("<Escape>", stop)
        root.protocol("WM_DELETE_WINDOW", stop)
        image_label.bind("<Button-1>", self._on_tkinter_click)

        print("Astra Pro viewer started. Click on the depth image to measure. Press 'q' or ESC to exit.")

        def update_frame():
            if not state["running"]:
                return

            frames = self._camera.get_frames(timeout_ms=50)
            if frames is not None:
                combined = self._compose_frame(frames)
                rgb = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
                ppm = self._rgb_to_ppm(rgb)
                photo = tk.PhotoImage(data=ppm, format="PPM")
                image_label.configure(image=photo)
                image_label.image = photo
                state["photo"] = photo

                if self._callback:
                    self._callback(frames)

            if state["running"] and root.winfo_exists():
                root.after(1, update_frame)

        try:
            update_frame()
            root.mainloop()
        finally:
            state["running"] = False

    def _compose_frame(self, frames: dict) -> np.ndarray:
        color_image = frames["color"]
        depth_data = frames["depth"]

        half_w = self._window_width // 2

        if color_image is not None:
            color_resized = cv2.resize(color_image, (half_w, self._window_height))
        else:
            color_resized = np.zeros((self._window_height, half_w, 3), dtype=np.uint8)
            cv2.putText(color_resized, "No color data",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if depth_data is not None:
            depth_colormap = depth_to_colormap(depth_data)
            h, w = depth_data.shape
            depth_resized = cv2.resize(depth_colormap, (half_w, self._window_height))
            pick_x, pick_y = self._get_pick_point(w, h)
            pick_depth = self._camera.get_depth_at(depth_data, pick_x, pick_y)

            self._depth_view = {
                "x0": half_w,
                "display_width": half_w,
                "display_height": self._window_height,
                "source_width": w,
                "source_height": h,
            }

            display_x = self._map_source_to_display(pick_x, w, half_w)
            display_y = self._map_source_to_display(pick_y, h, self._window_height)
            self._draw_crosshair(depth_resized, display_x, display_y)

            cv2.putText(depth_resized, f"Pick: ({pick_x}, {pick_y}) {pick_depth:.0f}mm",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(depth_resized, "Click this depth image to measure",
                        (10, self._window_height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        else:
            self._depth_view = None
            depth_resized = np.zeros((self._window_height, half_w, 3), dtype=np.uint8)
            cv2.putText(depth_resized, "No depth data",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return np.hstack((color_resized, depth_resized))

    def _rgb_to_ppm(self, rgb: np.ndarray) -> bytes:
        height, width = rgb.shape[:2]
        header = f"P6 {width} {height} 255 ".encode("ascii")
        return header + rgb.tobytes()

    def _get_pick_point(self, width: int, height: int) -> tuple[int, int]:
        if self._selected_depth_xy is None:
            self._selected_depth_xy = (width // 2, height // 2)

        x, y = self._selected_depth_xy
        x = int(np.clip(x, 0, max(width - 1, 0)))
        y = int(np.clip(y, 0, max(height - 1, 0)))
        self._selected_depth_xy = (x, y)
        return x, y

    def _set_pick_from_display(self, display_x: int, display_y: int) -> None:
        if self._depth_view is None:
            return

        x0 = self._depth_view["x0"]
        display_width = self._depth_view["display_width"]
        display_height = self._depth_view["display_height"]
        source_width = self._depth_view["source_width"]
        source_height = self._depth_view["source_height"]

        if display_x < x0 or display_x >= x0 + display_width:
            return
        if display_y < 0 or display_y >= display_height:
            return

        local_x = display_x - x0
        source_x = self._map_display_to_source(local_x, display_width, source_width)
        source_y = self._map_display_to_source(display_y, display_height, source_height)
        self._selected_depth_xy = (source_x, source_y)

    def _on_opencv_mouse(self, event, x, y, _flags, _userdata):
        if event == cv2.EVENT_LBUTTONDOWN:
            self._set_pick_from_display(x, y)

    def _on_tkinter_click(self, event):
        self._set_pick_from_display(event.x, event.y)

    def _draw_crosshair(self, image: np.ndarray, x: int, y: int) -> None:
        marker_size = 12
        color = (0, 255, 0)
        outline = (0, 0, 0)
        cv2.drawMarker(image, (x, y), outline, markerType=cv2.MARKER_CROSS,
                       markerSize=marker_size + 2, thickness=3, line_type=cv2.LINE_AA)
        cv2.drawMarker(image, (x, y), color, markerType=cv2.MARKER_CROSS,
                       markerSize=marker_size, thickness=2, line_type=cv2.LINE_AA)

    def _map_source_to_display(self, value: int, source_size: int, display_size: int) -> int:
        if source_size <= 1 or display_size <= 1:
            return 0
        return int(round(value * (display_size - 1) / (source_size - 1)))

    def _map_display_to_source(self, value: int, display_size: int, source_size: int) -> int:
        if display_size <= 1 or source_size <= 1:
            return 0
        return int(round(value * (source_size - 1) / (display_size - 1)))
