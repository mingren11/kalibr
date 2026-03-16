# Kalibr standalone CMake build (no catkin/ROS)
cmake_minimum_required(VERSION 3.14)
project(kalibr_standalone LANGUAGES CXX)

# Install to build/install for relocatable deploy (set OFF to use system prefix)
option(KALIBR_INSTALL_TO_BUILD "Install to build/install dir for deploy (copy to device)" ON)
if(KALIBR_INSTALL_TO_BUILD)
  set(CMAKE_INSTALL_PREFIX "${CMAKE_BINARY_DIR}/install" CACHE PATH "Install directory" FORCE)
endif()

# Shadow system catkin when ROS is installed (e.g. in dev Docker)
# Our fake catkinConfig.cmake must be found before /opt/ros
list(INSERT CMAKE_PREFIX_PATH 0 ${CMAKE_CURRENT_SOURCE_DIR}/cmake/standalone_catkin_prefix)

set(CMAKE_CXX_STANDARD 14)

# Required for static libs linked into Python .so extensions
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Install destinations (catkin-compatible names for minimal package changes)
set(CATKIN_PACKAGE_LIB_DESTINATION lib)
set(CATKIN_GLOBAL_LIB_DESTINATION lib)
set(CATKIN_PACKAGE_BIN_DESTINATION bin)
set(CATKIN_GLOBAL_BIN_DESTINATION bin)
set(CATKIN_GLOBAL_INCLUDE_DESTINATION include)
set(CATKIN_PACKAGE_INCLUDE_DESTINATION include/${PROJECT_NAME})
set(CATKIN_GLOBAL_PYTHON_DESTINATION lib/python3/dist-packages)
set(CATKIN_DEVEL_PREFIX ${CMAKE_BINARY_DIR})
set(CATKIN_PACKAGE_SHARE_DESTINATION share/${PROJECT_NAME})

# Testing
option(BUILD_TESTING "Build tests" ON)
set(CATKIN_ENABLE_TESTING ${BUILD_TESTING})

# Include compatibility macros and fake Findcatkin
list(INSERT CMAKE_MODULE_PATH 0
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake
  ${CMAKE_CURRENT_SOURCE_DIR}/Schweizer-Messer/python_module/cmake
)
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/catkin_compat.cmake)
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/add_python_export_library_standalone.cmake)

# Find common dependencies
find_package(Boost REQUIRED COMPONENTS system filesystem serialization thread regex)
find_package(Eigen3 REQUIRED)
# Headless: exclude highgui to avoid GTK dependency (libgtk-3.so.0)
find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs calib3d features2d)
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/aslam_optimizer/sparse_block_matrix/cmake)
find_package(SuiteSparse REQUIRED)
find_package(TBB REQUIRED)
# Cross-compilation: point Python3 to target sysroot (host interpreter used for cmake scripts)
if(CMAKE_CROSSCOMPILING AND CMAKE_SYSROOT)
  set(_py_usr ${CMAKE_SYSROOT}/usr)
  set(Python3_INCLUDE_DIR ${_py_usr}/include/python3.10 CACHE PATH "")
  set(Python3_LIBRARY ${_py_usr}/lib/aarch64-linux-gnu/libpython3.10.so CACHE FILEPATH "")
  set(Python3_NumPy_INCLUDE_DIR ${_py_usr}/lib/python3/dist-packages/numpy/core/include CACHE PATH "")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter Development NumPy)
find_package(PkgConfig REQUIRED)
pkg_check_modules(v4l libv4l)  # Optional, for ethz_apriltag2 demo

# Migration stages - disable tiers for incremental verification
option(KALIBR_BUILD_TIER2 "Build tier 2+: sm_*, numpy_eigen, aslam_*, kalibr" ON)
# Tier 1: No workspace deps
add_subdirectory(Schweizer-Messer/sm_common)
add_subdirectory(Schweizer-Messer/sm_random)
add_subdirectory(Schweizer-Messer/sm_logging)
add_subdirectory(aslam_cv/aslam_time)
add_subdirectory(Schweizer-Messer/python_module)

if(KALIBR_BUILD_TIER2)
  # Tier 2: sm_common, sm_random, etc.
  add_subdirectory(Schweizer-Messer/sm_property_tree)
  add_subdirectory(Schweizer-Messer/sm_boost)
  add_subdirectory(Schweizer-Messer/sm_opencv)
  add_subdirectory(Schweizer-Messer/sm_eigen)
  add_subdirectory(Schweizer-Messer/sm_timing)
  add_subdirectory(Schweizer-Messer/sm_matrix_archive)
  add_subdirectory(Schweizer-Messer/sm_kinematics)
  add_subdirectory(Schweizer-Messer/numpy_eigen)

  # Tier 3: opencv2 replacement
  include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/opencv2_catkin_replacement.cmake)

  # Tier 4: sparse_block_matrix, aslam_backend, bsplines
  add_subdirectory(aslam_optimizer/sparse_block_matrix)
  add_subdirectory(aslam_optimizer/aslam_backend)
  add_subdirectory(aslam_optimizer/aslam_backend_expressions)
  add_subdirectory(aslam_nonparametric_estimation/bsplines)
  add_subdirectory(aslam_optimizer/aslam_backend_python)
  add_subdirectory(aslam_nonparametric_estimation/bsplines_python)

  # Tier 5: incremental_calibration, aslam_cameras
  add_subdirectory(aslam_incremental_calibration/incremental_calibration)
  add_subdirectory(aslam_incremental_calibration/incremental_calibration_python)
  add_subdirectory(aslam_cv/aslam_cameras)
  add_subdirectory(aslam_cv/aslam_cv_serialization)
  add_subdirectory(aslam_nonparametric_estimation/aslam_splines)
  add_subdirectory(aslam_cv/aslam_cv_backend)
  add_subdirectory(aslam_cv/aslam_imgproc)
  add_subdirectory(aslam_cv/aslam_cv_error_terms)

  # Tier 6: sm_python, aslam_cv_python, etc.
  add_subdirectory(Schweizer-Messer/sm_python)
  add_subdirectory(aslam_offline_calibration/ethz_apriltag2)
  add_subdirectory(aslam_cv/aslam_cv_python)
  add_subdirectory(aslam_cv/aslam_cameras_april)
  add_subdirectory(aslam_nonparametric_estimation/aslam_splines_python)
  add_subdirectory(aslam_cv/aslam_cv_backend_python)

  # Tier 7: kalibr
  add_subdirectory(aslam_offline_calibration/kalibr)

  # Standalone install: Python .py packages + setup_kalibr.sh
  include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/install_standalone.cmake)
endif()
