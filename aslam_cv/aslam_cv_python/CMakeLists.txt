cmake_minimum_required(VERSION 3.0.2)
project(aslam_cv_python)

set(CMAKE_CXX_STANDARD 14)

find_package(Boost REQUIRED COMPONENTS serialization) 
find_package(catkin REQUIRED COMPONENTS
  sm_common
  sm_eigen
  sm_kinematics
  sm_python
  sm_opencv
  opencv2_catkin
  python_module
  aslam_cv_serialization
  aslam_imgproc
  aslam_cameras
  aslam_time
)

catkin_package(
  INCLUDE_DIRS include
)

add_definitions(-fPIC -Wextra -Winit-self -Woverloaded-virtual -Wnon-virtual-dtor -Wsign-promo -Wno-long-long)

if(APPLE)
  add_definitions( -ftemplate-depth-1024)
endif()

include_directories(include ${catkin_INCLUDE_DIRS})

add_python_export_library(${PROJECT_NAME} python/aslam_cv
  src/module.cpp
  src/CameraGeometries.cpp
  src/CameraGeometry.cpp
  src/Time.cpp
  src/Frontend.cpp
  src/Frame.cpp
  src/CameraProjections.cpp
  src/CameraShutters.cpp
  src/GridCalibration.cpp
  src/Undistorters.cpp
  src/OmniUndistorter.cpp
  src/PinholeUndistorter.cpp
)
target_compile_options(${PROJECT_NAME} PUBLIC "-Wno-deprecated-copy") # TODO: Fix...

# aslam_cv_serialization contains BOOST_CLASS_EXPORT_IMPLEMENT static initializers
# that must be force-included via --whole-archive. The library also appears normally
# in catkin_LIBRARIES (as a transitive dep), so we use --allow-multiple-definition
# to suppress the resulting duplicate symbol error (identical symbols, same library).
target_link_libraries(${PROJECT_NAME}
  -Wl,--allow-multiple-definition
  -Wl,--whole-archive $<TARGET_FILE:aslam_cv_serialization> -Wl,--no-whole-archive
  ${Boost_LIBRARIES}
)

##################
## Installation ##
##################
install(DIRECTORY include/
  DESTINATION ${CATKIN_GLOBAL_INCLUDE_DESTINATION}
)
