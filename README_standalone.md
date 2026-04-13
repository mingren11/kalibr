# Kalibr X5 使用说明

本文档只保留当前工程在 X5 上的实际使用方式：

- 交叉编译生成 `install/`
- 拷贝 `install/` 到板端
- 三目标定
- 双目 + IMU 联合标定

## 1. 编译

在交叉编译 Docker 中执行：

```bash
# 1. 进入 tros_ws
cd /path/to/LooperHub/tros_ws

# 2. 配置 X5 交叉编译环境
export TARGET_ARCH=aarch64
export TARGET_TRIPLE=aarch64-linux-gnu
export CROSS_COMPILE=/usr/bin/$TARGET_TRIPLE-

# 3. 切换 sysroot 到 X5
rm -f ../sysroot_docker/usr
ln -s "$(pwd)/../sysroot_docker/usr_x5" "$(pwd)/../sysroot_docker/usr"

# 4. 配置并编译 kalibr
cd src/kalibr
mkdir -p build_standalone_x5
cd build_standalone_x5

cmake .. \
  -DCMAKE_TOOLCHAIN_FILE="../../../robot_dev_config/aarch64_toolchainfile.cmake" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF

make -j"$(nproc)"
make install
```

编译完成后，产物在：

```bash
src/kalibr/build_standalone_x5/install
```

## 2. 部署到 X5

```bash
scp -r install root@192.168.137.100:/userdata/calibr
```

X5 上加载环境：

```bash
source /userdata/calibr/install/setup_kalibr.sh
```

可用性检查：

```bash
kalibr_calibrate_cameras --help
kalibr_calibrate_imu_camera --help
```

## 3. 数据目录

### 3.1 三目相机数据

```text
/userdata/calibr-data/cam/
  cam0/
    <timestamp_ns>.png
  cam1/
    <timestamp_ns>.png
  cam2/
    <timestamp_ns>.png
```

规则：

- 文件名必须是纳秒时间戳整数
- `cam0/cam1/cam2` 按文件名时间戳对齐
- 只使用三路共有时间戳
- 缺失帧会打印丢弃日志

### 3.2 双目 + IMU 数据

```text
/userdata/calibr-data/imu_cam/
  cam0/
    <timestamp_ns>.png
  cam1/
    <timestamp_ns>.png
  imu.csv
```

`imu.csv` 格式：

```csv
timestamp,omega_x,omega_y,omega_z,alpha_x,alpha_y,alpha_z
```

规则：

- 图像文件名必须是纳秒时间戳整数
- `imu.csv` 第一列必须是纳秒时间戳整数
- 图像按时间戳排序
- IMU 全量读入
- 程序会打印图像数、IMU 样本数、时间范围和 camera/imu overlap

## 4. 三目标定

命令：

```bash
kalibr_calibrate_cameras \
  --folder /userdata/calibr-data/cam \
  --topics cam0 cam1 cam2 \
  --models pinhole-equi pinhole-equi pinhole-equi \
  --target /userdata/calibr/target_aprilgrid6x6_055.yaml
```

输出：

- `/userdata/calibr-data/cam-camchain.yaml`
- 标定报告和结果文本

## 5. 双目 + IMU 联合标定

### 5.1 复用三目标定结果

可以复用三目标定生成的 `cam-camchain.yaml`，但要先裁剪成只包含 `cam0/cam1`，并把 `rostopic` 改成子目录名。

示例：

```bash
sed -n '/^cam2:/q;p' /userdata/calibr-data/cam-camchain.yaml \
  | sed -E 's|(rostopic:\s+).*/([^/]+)$|\1\2|' \
  > /userdata/calibr-data/cam-camchain-to-imu-cam.yaml
```

生成后的文件应满足：

- 只保留 `cam0` 和 `cam1`
- `rostopic: cam0`
- `rostopic: cam1`

### 5.2 再做双目 + IMU 联标

```bash
kalibr_calibrate_imu_camera \
  --folder /userdata/calibr-data/imu_cam \
  --cams /userdata/calibr-data/cam-camchain-to-imu-cam.yaml \
  --imu /userdata/calibr/imu.yaml \
  --target /userdata/calibr/target_aprilgrid6x6_055.yaml \
  --bag-freq 5
```

输出：

- `/userdata/calibr-data/imu_cam-camchain-imucam.yaml`
- `/userdata/calibr-data/imu_cam-imu.yaml`
- 标定报告和结果文本

## 6. 重要说明

- `kalibr_calibrate_imu_camera` 的 `--cams` 必须对应当前 `--folder` 数据集
- 对 `/userdata/calibr-data/imu_cam` 联标时，`camchain` 里只能有 `cam0` 和 `cam1`
- `camchain.yaml` 里的 `rostopic` 必须是子目录名，例如：

```yaml
cam0:
  rostopic: cam0
cam1:
  rostopic: cam1
```

- 如果 `rostopic` 被写成完整路径，例如 `/userdata/calibr-data/cam/cam0`，联标时会找不到图像目录

## 7. 常见问题

### 7.1 报错 `Neither 'timestamps.txt + data/' nor 'images.csv' found`

说明板端还在使用旧版本 `install/`。  
重新编译并把新的 `build_standalone_x5/install` 整体拷到设备覆盖。

### 7.2 报错 `no camera data found in '/userdata/calibr-data/imu_cam'`

通常是 `--cams` 用错了：

- 直接用了未裁剪的三目 `cam-camchain.yaml`
- 或 `rostopic` 不是 `cam0` / `cam1`

正确做法是先把三目 `cam-camchain.yaml` 裁剪成 `cam0/cam1` 两路，并把 `rostopic` 改成 `cam0`、`cam1`，再执行 `kalibr_calibrate_imu_camera`
