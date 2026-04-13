
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

source /userdata/calibr/install/setup_kalibr.sh


kalibr_calibrate_cameras \
  --folder /userdata/calibr-data/cam \
  --topics cam0 cam1 cam2 \
  --models pinhole-equi pinhole-equi pinhole-equi \
  --target /userdata/calibr/target_aprilgrid6x6_055.yaml

sed -n '/^cam2:/q;p' cam-camchain.yaml \
  | sed -E 's|(rostopic:\s+).*/([^/]+)$|\1\2|' \
  > cam-camchain-to-imu-cam.yaml

kalibr_calibrate_imu_camera \
  --folder /userdata/calibr-data/imu_cam \
  --cams /userdata/calibr-data/cam-camchain-to-imu-cam.yaml \
  --imu /userdata/calibr/imu.yaml \
  --target /userdata/calibr/target_aprilgrid6x6_055.yaml \
  --bag-freq 5

