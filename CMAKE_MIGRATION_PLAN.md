# Kalibr Catkin → CMake 迁移计划

## 目标
将 kalibr 从 catkin 构建迁移到纯 CMake，实现无 ROS 构建。

## 迁移架构

### 新增文件
- `kalibr/CMakeLists.txt` - 顶层 CMake 入口
- `kalibr/cmake/Findcatkin.cmake` - 兼容 find_package(catkin)
- `kalibr/cmake/catkin_compat.cmake` - catkin_package、catkin_add_gtest 等宏
- `kalibr/cmake/opencv2_catkin_replacement.cmake` - 替换 opencv2_catkin
- `kalibr/cmake/add_python_export_library_standalone.cmake` - Python 扩展构建

### 依赖顺序（Tier）
| Tier | 包 | 说明 |
|------|-----|------|
| 1 | sm_common, sm_random, sm_logging, aslam_time, python_module | ✅ 已验证 |
| 2 | sm_property_tree, sm_boost, sm_opencv, sm_eigen, sm_timing, sm_matrix_archive, sm_kinematics, numpy_eigen | |
| 3 | sparse_block_matrix, aslam_backend, aslam_backend_expressions, bsplines, aslam_backend_python, bsplines_python | |
| 4 | incremental_calibration, aslam_cameras, aslam_cv_serialization, aslam_splines, aslam_cv_backend, aslam_imgproc, aslam_cv_error_terms | |
| 5 | sm_python, ethz_apriltag2, aslam_cv_python, aslam_cameras_april, aslam_splines_python, aslam_cv_backend_python | |
| 6 | kalibr | |

## 验证步骤

1. **Tier 1**: `cmake .. -DKALIBR_BUILD_TIER2=OFF && make` 应成功
2. **Tier 2**: 启用 KALIBR_BUILD_TIER2，逐个修复编译错误
3. **全量**: 所有 tier 通过后，运行 `kalibr_calibrate_cameras --folder ...` 验证

## 外部依赖
- Boost, Eigen3, OpenCV, SuiteSparse, TBB, Python3+NumPy
- 系统包: libsuitesparse-dev, libboost-all-dev, libeigen3-dev, libopencv-dev, libtbb-dev
