#!/bin/bash
set -Eeuo pipefail

source /userdata/install/kalibr/setup_kalibr.sh

step1_calibrate_cameras() {
  kalibr_calibrate_cameras \
    --folder /userdata/calibr-data/cam \
    --topics cam0 cam1 cam2 \
    --models pinhole-equi pinhole-equi pinhole-equi \
    --target /userdata/install/kalibr/target.yaml
}

step2_generate_camchain() {
  sed -n '/^cam1:/q;p' /userdata/calibr-data/cam-camchain.yaml \
    | sed -E 's|(rostopic:\s+).*/([^/]+)$|\1\2|' \
    > /userdata/calibr-data/for-imu-camera.yaml

  test -s /userdata/calibr-data/for-imu-camera.yaml
}

step3_calibrate_imu_camera() {
  kalibr_calibrate_imu_camera \
    --folder /userdata/calibr-data/imu_cam \
    --cams /userdata/calibr-data/for-imu-camera.yaml \
    --imu /userdata/install/kalibr/imu.yaml \
    --target /userdata/install/kalibr/target.yaml \
    --bag-freq 5
}

step4_format_output() {
  looper_format.py \
    --imucam /userdata/calibr-data/imu_cam-camchain-imucam.yaml \
    --camchain /userdata/calibr-data/for-imu-camera.yaml \
    --output-dir /app/calibration
}

step5_cleanup() {
  mkdir -p /app/calibration/calibr_info
  cp /userdata/calibr-data/cam-camchain.yaml /app/calibration/calibr_info/cam-camchain.yaml
  cp /userdata/calibr-data/imu_cam-camchain-imucam.yaml /app/calibration/calibr_info/imu_cam-camchain-imucam.yaml
  cp /userdata/calibr-data/cam-results-cam.txt /app/calibration/calibr_info/cam-results-cam.txt
  cp /userdata/calibr-data/imu_cam-results-imucam.txt /app/calibration/calibr_info/imu_cam-results-imucam.txt
  rm -rf /userdata/calibr-data/*
}

step1_calibrate_cameras
step2_generate_camchain
step3_calibrate_imu_camera
step4_format_output
step5_cleanup