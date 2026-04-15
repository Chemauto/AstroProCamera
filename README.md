# Carema / Astra Pro

面向 Orbbec Astra Pro 的 Python 工具库。

当前默认链路：

- 深度：OpenCV `CAP_OPENNI2_ASTRA` + Orbbec OpenNI runtime
- 彩色：UVC `/dev/videoX` + OpenCV

这条链路已经验证可用，适合实时预览、点击测距和保存 RGB/深度图。

## 安装

```bash
conda create -n camera python=3.10 -y
conda activate camera
pip install numpy opencv-python

# 重编译带 OpenNI2 支持的 OpenCV
bash scripts/build_opencv_openni2.sh

# 安装仓库内置的 Orbbec OpenNI runtime 和 udev 规则
sudo bash scripts/install_orbbec_openni_runtime.sh
```

如果 OpenNI2 runtime 还没有装到系统路径，也可以临时这样运行：

```bash
bash scripts/run_with_orbbec_openni2.sh python examples/test_opencv_openni.py
```

## 快速开始

实时预览：

```bash
python examples/preview.py
```

单次抓拍：

```bash
python examples/capture.py
```

箱子检测示例：

```bash
python examples/detect_box.py
```

## 预览交互

`examples/preview.py` 当前支持：

- 左侧显示 RGB，右侧显示深度图
- 右侧深度图常驻十字准星
- 鼠标左键点击右侧深度图，测量点击位置附近的深度
- `q` 或 `ESC` 退出

深度图左上角显示的是 `Pick: (x, y) ... mm`。

`examples/detect_box.py` 会在 RGB 图里找箱子轮廓，并在深度图中返回近似距离。

## 代码示例

```python
from astra_camera import AstraCamera

with AstraCamera() as cam:
    frames = cam.get_frames()
    color = frames["color"]      # BGR uint8
    depth = frames["depth"]      # uint16, mm
    depth_mask = frames["depth_mask"]

    h, w = depth.shape
    d = cam.get_depth_at(depth, w // 2, h // 2)
    print(d)
```

返回的 `frames` 结构：

```python
{
    "color": np.ndarray,
    "depth": np.ndarray,
    "depth_raw": np.ndarray,
    "depth_mask": np.ndarray,
    "timestamp": int,
}
```

## 注意事项

- Astra Pro 不支持硬件同步，RGB 和深度来自同一台设备的两条独立链路
- 现在的点击测距以右侧深度图为准，不按左侧 RGB 图坐标测距
- `Center area` 或点击读数是局部有效像素的中值，不是单个像素值
- OpenNI2 后端通常不直接提供 Astra Pro 的 RGB 图像
- 如果 RGB 口不是 `/dev/video2`，修改 [astra_camera/camera.py](/home/xcj/work/Carema/astra_camera/camera.py:31) 的 `color_video_index`
