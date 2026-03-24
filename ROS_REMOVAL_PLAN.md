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




# 相机+IMU 标定
kalibr_calibrate_imu_camera --folder /userdata/online_calibr/20250827_054720 \
  --cams /app/calibration/rgb_calibr.calibration.json \
  --imu /userdata/kalibr_test/imu.yaml \
  --target /userdata/kalibr_test/params/target_aprilgrid6x6_055.yaml \
  --pose-knots-per-second 40 \
  --bias-knots-per-second 10 \
  --bag-freq 5 --dont-show-report