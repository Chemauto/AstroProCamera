# Astra Pro 相机 Python SDK 封装

面向奥比中光 Astra Pro 的 Python 工具库，默认使用更稳定的
`OpenCV OpenNI2 depth + UVC RGB` 架构，支持实时预览、拍照保存和深度图处理。

## 架构说明

Astra Pro 是旧版 OpenNI 设备。当前默认链路为：

- **深度流**：OpenCV `CAP_OPENNI2_ASTRA` + Orbbec OpenNI runtime
- **彩色流**：普通 UVC `/dev/videoX` + OpenCV

这也是当前在该设备上更稳定、深度值更接近真实毫米值的实现。

## 环境配置

```bash
conda create -n camera python=3.10 -y
conda activate camera
pip install numpy opencv-python

# 将 OpenCV 重编译为带 OpenNI2 支持的版本
bash scripts/build_opencv_openni2.sh

# 安装仓库内置的 Orbbec OpenNI runtime 和 udev 规则
sudo bash scripts/install_orbbec_openni_runtime.sh
```

## 快速使用

```python
from astra_camera import AstraCamera, AstraViewer, utils

# 方式1：上下文管理器
with AstraCamera() as cam:
    frames = cam.get_frames()
    color = frames["color"]    # BGR numpy
    depth = frames["depth"]    # uint16 numpy, 单位 mm

# 方式2：实时预览
viewer = AstraViewer()
viewer.run()  # 按 q 或 ESC 退出

# 保存图片
utils.save_color_image(frames["color"], "output/color.png")
utils.save_depth_png(frames["depth"], "output/depth.png")
utils.save_depth_raw(frames["depth"], "output/depth.npy")
```

## 示例脚本

```bash
python examples/preview.py     # 实时预览彩色+深度
python examples/capture.py     # 拍照保存到 output/
python examples/pointcloud.py  # 生成点云 PLY 文件
```

## OpenCV + OpenNI2 路径

如果你还没有把 runtime 安装到系统路径，可以通过仓库自带包装脚本
加载本地 vendored 的 Orbbec OpenNI runtime：

```bash
bash scripts/run_with_orbbec_openni2.sh python examples/test_opencv_openni.py
```

运行时库位于 `third_party/orbbec_openni2/lib`。

## API 参考

### AstraCamera

| 方法 | 说明 |
|------|------|
| `open()` | 打开相机（默认 UVC 彩色 + OpenNI2 深度） |
| `close()` | 关闭相机释放资源 |
| `get_frames(timeout_ms)` | 获取帧数据，返回 dict |
| `get_depth_at(depth, x, y)` | 获取像素点深度值 (mm) |
| `get_camera_param()` | 获取相机内外参 |

### 帧数据格式

```python
{
    "color": np.ndarray,      # BGR uint8
    "depth": np.ndarray,      # uint16, 单位 mm
    "depth_raw": np.ndarray,  # 原始深度数组
    "depth_mask": np.ndarray, # 有效深度掩码
    "timestamp": int,         # 时间戳
}
```

## 注意事项

- 深度数据单位为毫米 (mm)
- Astra Pro 不支持硬件帧同步；默认 RGB 与深度来自同一物理设备的两条独立链路
- OpenNI2 后端通常不直接提供 Astra Pro RGB 图像，彩色图请走 `/dev/videoX`
- 需要 sudo 权限安装 udev 规则
# AstroProCamera
