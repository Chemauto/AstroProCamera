"""Example: Capture and save color image + depth data."""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from astra_camera import AstraCamera, utils


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")

    with AstraCamera() as cam:
        print("Warming up sensor (skip initial frames)...")
        for _ in range(15):
            cam.get_frames()

        print("Capturing frames...")
        frames = cam.get_frames(timeout_ms=3000)
        if frames is None:
            print("Failed to capture frames.")
            return

        timestamp = int(time.time() * 1000)

        # Save color image
        utils.save_color_image(
            frames["color"],
            os.path.join(output_dir, f"color_{timestamp}.png")
        )

        # Save depth as colormap PNG
        utils.save_depth_png(
            frames["depth"],
            os.path.join(output_dir, f"depth_{timestamp}.png")
        )

        # Save raw depth as numpy
        utils.save_depth_raw(
            frames["depth"],
            os.path.join(output_dir, f"depth_{timestamp}.npy")
        )

        # Print center depth
        h, w = frames["depth"].shape
        center_depth = cam.get_depth_at(frames["depth"], w // 2, h // 2)
        print(f"Center-area depth: {center_depth} mm")


if __name__ == "__main__":
    main()
