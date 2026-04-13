# Kalibr — 独立 CMake 构建使用指南

本文档说明如何**不依赖 ROS** 编译和使用 kalibr 标定工具。

---

## 目录

- [依赖项安装](#依赖项安装)
- [编译](#编译)
- [X5 交叉编译](#x5-交叉编译)
- [环境配置](#环境配置)
- [数据集格式](#数据集格式)
- [标定目标配置](#标定目标配置)
- [相机标定](#相机标定-kalibr_calibrate_cameras)
- [相机IMU联合标定](#相机imu联合标定-kalibr_calibrate_imu_camera)
- [滚动快门标定](#滚动快门标定-kalibr_calibrate_rs_cameras)
- [可视化工具](#可视化工具)
- [IMU参数YAML格式](#imu参数yaml格式)
- [camchain-YAML格式](#camchain-yaml格式)
- [输出文件说明](#输出文件说明)
- [常见问题](#常见问题)
- [完整示例](#完整示例)

---

## 依赖项安装

Ubuntu 20.04 环境：

```bash
sudo apt-get install -y \
    cmake build-essential \
    python3 python3-dev python3-pip \
    libboost-all-dev \
    libeigen3-dev \
    libsuitesparse-dev \
    libtbb-dev \
    libopencv-dev \
    libv4l-dev \
    python3-numpy python3-scipy python3-matplotlib \
    python3-wxgtk4.0 \
    python3-yaml

# Python shebang 兼容（scripts 使用 #!/usr/bin/env python）
sudo ln -sf /usr/bin/python3 /usr/bin/python
```

---

## 编译

```bash
cd /path/to/kalibr
mkdir -p build_standalone && cd build_standalone

# 配置（Release：优化编译，适合日常使用与部署；调试可加 -DCMAKE_BUILD_TYPE=Debug）
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF

# 编译（使用所有核心，首次约 30~60 分钟）
make -j$(nproc)
```

### CMake 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `CMAKE_BUILD_TYPE` | 未设置 | 单配置生成器（Unix Makefiles、Ninja）下生效。发布与板端部署建议 **`Release`**（`-O3 -DNDEBUG` 等）；调试使用 **`Debug`**。未指定时 CMake 可能不启用 `-O`，性能较差 |
| `BUILD_TESTING` | `ON` | 是否编译测试目标 |
| `KALIBR_BUILD_TIER2` | `ON` | 编译完整模块（关闭则只编译底层库） |
| `OpenCV_DIR` | 自动 | 显式指定 OpenCV 路径。若环境中有多个 OpenCV（如 /usr/local 自编译 4.9 + apt 4.2），建议强制使用系统版：`-DOpenCV_DIR=/usr/lib/x86_64-linux-gnu/cmake/opencv4` |

### X5 交叉编译

在 X5（aarch64）平台上交叉编译 kalibr，需使用项目已有的交叉编译环境和 sysroot。

**前置条件**

1. 已获取并加载交叉编译 Docker 镜像（见 [README 交叉编译环境搭建](https://github.com/deepmirrorinc/LooperHub#交叉编译环境搭建)）
2. 在 Docker 内进入 `tros_ws` 目录
3. 确保 `sysroot_docker` 子模块已初始化（`git submodule update --init`）

**步骤**

```bash
# 1. 进入交叉编译 Docker 后，切到 tros_ws
cd /path/to/LooperHub/tros_ws

# 2. 配置 X5 交叉编译环境（与 build.sh -p X5 一致）
export TARGET_ARCH=aarch64
export TARGET_TRIPLE=aarch64-linux-gnu
export CROSS_COMPILE=/usr/bin/$TARGET_TRIPLE-

# 3. 确保 sysroot 指向 X5
rm -f ../sysroot_docker/usr
ln -s "$(pwd)/../sysroot_docker/usr_x5" "$(pwd)/../sysroot_docker/usr"

# 4. 进入 kalibr 并创建构建目录
cd src/kalibr
mkdir -p build_standalone_x5 && cd build_standalone_x5

# 5. 使用项目 toolchain 配置 CMake（路径相对于 build_standalone_x5）
cmake .. \
  -DCMAKE_TOOLCHAIN_FILE="../../../robot_dev_config/aarch64_toolchainfile.cmake" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF

# 6. 编译
make -j$(nproc)

# 7. 安装到 build/install（仅拷贝 install 目录到设备即可）
make install
```

scp -r install root@192.168.137.100:/userdata/calibr
```

在 X5 上使用：

```bash
source /userdata/calibr/install/setup_kalibr.sh

kalibr_calibrate_cameras --help
  kalibr_calibrate_cameras \
    --folder /userdata/calibr-data/cam \
    --topics cam0 cam1 cam2 \
    --models pinhole-equi pinhole-equi pinhole-equi \
    --target /userdata/calibr/target_aprilgrid6x6_055.yaml
```


**说明**

- 依赖（Boost、Eigen3、OpenCV、SuiteSparse、TBB、Python3）从 `sysroot_docker/usr_x5` 获取，无需在宿主机单独安装
- **Release 构建**：步骤 5 中已使用 `-DCMAKE_BUILD_TYPE=Release`；若曾用 Debug 或未指定类型配置过，请删除构建目录或 `CMakeCache.txt` 后重新 `cmake`，否则会沿用旧缓存
- **必须在执行 `cmake` 的同一终端里先完成步骤 2 的 `export`（`CROSS_COMPILE` 等）**。若未设置交叉编译器，CMake 会使用宿主机 `g++` 并从 `/usr/lib/x86_64-linux-gnu` 找 Boost，随后易出现 Threads / Eigen3 等与交叉编译不一致的错误
- Eigen3 的 CMake 包在 `sysroot_docker/usr/share/eigen3/cmake`；本仓库 Kalibr 的 `CMakeLists.txt` 在检测到 `CMAKE_SYSROOT` 时会自动把 `<sysroot>/usr` 加入 `CMAKE_PREFIX_PATH`，无需改工具链。若仍报找不到 Eigen3，请确认 `usr` 已正确符号链接到 `usr_x5`（步骤 3）
- 若 OpenCV 查找失败，可显式指定：`-DOpenCV_DIR=../../../sysroot_docker/usr/lib/aarch64-linux-gnu/cmake/opencv4`（路径相对于 build 目录）
- 编译产物为 aarch64 可执行文件和 `.so`，需拷贝到 X5 板子上运行
- 在 X5 上使用前，需安装对应 Python 依赖（numpy、scipy、matplotlib、wx、pyyaml 等），或通过 pip 安装

**部署到 X5 及使用**

**方式一：make install 生成 install 目录（推荐）**

编译完成后执行 `make install`，会在 build 目录下生成 `install/`，仅需拷贝该目录到设备：

```bash
cd build_standalone_x5
make -j$(nproc)
make install
# install/ 位于 build_standalone_x5/install/
scp -r install root@<X5_IP>:/userdata/kalibr_install
```

在 X5 上使用：

```bash
source /userdata/kalibr_install/setup_kalibr.sh
kalibr_calibrate_cameras --help
```

默认安装到 `build/install`（由 `KALIBR_INSTALL_TO_BUILD=ON` 控制）。若需安装到系统路径，配置时加 `-DKALIBR_INSTALL_TO_BUILD=OFF`。

**X5 上需安装的 Python 依赖**：

```bash
pip3 install numpy scipy pyyaml
# 无显示器时：export MPLBACKEND=Agg
```

- **图像读取**：由 C++ OpenCV imgcodecs 完成，无需 Python cv2/Pillow。
- **matplotlib**：可选。无 matplotlib 时，标定正常完成，报告输出为 .txt 而非 .pdf；`--plot` 需安装 matplotlib。

**主要命令**：`kalibr_calibrate_cameras`、`kalibr_calibrate_imu_camera`、`kalibr_calibrate_rs_cameras`、`kalibr_create_target_pdf`

---

## 环境配置

每次新开终端执行一次 source：

```bash
source /path/to/kalibr/setup_kalibr.sh
```

设置完成后可直接调用所有 `kalibr_*` 命令。验证安装：

```bash
kalibr_calibrate_cameras --help
```

无显示器的服务器或 Docker 中，需设置 matplotlib 后端：

```bash
export MPLBACKEND=Agg
```

---

## 数据集格式

无 ROS 模式使用**文件夹数据集**格式。

### 相机图像数据集

```
dataset/
  cam0/
    images.csv          <- 必须，时间戳索引
    image_000000.png
    image_000001.png
    ...
  cam1/
    images.csv
    image_000000.png
    ...
```

**images.csv 格式**（每行：时间戳_ns,文件名）：

```
# timestamp_ns,filename
1609459200000000000,image_000000.png
1609459200033333333,image_000001.png
1609459200066666666,image_000002.png
```

说明：
- 时间戳单位为纳秒（ns），若值 < 1e12 则自动识别为秒并转换
- 文件名为相对于 images.csv 所在目录的路径
- 以 `#` 开头的行为注释，自动跳过

### IMU 数据集

```
dataset/
  imu.csv               <- IMU 测量数据（位于 dataset 根目录）
```

**imu.csv 格式**（每行：时间戳_ns,gx,gy,gz,ax,ay,az）：

```
# timestamp_ns,gx,gy,gz,ax,ay,az
1609459200000000000,0.01,-0.02,0.003,0.12,-0.05,9.81
1609459200002000000,0.01,-0.02,0.003,0.12,-0.05,9.81
```

说明：
- 角速度 gx,gy,gz 单位：rad/s
- 线加速度 ax,ay,az 单位：m/s²
- 典型 IMU 采样率：400 Hz（每 2.5ms 一条）

---

## 标定目标配置

标定目标通过 `--target YAML` 指定。

### AprilGrid（推荐）

```yaml
# target_aprilgrid.yaml
target_type: 'aprilgrid'
tagCols: 6          # AprilTag 列数
tagRows: 6          # AprilTag 行数
tagSize: 0.055      # 单个 tag 边长 [m]
tagSpacing: 0.3     # tag 间距与 tagSize 的比值（无量纲）
codeOffset: 0       # 起始 tag ID 偏移（默认 0）
```

### Checkerboard（棋盘格）

```yaml
target_type: 'checkerboard'
targetCols: 6            # 内角点列数
targetRows: 7            # 内角点行数
rowSpacingMeters: 0.06   # 行方向格子尺寸 [m]
colSpacingMeters: 0.06   # 列方向格子尺寸 [m]
```

### Circlegrid（圆形阵列）

```yaml
target_type: 'circlegrid'
targetCols: 6
targetRows: 7
spacingMeters: 0.02      # 圆心间距 [m]
asymmetricGrid: False    # True 为非对称排列
```

---

## 相机标定 kalibr_calibrate_cameras

标定单相机或多相机系统的内参和相机间外参（基线）。

### 基本用法

```bash
# 单相机
kalibr_calibrate_cameras \
  --folder /data/dataset \
  --topics cam0 \
  --models pinhole-radtan \
  --target /data/aprilgrid.yaml \
  --dont-show-report

# 双相机（stereo）
kalibr_calibrate_cameras \
  --folder /data/dataset \
  --topics cam0 cam1 \
  --models pinhole-radtan pinhole-radtan \
  --target /data/aprilgrid.yaml \
  --bag-freq 4 \
  --dont-show-report
```

### 参数说明

**必填参数**

| 参数 | 说明 |
|------|------|
| `--topics NAME [NAME ...]` | 子文件夹名列表，与 `--models` 一一对应，如 `cam0 cam1` |
| `--models MODEL [MODEL ...]` | 每个相机的镜头模型，见下方相机模型列表 |
| `--target YAML` | 标定目标配置文件路径 |

**数据源（二选一）**

| 参数 | 说明 |
|------|------|
| `--folder PATH` | 文件夹数据集根目录（无 ROS 模式，推荐） |
| `--bag PATH` | ROS bag 文件（需要 ROS 环境） |

**数据筛选**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--bag-freq HZ` | 无限制 | 最大图像采样频率 [Hz]，推荐 4~10 |
| `--bag-from-to T0 T1` | 全部 | 只处理数据集内 [T0, T1] 秒的图像 |
| `--approx-sync SEC` | 0.02 | 多相机时间同步容差 [s] |

**优化器设置**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--qr-tol VAL` | 0.02 | QR 分解阈值，越小越严格 |
| `--mi-tol VAL` | 0.2 | 互信息阈值，越大保留图像越少；-1 强制使用全部 |
| `--no-shuffle` | — | 禁用处理顺序随机化 |

**离群点过滤**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--no-outliers-removal` | — | 禁用角点离群点过滤 |
| `--no-final-filtering` | — | 禁用最终过滤阶段 |
| `--min-views-outlier N` | 20 | 初始化统计量所需最小视角数 |
| `--use-blakezisserman` | — | 启用 Blake-Zisserman M-估计器（鲁棒性更强） |
| `--plot-outliers` | — | 绘制离群点检测过程（较慢） |

**输出控制**

| 参数 | 说明 |
|------|------|
| `--dont-show-report` | 不弹出 PDF 报告（无显示器时必须加） |
| `--verbose` | 详细调试输出（会禁用图表） |
| `--show-extraction` | 实时显示角点提取（需要显示器） |
| `--plot` | 标定过程中实时绘图 |
| `--export-poses` | 额外输出优化后的位姿 CSV（time_ns, tx, ty, tz, qx, qy, qz, qw） |

### 相机模型

| 模型名 | 投影 | 畸变 | 适用场景 |
|--------|------|------|----------|
| `pinhole-radtan` | 针孔 | 径向+切向（k1,k2,p1,p2） | 普通工业相机、标准镜头 |
| `pinhole-equi` | 针孔 | 等距（k1,k2,k3,k4） | 鱼眼/广角镜头（推荐） |
| `pinhole-fov` | 针孔 | FOV（w） | 广角镜头（简化） |
| `omni-none` | 全向（UCM） | 无 | 鱼眼相机 |
| `omni-radtan` | 全向 | 径向+切向 | 鱼眼+畸变 |
| `eucm-none` | 扩展统一（EUCM） | 无 | 广角/鱼眼（推荐） |
| `ds-none` | 双球面（DS） | 无 | 鱼眼（Double Sphere） |

### 输出文件

结果保存在 `--folder` 指定的数据集根目录：

| 文件 | 说明 |
|------|------|
| `*-camchain.yaml` | 相机链参数（内参、外参基线，供后续使用） |
| `*-results-cam.txt` | 详细文字结果（误差统计、参数值） |
| `*-report-cam.pdf` | 可视化 PDF 报告（重投影误差图、姿态分布图） |

---

## 相机IMU联合标定 kalibr_calibrate_imu_camera

标定相机相对于 IMU 的空间外参（T_cam_imu）和时间偏移（time_delay）。

### 基本用法

```bash
# 先完成相机内参标定，再进行联合标定
kalibr_calibrate_imu_camera \
  --folder /data/dataset \
  --cams /data/dataset/dataset-camchain.yaml \
  --imu /data/imu0.yaml \
  --target /data/aprilgrid.yaml \
  --dont-show-report
```

### 参数说明

**必填参数**

| 参数 | 说明 |
|------|------|
| `--cams YAML` | 相机链配置（来自 kalibr_calibrate_cameras 的输出） |
| `--imu YAML [YAML ...]` | IMU 噪声参数 YAML，可指定多个 IMU（第一个为参考 IMU） |
| `--target YAML` | 标定目标文件 |

**数据源（二选一）**

| 参数 | 说明 |
|------|------|
| `--folder PATH` | 文件夹数据集根目录，需含 cam0/（等）子目录及根目录下的 imu.csv |
| `--bag PATH` | ROS bag 文件 |

**数据筛选**

| 参数 | 说明 |
|------|------|
| `--bag-freq HZ` | 图像采样最大频率（推荐 4） |
| `--bag-from-to T0 T1` | 时间截断范围 [s] |
| `--perform-synchronization` | 对数据进行软件时间同步 |

**优化器设置**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-iter N` | 30 | 最大迭代次数 |
| `--no-time-calibration` | — | 禁用时间偏移估计 |
| `--timeoffset-padding SEC` | 0.03 | 时间偏移搜索范围 [s] |
| `--recompute-camera-chain-extrinsics` | — | 重新估计相机链外参 |
| `--reprojection-sigma PX` | 1.0 | 重投影误差先验标准差 [px] |
| `--recover-covariance` | — | 输出协方差矩阵 |
| `--imu-delay-by-correlation` | — | 用互相关法估计 IMU 初始时延 |
| `--imu-models MODEL [...]` | calibrated | IMU 模型，可选：`calibrated`、`scale-misalignment`、`scale-misalignment-size-effect` |

**输出控制**

| 参数 | 说明 |
|------|------|
| `--dont-show-report` | 不弹出 PDF 报告 |
| `--verbose` | 详细输出 |
| `--show-extraction` | 实时显示提取 |
| `--export-poses` | 输出位姿 CSV |

### 输出文件

| 文件 | 说明 |
|------|------|
| `*-camchain.yaml` | 更新的相机链（含 T_cam_imu） |
| `*-imu.yaml` | 更新的 IMU 参数（含时延估计） |
| `*-results-imucam.txt` | 详细文字结果 |
| `*-report-imucam.pdf` | 可视化 PDF 报告 |

---

## 滚动快门标定 kalibr_calibrate_rs_cameras

标定滚动快门（Rolling Shutter）相机的内参及逐行读出时间。

### 基本用法

```bash
kalibr_calibrate_rs_cameras \
  --folder /data/dataset \
  --topic cam0 \
  --model pinhole-radtan-rs \
  --frame-rate 30 \
  --inverse-feature-variance 1 \
  --target /data/aprilgrid.yaml \
  --dont-show-report
```

### 参数说明

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `--topic NAME` | 是 | — | 子文件夹名（如 `cam0`） |
| `--model MODEL` | 是 | — | 相机模型，格式：`<投影>-<畸变>-rs`，如 `pinhole-radtan-rs`、`pinhole-equi-rs` |
| `--frame-rate FPS` | 是 | — | 相机近似帧率（fps） |
| `--inverse-feature-variance V` | 是 | — | 角点检测器逆方差（通常取 1） |
| `--folder PATH` 或 `--bag PATH` | 是 | — | 数据源 |
| `--target YAML` | 是 | — | 标定目标文件 |
| `--bag-freq HZ` | 否 | 无限制 | 最大采样频率 |
| `--bag-from-to T0 T1` | 否 | 全部 | 时间截断 [s] |
| `--max-iter N` | 否 | 30 | 最大迭代次数 |
| `--verbose` | 否 | — | 详细输出 |
| `--show-extraction` | 否 | — | 实时显示提取 |
| `--dont-show-report` | 否 | — | 不弹出报告 |

---

## 可视化工具

```bash
# 可视化相机标定结果
kalibr_visualize_calibration \
  --chain /data/dataset/dataset-camchain.yaml

# 可视化畸变模型（指定相机索引）
kalibr_visualize_distortion \
  --chain /data/dataset/dataset-camchain.yaml \
  --cam 0

# 生成标定靶 PDF（A3 打印用）
kalibr_create_target_pdf \
  --type aprilgrid \
  --nx 6 --ny 6 \
  --tsize 0.055 \
  --tspace 0.3 \
  --output aprilgrid_6x6_55mm.pdf
```

---

## IMU参数YAML格式

描述 IMU 传感器的噪声特性，传入 `--imu` 参数。

```yaml
# imu0.yaml
rostopic: /imu/data         # folder 模式下可任意填写，bag 模式需匹配实际 topic

update_rate: 200.0          # IMU 采样率 [Hz]

# Allan 方差分析得到的噪声参数
accelerometer_noise_density: 1.862e-3   # 加速度计白噪声  [m/s^2/sqrt(Hz)]
accelerometer_random_walk:   4.500e-5   # 加速度计随机游走 [m/s^3/sqrt(Hz)]
gyroscope_noise_density:     1.649e-4   # 陀螺仪白噪声    [rad/s/sqrt(Hz)]
gyroscope_random_walk:       6.318e-7   # 陀螺仪随机游走  [rad/s^2/sqrt(Hz)]
```

噪声参数来源：
1. IMU 数据手册（通常可直接使用）
2. Allan 方差分析工具，如 `imu_utils`（更准确）

**输入格式说明**：`--imu` 参数要求**扁平结构**（所有字段在顶层）。若使用 `kalibr_calibrate_imu_camera` 输出的 `*-imu.yaml` 作为输入，需将 `imu0:` 下的内容提取到顶层（输出格式含 `imu0:` 嵌套，不能直接复用）。

---

## camchain YAML格式

相机链参数文件，作为 `kalibr_calibrate_imu_camera` 的 `--cams` 输入：

```yaml
cam0:
  camera_model: pinhole
  distortion_model: radtan
  intrinsics: [336.63, 336.73, 273.90, 312.41]  # [fx, fy, cx, cy] [px]
  distortion_coeffs: [-0.2435, 0.0395, 0.0001, -0.0004]  # [k1, k2, p1, p2]
  resolution: [640, 480]                          # [width, height] [px]
  rostopic: cam0                                  # folder 模式：必须为子目录名（cam0/cam1）

cam1:
  camera_model: pinhole
  distortion_model: radtan
  intrinsics: [333.06, 333.09, 275.47, 304.09]
  distortion_coeffs: [-0.2503, 0.0422, 0.0025, -0.0015]
  resolution: [640, 480]
  rostopic: cam1                                  # folder 模式：必须为子目录名
  T_cn_cnm1:                    # cam1 到 cam0 的变换（4x4 齐次矩阵）
  - [ 0.99998, -0.00357,  0.00561, -0.10002]
  - [ 0.00357,  0.99999,  0.00015,  0.00007]
  - [-0.00561, -0.00013,  0.99998, -0.00018]
  - [ 0.0,      0.0,      0.0,     1.0    ]
```

联合标定后，camchain 中会增加 `T_cam_imu` 字段：

```yaml
cam0:
  ...
  T_cam_imu:                    # cam0 到 IMU0 的变换（4x4 齐次矩阵）
  - [ 0.99993, -0.00783,  0.00853,  0.03201]
  - [ 0.00781,  0.99996,  0.00444, -0.01023]
  - [-0.00856, -0.00438,  0.99995, -0.00142]
  - [ 0.0,      0.0,      0.0,     1.0    ]
  timeshift_cam_imu: -0.0023    # 相机相对 IMU 的时间偏移 [s]
```

**folder 模式下的 rostopic**：`kalibr_calibrate_imu_camera` 会通过 rostopic 解析图像子目录（取路径第一段）。若 `kalibr_calibrate_cameras` 输出的 camchain 中 rostopic 为完整路径（如 `/path/dataset/cam0`），会导致 `images.csv not found`。需手动改为子目录名：`cam0`、`cam1`。

---

## 输出文件说明

### camchain.yaml

相机链完整参数，可直接用于 SLAM、视觉里程计等框架（如 ORB-SLAM3、Basalt 等）。

### results-cam.txt / results-imucam.txt

文字报告示例：

```
Camera chain
==================
  cam0 (/data/dataset/cam0):
    type: DistortedPinholeCameraGeometry
    distortion: [-0.2455  0.0395  0.0025 -0.0019] +- [0.0027 0.0009 0.0002 0.0002]
    projection: [332.77 333.02 279.29 301.17]      +- [1.81   1.81   0.39   0.41]
    reprojection error: [-0.000126, 0.000017] +- [1.049286, 1.180141]
  cam1:
    ...
  baseline T_1_0:
    q: [-0.00357 -0.00561 0.00245 0.99997] +- [0.00099 0.00095 0.00015]
    t: [-0.10002 -0.00007 -0.00018]        +- [0.00013 0.00012 0.00028]
```

### report.pdf

PDF 报告包含：
- 角点提取覆盖情况（热力图）
- 各相机重投影误差分布（直方图、散点图）
- 标定靶姿态分布（保证标定多角度覆盖）
- 相机-IMU 时延分析曲线（imu_camera 模式）

---

## 常见问题

**Q：`No corners could be extracted`**
- 检查 YAML 参数与实物是否一致（tagSize、tagRows、tagCols）
- 确保图像清晰、标定靶占图像面积 > 20%
- 用 `--show-extraction` 实时查看提取效果
- 检查 `images.csv` 时间戳和文件名是否正确

**Q：`Optimization diverged`**
- 数据量不足，需从更多角度采集图像
- 尝试增大 `--mi-tol 0.5` 允许使用更多图像
- 标定靶运动时不应有运动模糊

**Q：重投影误差偏大（> 1.5 px）**
- 图像模糊或曝光过度
- 纸质标定靶有形变（折叠、弯曲），建议使用硬质材料打印
- 镜头模型与实际不匹配（鱼眼请选 `pinhole-equi` 或 `eucm-none`）

**Q：无显示器时报 `cannot connect to X server`**
- 添加 `--dont-show-report` 参数
- 同时设置 `export MPLBACKEND=Agg`

**Q：`ImportError: libgtk-3.so.0: cannot open shared object file`**
- **原因**：sysroot 中的 OpenCV 在构建时启用了 GTK，`libopencv_highgui.so` 依赖 `libgtk-3`。X5 等无 GUI 设备通常未安装 GTK。
- **已内置方案**：kalibr 源码已修改为 headless 模式，注释了所有显示相关代码（`--show-extraction`、`--plot-corner-reprojection` 等），CMake 仅链接 `core/imgproc/imgcodecs/calib3d/features2d`，不链接 `opencv_highgui`。重新编译部署即可，无需 GTK。
- **若需恢复显示**：需重新构建 sysroot 的 OpenCV 并禁用 GTK（`-DWITH_GTK=OFF`），或安装 `apt install libgtk-3-0`。

**Q：`ImportError: libopencv_highgui.so.409: cannot open shared object file`**
- **原因**：kalibr 有多个 .so 会加载 OpenCV（`libaslam_cv_python.so`、`libaslam_cameras_april_python.so` 等），任一链接了 OpenCV 4.9 都会报此错。运行环境只有 4.2 时需全部用 4.2 重编。
- **排查步骤**（在 `build_standalone` 目录下执行）：
  1. 查看当前系统 OpenCV：`find /usr /usr/local -name "libopencv_highgui.so*" 2>/dev/null`
  2. 查看编译时使用的 OpenCV：`grep OpenCV_DIR CMakeCache.txt`
  3. **检查所有会加载 OpenCV 的 .so**（`libaslam_cv_python.so` 和 `libaslam_cameras_april_python.so` 都要查）：
     ```bash
     for f in aslam_cv/aslam_cv_python/python/aslam_cv/libaslam_cv_python.so \
              aslam_cv/aslam_cameras_april/python/aslam_cameras_april/libaslam_cameras_april_python.so; do
       [ -f "$f" ] && echo "=== $f ===" && ldd "$f" | grep opencv
     done
     ```
     若任一出现 `.so.409` 则需重编。
- **解决**：完整清理后用系统 OpenCV 重新编译：
  ```bash
  cd build_standalone && rm -rf *
  cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DOpenCV_DIR=/usr/lib/x86_64-linux-gnu/cmake/opencv4
  make -j$(nproc)
  ```
  若系统 OpenCV 的 cmake 路径不同，可用：`find /usr -name "OpenCVConfig.cmake" 2>/dev/null` 查找。

**Q：`images.csv not found in .../dataset/catkin_ws`（或类似错误路径）**
- camchain 中 rostopic 被错误写成完整路径。folder 模式下 rostopic 必须为子目录名（`cam0`、`cam1`），用于拼接 `dataset/cam0`、`dataset/cam1`。手动修改 camchain.yaml 中 `rostopic: cam0`、`rostopic: cam1`。

**Q：`Field 'update_rate' missing in file` 或 IMU 配置解析失败**
- `--imu` 输入要求扁平 YAML（字段在顶层）。若复用 `kalibr_calibrate_imu_camera` 输出的 `*-imu.yaml`，需将 `imu0:` 下的内容提取到顶层。

**Q：imu_camera 标定后时延异常偏大（> 100ms）**
- IMU 和相机数据时间未对齐，检查时间戳来源
- 尝试加 `--imu-delay-by-correlation` 自动搜索初始偏移
- 扩大搜索范围：`--timeoffset-padding 0.1`

**Q：多次运行结果不一致**
- 属正常现象（优化涉及随机初始化）
- 若结果相差 > 5 像素，说明数据质量不足，请增加图像数量和角度多样性

---

## 完整示例

### 双目相机标定

```bash
# 数据集结构
ls /data/stereo/
# cam0/  cam1/
# cam0/images.csv  cam0/image_000000.png ...
# cam1/images.csv  cam1/image_000000.png ...

# 激活环境
source /path/to/kalibr/setup_kalibr.sh

# 以 4Hz 采样（约 25 帧），pinhole+等距畸变
kalibr_calibrate_cameras \
  --folder /data/stereo \
  --topics cam0 cam1 \
  --models pinhole-equi pinhole-equi \
  --target /data/aprilgrid_6x6_55mm.yaml \
  --bag-freq 4 \
  --dont-show-report

# 查看结果
cat /data/stereo/*-results-cam.txt
```

### 相机+IMU 联合标定

```bash
# 数据集结构（需要 IMU 高频数据同步录制）
ls /data/imu_calib/
# cam0/  imu.csv
# cam0/images.csv  cam0/image_000000.png ...
# imu.csv           <- 位于 dataset 根目录

# 第一步：相机内参标定
kalibr_calibrate_cameras \
  --folder /data/imu_calib \
  --topics cam0 \
  --models pinhole-equi \
  --target /data/aprilgrid.yaml \
  --bag-freq 4 \
  --dont-show-report

# 第二步：联合标定（使用第一步输出的 camchain）
kalibr_calibrate_imu_camera \
  --folder /data/imu_calib \
  --cams /data/imu_calib/*-camchain.yaml \
  --imu /data/imu0_noise.yaml \
  --target /data/aprilgrid.yaml \
  --bag-freq 4 \
  --dont-show-report

# 查看结果
cat /data/imu_calib/*-results-imucam.txt
```

### 采集数据建议

- **图像数量**：每个相机至少 50~100 张（含不同距离、角度）
- **运动要求**：标定靶要覆盖图像各区域（尤其是四角和中心）
- **避免**：运动模糊、过曝、欠曝
- **IMU 数据**：录制时保持激励运动（3 轴旋转 + 平移），避免静止
- **采集时长**：IMU+相机联合标定建议 60~120 秒的激励运动序列
