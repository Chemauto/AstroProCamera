"""Example: Real-time preview of color and depth streams."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from astra_camera import AstraViewer


def main():
    viewer = AstraViewer(window_width=1280, window_height=480)
    viewer.run()


if __name__ == "__main__":
    main()
