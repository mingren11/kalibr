# Kalibr 去除 ROS 依赖 - 修改计划

## 目标
使 kalibr 项目完全脱离 ROS1 运行时依赖，支持纯 Python/CMake 构建和运行。

## 已完成阶段

### Phase 1: 替换 rospkg ✅
**文件**: `kalibr_msf_config`, `kalibr_okvis_config`, `kalibr_rovio_config`
**改动**: `rospack.get_path('kalibr')` → `Path(__file__).resolve().parent / 'auxiliary_files'` 的父级路径
**验证**: 运行各 exporter 脚本，确认能正确读取 auxiliary_files

### Phase 2: 创建 FolderImageDatasetReader ✅
**新建**: `kalibr_common/FolderImageDatasetReader.py`
**格式**: 文件夹 + `images.csv`（列: timestamp_ns, filename）
**接口**: 与 BagImageDatasetReader 兼容的 `getImage(idx)` → `(timestamp, img_data)`

### Phase 3: 创建 FolderImuDatasetReader ✅
**新建**: `kalibr_common/FolderImuDatasetReader.py`
**格式**: `imu.csv`（列: timestamp_ns, gx, gy, gz, ax, ay, az）
**接口**: 与 BagImuDatasetReader 兼容的 `getMessage(idx)` → `(timestamp, omega, alpha)`

### Phase 4: 数据集抽象与集成 ✅
**改动**: 
- 添加 `create_image_dataset(bag_or_folder, topic_or_csv, ...)` 工厂函数
- 添加 `create_imu_dataset(bag_or_folder, topic_or_csv, ...)` 工厂函数
- 修改 `IccSensors.py` 的 `initCameraBagDataset`/`initImuBagDataset` 支持两种输入
- 修改 `kalibr_calibrate_cameras` 支持 folder 输入
- 修改 `kalibr_calibrate_imu_camera` 入口参数解析

### Phase 5: 移除 rosbag/cv_bridge 依赖 ✅
**改动**:
- 从 `kalibr_common/__init__.py` 移除 rosbag/cv_bridge 的导出（当使用 folder 时）
- 确保主标定流程可完全使用 folder 格式运行
- 移除或标记 `kalibr_bagcreater`、`kalibr_bagextractor` 为 ROS 专用（可选保留作转换工具）

### Phase 8: 完全移除所有 ROS1 代码 ✅
**改动**:
- 删除 `ImageDatasetReader.py`、`ImuDatasetReader.py`（旧 rosbag 读取器）
- 删除 `kalibr_bagcreater`、`kalibr_bagextractor`、`kalibr_camera_focus`、`kalibr_camera_validator`（纯 ROS 工具）
- `kalibr_common/__init__.py`：移除 lazy bag reader 加载
- `DatasetFactory.py`：仅支持 folder 模式，删除 bag 分支
- `kalibr_calibrate_cameras/imu_camera/rs_cameras`：移除 `--bag` 参数，`--folder` 为唯一数据源
- `aslam_cameras/aslam_cameras_april` CMakeLists.txt：移除 `ADD_DEFINITIONS(-DASLAM_USE_ROS)`

### Phase 6: 构建系统迁移（catkin → CMake）🔄 进行中
**范围**: 39 个包
**策略**: 分 tier 迁移验证，tier 1 已通过
**关键**: opencv2_catkin → find_package(OpenCV)，Findcatkin 兼容层
**说明**: 新增 `kalibr/CMakeLists.txt` 和 `kalibr/cmake/` 支持独立 CMake 构建

**构建方式**:
```bash
cd /catkin_ws/src/kalibr
mkdir build_standalone && cd build_standalone
cmake .. -DCMAKE_BUILD_TYPE=Release  # 全量构建
make -j4
make install
scp -r install root@192.168.137.100:/userdata/kalibr_install    (记得先删除/userdata/kalibr_install目录)
```

### Phase 7: 实时工具处理 ✅
**文件**: `kalibr_camera_focus`, `kalibr_camera_validator`
**方案**: 已添加 ROS 检测，无 ROS 时打印友好提示并退出

---

## 使用方式（无 ROS 运行时）

```bash
# 相机标定（多相机）


source /userdata/kalibr_install/setup.sh

kalibr_calibrate_cameras --folder /userdata/kalibr_test/dataset --topics cam0 cam1 \
  --models pinhole-equi pinhole-equi \
  --target /userdata/kalibr_test/params/target_aprilgrid6x6_055.yaml \
  --bag-freq 5 \
  --dont-show-report

# 相机+IMU 标定
kalibr_calibrate_imu_camera --folder /userdata/kalibr_test/dataset \
  --cams /userdata/kalibr_test/dataset-camchain.yaml \
  --imu /userdata/kalibr_test/imu.yaml \
  --target /userdata/kalibr_test/params/target_aprilgrid6x6_055.yaml \
  --pose-knots-per-second 40 \
  --bias-knots-per-second 10 \
  --bag-freq 5 --dont-show-report

# 滚动快门标定
kalibr_calibrate_rs_cameras --folder /userdata/kalibr_test/dataset \
  --topic cam0 \
  --model pinhole-radtan-rs \
  --target /userdata/kalibr_test/params/target_aprilgrid6x6_055.yaml \
  --frame-rate 20 \
  --inverse-feature-variance 1 \
  --dont-show-report
```

---

## 数据格式规范（Phase 2/3）

### 图像数据集
```
dataset/
  cam0/
    images.csv          # timestamp_ns,filename
    image_000000.png
    image_000001.png
  cam1/
    images.csv
    ...
```

### IMU 数据集
```
dataset/
  imu.csv               # timestamp_ns,gx,gy,gz,ax,ay,az (单位: rad/s, m/s^2)
```
