"""Example: Generate and save a point cloud from depth data."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyorbbecsdk import (
    Pipeline, Config, OBSensorType, OBFormat,
    AlignFilter, OBStreamType, PointCloudFilter,
)
from astra_camera import utils
from astra_camera.depth_processor import depth_to_pointcloud, extract_pointcloud_arrays


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    pipeline = Pipeline()
    config = Config()

    # Configure depth stream
    depth_profiles = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
    if depth_profiles is None:
        print("No depth sensor found.")
        return
    depth_profile = depth_profiles.get_default_video_stream_profile()
    config.enable_stream(depth_profile)

    # Configure color stream
    has_color = False
    try:
        color_profiles = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
        if color_profiles is not None:
            color_profile = color_profiles.get_default_video_stream_profile()
            config.enable_stream(color_profile)
            has_color = True
    except Exception:
        pass

    pipeline.enable_frame_sync()
    pipeline.start(config)

    align_filter = AlignFilter(align_to_stream=OBStreamType.COLOR_STREAM)

    print("Capturing frame for point cloud...")
    # Skip warmup frames
    for _ in range(15):
        pipeline.wait_for_frames(1000)

    while True:
        frames = pipeline.wait_for_frames(3000)
        if frames is None:
            continue

        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if depth_frame is None:
            continue
        if has_color and color_frame is None:
            continue

        # Align depth to color
        aligned = align_filter.process(frames)
        if aligned is None:
            continue
        aligned = aligned.as_frame_set()

        # Generate point cloud
        camera_param = pipeline.get_camera_param()
        aligned_depth = aligned.get_depth_frame()
        aligned_color = aligned.get_color_frame() if has_color else None

        points_frame = depth_to_pointcloud(
            aligned_depth,
            color_frame=aligned_color,
            camera_param=camera_param,
        )

        if points_frame is not None:
            # Save as PLY
            ply_path = os.path.join(output_dir, "point_cloud.ply")
            utils.save_pointcloud_ply(points_frame, ply_path)
            print(f"Point cloud saved to {ply_path}")
        else:
            print("Failed to generate point cloud.")

        break

    pipeline.stop()
    print("Done.")


if __name__ == "__main__":
    main()
