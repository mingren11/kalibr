#!/bin/bash
# Source this script to set up the environment for running kalibr without ROS:
#   source /catkin_ws/src/kalibr/setup_kalibr.sh

KALIBR_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KALIBR_BUILD="${KALIBR_BUILD:-${KALIBR_SRC}/build_standalone}"

# ── Source tree Python package directories ──────────────────────────────────
# Each of these has __init__.py + lib*.so symlink (pointing to build dir ELF)
KALIBR_PY=""
for d in \
    "${KALIBR_SRC}/Schweizer-Messer/numpy_eigen/python" \
    "${KALIBR_SRC}/Schweizer-Messer/sm_python/python" \
    "${KALIBR_SRC}/aslam_optimizer/aslam_backend_python/python" \
    "${KALIBR_SRC}/aslam_incremental_calibration/incremental_calibration_python/src" \
    "${KALIBR_SRC}/aslam_nonparametric_estimation/bsplines_python/python" \
    "${KALIBR_SRC}/aslam_nonparametric_estimation/aslam_splines_python/python" \
    "${KALIBR_SRC}/aslam_cv/aslam_cv_python/python" \
    "${KALIBR_SRC}/aslam_cv/aslam_cv_backend_python/python" \
    "${KALIBR_SRC}/aslam_cv/aslam_cameras_april/python" \
    "${KALIBR_SRC}/aslam_offline_calibration/kalibr/python" \
; do
    KALIBR_PY="${d}:${KALIBR_PY}"
done

# ── Build dir for libkalibr_errorterms_python.so (non-relative import) ──────
KALIBR_PY="${KALIBR_BUILD}/aslam_offline_calibration/kalibr/python:${KALIBR_PY}"

export PYTHONPATH="${KALIBR_PY}${PYTHONPATH}"
export PATH="${KALIBR_SRC}/aslam_offline_calibration/kalibr/python:${PATH}"

echo "kalibr environment ready."
echo "Run: kalibr_calibrate_cameras --help"
