#!/bin/bash
# Deploy kalibr build output to a target directory (no source needed on device).
# Usage: ./deploy_standalone.sh <target_dir> [build_dir]
#
# Example:
#   ./deploy_standalone.sh /userdata/kalibr_install
#   ./deploy_standalone.sh /userdata/kalibr_install build_standalone_x5

set -e

KALIBR_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:?Usage: $0 <target_dir> [build_dir]}"
BUILD_DIR="${2:-${KALIBR_SRC}/build_standalone_x5}"

if [[ ! -d "$BUILD_DIR" ]]; then
  echo "Error: build dir not found: $BUILD_DIR"
  echo "Run from kalibr src, or pass build dir: $0 <target> build_standalone_x5"
  exit 1
fi

echo "Deploying kalibr to $TARGET_DIR"
echo "  Source: $KALIBR_SRC"
echo "  Build:  $BUILD_DIR"

mkdir -p "$TARGET_DIR"/{lib,bin}

# Python packages: copy .py from source, .so from build (or source for numpy_eigen)
# Each entry: "src_rel_path:lib_subdir" (lib_subdir is the name under TARGET_DIR/lib)
packages=(
  "Schweizer-Messer/numpy_eigen/python/numpy_eigen:numpy_eigen"
  "Schweizer-Messer/sm_python/python/sm:sm"
  "aslam_optimizer/aslam_backend_python/python/aslam_backend:aslam_backend"
  "aslam_incremental_calibration/incremental_calibration_python/src/incremental_calibration:incremental_calibration"
  "aslam_nonparametric_estimation/bsplines_python/python/bsplines:bsplines"
  "aslam_nonparametric_estimation/aslam_splines_python/python/aslam_splines:aslam_splines"
  "aslam_cv/aslam_cv_python/python/aslam_cv:aslam_cv"
  "aslam_cv/aslam_cv_backend_python/python/aslam_cv_backend:aslam_cv_backend"
  "aslam_cv/aslam_cameras_april/python/aslam_cameras_april:aslam_cameras_april"
)

for spec in "${packages[@]}"; do
  src_rel="${spec%%:*}"
  lib_name="${spec##*:}"
  src_path="$KALIBR_SRC/$src_rel"
  build_path="$BUILD_DIR/$src_rel"
  dest="$TARGET_DIR/lib/$lib_name"
  mkdir -p "$dest"
  # Copy .py from source
  if [[ -d "$src_path" ]]; then
    find "$src_path" -maxdepth 1 -name "*.py" -exec cp {} "$dest/" \; 2>/dev/null || true
    # Copy subdirs (e.g. sm/experiments)
    for sub in "$src_path"/*/; do
      [[ -d "$sub" ]] || continue
      subname=$(basename "$sub")
      mkdir -p "$dest/$subname"
      find "$sub" -maxdepth 1 -name "*.py" -exec cp {} "$dest/$subname/" \; 2>/dev/null || true
      [[ -f "$sub/__init__.py" ]] && cp "$sub/__init__.py" "$dest/$subname/" 2>/dev/null || true
    done
  fi
  # Copy .so from build or source (numpy_eigen outputs to source)
  for so in "$build_path"/*.so "$src_path"/*.so; do
    [[ -f "$so" ]] && cp "$so" "$dest/" 2>/dev/null || true
  done
done

# kalibr python packages (kalibr_common, kalibr_camera_calibration, etc.) + scripts
# These live in kalibr/python/ and are imported as top-level (kalibr_common, etc.)
kalibr_python="$KALIBR_SRC/aslam_offline_calibration/kalibr/python"
kalibr_build_python="$BUILD_DIR/aslam_offline_calibration/kalibr/python"
for sub in kalibr_common kalibr_camera_calibration kalibr_imu_camera_calibration kalibr_rs_camera_calibration kalibr_errorterms; do
  if [[ -d "$kalibr_python/$sub" ]]; then
    mkdir -p "$TARGET_DIR/lib/$sub"
    cp -r "$kalibr_python/$sub"/*.py "$TARGET_DIR/lib/$sub/" 2>/dev/null || true
    [[ -f "$kalibr_python/$sub/__init__.py" ]] && cp "$kalibr_python/$sub/__init__.py" "$TARGET_DIR/lib/$sub/"
    # Copy subdirs (e.g. exporters)
    for d in "$kalibr_python/$sub"/*/; do
      [[ -d "$d" ]] || continue
      dn=$(basename "$d")
      mkdir -p "$TARGET_DIR/lib/$sub/$dn"
      cp "$d"*.py "$TARGET_DIR/lib/$sub/$dn/" 2>/dev/null || true
      [[ -f "$d/__init__.py" ]] && cp "$d/__init__.py" "$TARGET_DIR/lib/$sub/$dn/"
    done
  fi
done
# libkalibr_errorterms_python.so must be in PYTHONPATH root (same dir as kalibr_errorterms)
[[ -f "$kalibr_build_python/libkalibr_errorterms_python.so" ]] && \
  cp "$kalibr_build_python/libkalibr_errorterms_python.so" "$TARGET_DIR/lib/"

# Copy kalibr_* scripts to bin
for script in kalibr_calibrate_cameras kalibr_calibrate_imu_camera kalibr_calibrate_rs_cameras \
              kalibr_visualize_calibration kalibr_visualize_distortion kalibr_create_target_pdf \
              kalibr_bagcreater kalibr_bagextractor kalibr_camera_focus kalibr_camera_validator; do
  [[ -f "$kalibr_python/$script" ]] && cp "$kalibr_python/$script" "$TARGET_DIR/bin/"
done

# Create setup script for install dir
cat > "$TARGET_DIR/setup_kalibr.sh" << 'SETUP_EOF'
#!/bin/bash
# Source this to use kalibr from the install directory (no source tree needed).
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${INSTALL_DIR}/lib:${PYTHONPATH}"
export PATH="${INSTALL_DIR}/bin:${PATH}"
echo "kalibr ready. Run: kalibr_calibrate_cameras --help"
SETUP_EOF
chmod +x "$TARGET_DIR/setup_kalibr.sh"
chmod +x "$TARGET_DIR/bin/"*

echo "Done. Install dir: $TARGET_DIR"
echo "  lib/: $(find "$TARGET_DIR/lib" -name "*.so" | wc -l) .so files, Python packages"
echo "  bin/: $(ls "$TARGET_DIR/bin" 2>/dev/null | wc -l) scripts"
echo ""
echo "On target device:"
echo "  scp -r $TARGET_DIR root@<X5_IP>:/userdata/"
echo "  ssh root@<X5_IP>"
echo "  source /userdata/$(basename $TARGET_DIR)/setup_kalibr.sh"
echo "  kalibr_calibrate_cameras --help"
