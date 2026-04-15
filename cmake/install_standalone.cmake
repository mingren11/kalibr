# Standalone install: Python packages (.py) + setup script for relocatable deploy
# The .so files are installed by add_python_export_library to lib/python3/dist-packages/<pkg>/
# We add the .py sources and a setup script. libkalibr_errorterms_python.so goes to lib/ via kalibr.

set(_PY_DEST ${CATKIN_GLOBAL_PYTHON_DESTINATION})

# Python package sources: install to same location as .so (lib/python3/dist-packages/<pkg>/)
set(_PY_PACKAGES
  Schweizer-Messer/numpy_eigen/python/numpy_eigen
  Schweizer-Messer/sm_python/python/sm
  aslam_optimizer/aslam_backend_python/python/aslam_backend
  aslam_incremental_calibration/incremental_calibration_python/src/incremental_calibration
  aslam_nonparametric_estimation/bsplines_python/python/bsplines
  aslam_nonparametric_estimation/aslam_splines_python/python/aslam_splines
  aslam_cv/aslam_cv_python/python/aslam_cv
  aslam_cv/aslam_cv_backend_python/python/aslam_cv_backend
  aslam_cv/aslam_cameras_april/python/aslam_cameras_april
)

foreach(_rel ${_PY_PACKAGES})
  get_filename_component(_pkg_name ${_rel} NAME)
  install(DIRECTORY ${_rel}/
    DESTINATION ${_PY_DEST}/${_pkg_name}
    FILES_MATCHING PATTERN "*.py"
    PATTERN "__pycache__" EXCLUDE
  )
endforeach()

# kalibr packages (kalibr_common, kalibr_camera_calibration, etc.)
set(_KALIBR_PY aslam_offline_calibration/kalibr/python)
foreach(_sub kalibr_common kalibr_camera_calibration kalibr_imu_camera_calibration kalibr_rs_camera_calibration kalibr_errorterms)
  install(DIRECTORY ${_KALIBR_PY}/${_sub}/
    DESTINATION ${_PY_DEST}/${_sub}
    FILES_MATCHING PATTERN "*.py"
    PATTERN "__pycache__" EXCLUDE
  )
endforeach()
# exporters (used by kalibr scripts)
install(DIRECTORY ${_KALIBR_PY}/exporters/
  DESTINATION ${_PY_DEST}/exporters
  FILES_MATCHING PATTERN "*.py"
  PATTERN "__pycache__" EXCLUDE
)

# Helper scripts shipped with the standalone install.
install(PROGRAMS
  ${CMAKE_CURRENT_SOURCE_DIR}/looper_format.py
  DESTINATION ${CATKIN_GLOBAL_BIN_DESTINATION}
)

# Default config files shipped with the standalone install.
install(FILES
  ${CMAKE_CURRENT_SOURCE_DIR}/config/imu.yaml
  ${CMAKE_CURRENT_SOURCE_DIR}/config/target.yaml
  DESTINATION .
)

install(PROGRAMS
  ${CMAKE_CURRENT_SOURCE_DIR}/run_kalibr.sh
  DESTINATION .
)

# setup_kalibr.sh for install dir (PYTHONPATH = lib + lib/python3/dist-packages, PATH = bin)
set(_SETUP_SCRIPT "#!/bin/bash
# Source this to use kalibr from the install directory.
INSTALL_DIR=\"\$(cd \"\$(dirname \"\${BASH_SOURCE[0]}\")\" && pwd)\"
export PYTHONPATH=\"\${INSTALL_DIR}/lib:\${INSTALL_DIR}/lib/python3/dist-packages:\${PYTHONPATH}\"
export PATH=\"\${INSTALL_DIR}/bin:\${PATH}\"
echo \"kalibr ready. Run: kalibr_calibrate_cameras --help\"
")
file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/setup_kalibr_install.sh" CONTENT "${_SETUP_SCRIPT}")
install(PROGRAMS ${CMAKE_BINARY_DIR}/setup_kalibr_install.sh DESTINATION . RENAME setup_kalibr.sh)
