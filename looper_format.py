#!/usr/bin/env python3
"""
Read imucam.yaml and camchain.yaml, and generate looper.calibration.json.
If camchain.yaml also contains cam2, generate rgb.calibration.json as well.
Dependencies: numpy, pyyaml (no scipy required)

python3 looper_format.py \
  --imucam /home/mingren/work/3DVision/Deploy/LooperHub/tros_ws/src/kalibr/config/imu_cam-camchain-imucam.yaml \
  --camchain /home/mingren/work/3DVision/Deploy/LooperHub/tros_ws/src/kalibr/config/cam-camchain-to-imu-cam.yaml \
  --output-dir /home/mingren/work/3DVision/Deploy/LooperHub/tros_ws/src/kalibr/config
"""

import argparse
import json
import os
import yaml
import numpy as np

# ========== Utility Functions ==========

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def mat_to_quat_translation(T):
    """
    Extract quaternion (w, x, y, z) and translation (x, y, z) from a 4x4 transformation matrix.
    Uses the Shepperd method, implemented with pure numpy, scipy not required.
    """
    R = np.array(T, dtype=np.float64)[:3, :3]
    t = np.array(T, dtype=np.float64)[:3, 3]

    trace = R[0, 0] + R[1, 1] + R[2, 2]
    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (R[2, 1] - R[1, 2]) * s
        y = (R[0, 2] - R[2, 0]) * s
        z = (R[1, 0] - R[0, 1]) * s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s

    quat        = {"w": float(w), "x": float(x), "y": float(y), "z": float(z)}
    translation = {"x": float(t[0]), "y": float(t[1]), "z": float(t[2])}
    return quat, translation

def make_camera_entry(camera_name, quat, translation, intrinsics, distortion_coef, resolution):
    """Construct a single camera calibration entry."""
    return {
        "camera_name": camera_name,
        "extrinsics": {
            "pose_base_in_sensor": {
                "rotation":    quat,
                "translation": translation
            }
        },
        "intrinsics": {
            "camera_model":    "FISHEYE",
            "cx":              intrinsics[2],
            "cy":              intrinsics[3],
            "distortion_coef": list(distortion_coef),
            "fx":              intrinsics[0],
            "fy":              intrinsics[1],
            "height":          resolution[1],
            "width":           resolution[0]
        }
    }

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {path}")

# ========== Main Logic ==========

def main():
    parser = argparse.ArgumentParser(
        description="Read imucam.yaml and camchain.yaml, and generate looper.calibration.json plus optional rgb.calibration.json"
    )
    parser.add_argument(
        "path", nargs="?",
        default="/userdata/calibr-data",
        help="Calibration data directory (contains ros1-camchain-imucam.yaml and ros1-camchain.yaml)"
    )
    parser.add_argument("--imucam", required=True, help="Path to imucam YAML file")
    parser.add_argument("--camchain", required=True, help="Path to camchain YAML file")
    parser.add_argument("--output-dir",        help="Common output directory, used if no specific directory is given")
    parser.add_argument("--rgb-output-dir",    help="Output directory for rgb.calibration.json")
    parser.add_argument("--looper-output-dir", help="Output directory for looper.calibration.json")
    args = parser.parse_args()

    default_output_dir = os.path.join(args.path, "calibration")
    rgb_output_dir    = args.rgb_output_dir    or args.output_dir or default_output_dir
    looper_output_dir = args.looper_output_dir or args.output_dir or default_output_dir

    # ===== Load YAML =====
    # imucam.yaml: intrinsics and extrinsics for left, right, and RGB cameras (including IMU-camera extrinsics)
    # camchain.yaml: extrinsics between cameras (chained for cam0/cam1/cam2)
    imucam   = load_yaml(args.imucam)
    camchain = load_yaml(args.camchain)

    rgb_output_dir    = os.path.abspath(rgb_output_dir)
    looper_output_dir = os.path.abspath(looper_output_dir)

    # ===== Extract from imucam.yaml =====
    # T_cam0_imu: Pose of the IMU in cam0 (left camera) coordinate frame
    T_cam0_imu          = np.array(imucam["cam0"]["T_cam_imu"],         dtype=np.float64)
    cam0_intrinsics_imu = imucam["cam0"]["intrinsics"]
    cam0_distortion_imu = imucam["cam0"]["distortion_coeffs"]
    cam0_resolution_imu = imucam["cam0"]["resolution"]

    # ===== Extract from camchain.yaml =====
    cam0_intrinsics = camchain["cam0"]["intrinsics"]
    cam0_distortion = camchain["cam0"]["distortion_coeffs"]
    cam0_resolution = camchain["cam0"]["resolution"]

    # T_cam1_cam0: Right camera relative to left camera transformation
    T_cam1_cam0     = np.array(camchain["cam1"]["T_cn_cnm1"], dtype=np.float64)
    cam1_intrinsics = camchain["cam1"]["intrinsics"]
    cam1_distortion = camchain["cam1"]["distortion_coeffs"]
    cam1_resolution = camchain["cam1"]["resolution"]

    has_cam2 = "cam2" in camchain
    if has_cam2:
        # T_cam2_cam1: RGB camera relative to right camera transformation
        T_cam2_cam1     = np.array(camchain["cam2"]["T_cn_cnm1"], dtype=np.float64)
        cam2_intrinsics = camchain["cam2"]["intrinsics"]
        cam2_distortion = camchain["cam2"]["distortion_coeffs"]
        cam2_resolution = camchain["cam2"]["resolution"]

    # ===== Compute composite transformations =====
    T_cam1_imu  = T_cam1_cam0 @ T_cam0_imu    # Right camera relative to IMU
    if has_cam2:
        T_cam2_cam0 = T_cam2_cam1 @ T_cam1_cam0   # RGB relative to left camera

    # ================================================================
    # rgb.calibration.json
    # base_name = "CAMERA_LEFT" (cam0)
    # pose_base_in_sensor = Pose of left camera (cam0) in each camera's coordinate frame, i.e., T_camX_cam0
    # ================================================================
    identity_quat  = {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}
    identity_trans = {"x": 0.0, "y": 0.0, "z": 0.0}

    quat_right, trans_right = mat_to_quat_translation(T_cam1_cam0)
    if has_cam2:
        quat_rgb, trans_rgb = mat_to_quat_translation(T_cam2_cam0)
        rgb_calibration = {
            "base_name": "CAMERA_LEFT",
            "camera_calibrations": [
                make_camera_entry("CAMERA_LEFT",  identity_quat, identity_trans,
                                  cam0_intrinsics, cam0_distortion, cam0_resolution),
                make_camera_entry("CAMERA_RIGHT", quat_right, trans_right,
                                  cam1_intrinsics, cam1_distortion, cam1_resolution),
                make_camera_entry("RGB_CAMERA",   quat_rgb,   trans_rgb,
                                  cam2_intrinsics, cam2_distortion, cam2_resolution),
            ]
        }
        write_json(os.path.join(rgb_output_dir, "rgb.calibration.json"), rgb_calibration)
    else:
        print("cam2 not found in camchain.yaml, skipping rgb.calibration.json generation")

    # ================================================================
    # looper.calibration.json
    # base_name = "IMU"
    # pose_base_in_sensor = Pose of the IMU in each camera's coordinate frame, i.e., T_camX_imu
    # ================================================================
    quat_left_imu,  trans_left_imu  = mat_to_quat_translation(T_cam0_imu)
    quat_right_imu, trans_right_imu = mat_to_quat_translation(T_cam1_imu)

    looper_calibration = {
        "base_name": "IMU",
        "camera_calibrations": [
            make_camera_entry("CAMERA_LEFT",  quat_left_imu,  trans_left_imu,
                              cam0_intrinsics_imu, cam0_distortion_imu, cam0_resolution_imu),
            make_camera_entry("CAMERA_RIGHT", quat_right_imu, trans_right_imu,
                              cam1_intrinsics, cam1_distortion, cam1_resolution),
        ]
    }

    write_json(os.path.join(looper_output_dir, "looper.calibration.json"), looper_calibration)

if __name__ == "__main__":
    main()