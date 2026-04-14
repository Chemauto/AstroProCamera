#!/usr/bin/env python3
"""实时预览彩色图和深度图， 按 s 保存, 按 q 退出"""

import sys
import os
import time
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from astra_camera import AstraCamera
from astra_camera.depth_processor import depth_to_colormap
from astra_camera import utils

ESC_KEY = 27


def main():
    cam = AstraCamera()
    cam.open()

    cv2.namedWindow("Astra Pro", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Astra Pro", 1280, 480)

    print("Astra Pro 实时预览已启动")
    print("按 's' 保存图片, 按 'q' 或 ESC 退出")

    save_count = 0
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    try:
        while True:
            frames = cam.get_frames(timeout_ms=1000)
            if frames is None:
                continue
            color = frames.get("color")
            depth = frames.get("depth")
            if color is None and depth is None:
                continue
            half_w = 640
            half_h = 480
            # 彩色图面板
            if color is not None:
                color_resized = cv2.resize(color, (half_w, half_h))
            else:
                color_resized = np.zeros((half_h, half_w, 3), dtype=np.uint8)
                cv2.putText(color_resized, "No color",
                             (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            # 深度图面板
            if depth is not None:
                depth_colored = depth_to_colormap(depth)
                h, w = depth.shape
                center_depth = cam.get_depth_at(depth, w // 2, h // 2)
                cv2.putText(depth_colored, f"Center: {center_depth}mm",
                             (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                depth_resized = cv2.resize(depth_colored, (half_w, half_h))
            else:
                depth_resized = np.zeros((half_h, half_w, 3), dtype=np.uint8)
                cv2.putText(depth_resized, "No depth",
                             (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            combined = np.hstack((color_resized, depth_resized))
            cv2.imshow("Astra Pro", combined)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                if color is not None:
                    color_path = os.path.join(output_dir, f"color_{timestamp}.png")
                    utils.save_color_image(color, color_path)
                if depth is not None:
                    depth_colored = depth_to_colormap(depth)
                    depth_path = os.path.join(output_dir, f"depth_{timestamp}.png")
                    utils.save_depth_png(depth, depth_path)
                    raw_path = os.path.join(output_dir, f"depth_{timestamp}.npy")
                    utils.save_depth_raw(depth, raw_path)
                save_count += 1
                print(f"已保存第 {save_count} 组图片到 {output_dir}")
                if depth is not None:
                    print(f"  Center depth: {cam.get_depth_at(depth, w // 2, h // 2)}mm")
            elif key == ord('q') or key == ESC_KEY:
                break
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        cam.close()
        print(f"程序退出，共保存了 {save_count} 组图片")


if __name__ == "__main__":
    main()
