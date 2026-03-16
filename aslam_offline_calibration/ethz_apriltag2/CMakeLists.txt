cmake_minimum_required(VERSION 3.0.2)
project(ethz_apriltag2)

add_definitions(-fPIC -O3)

find_package(catkin REQUIRED)
find_package(Eigen3 REQUIRED)
# Headless: exclude highgui to avoid GTK dependency
find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs calib3d features2d)

catkin_package(
  INCLUDE_DIRS include ${EIGEN3_INCLUDE_DIRS}
  LIBRARIES ${PROJECT_NAME}
)

include_directories(include ${EIGEN3_INCLUDE_DIRS} ${catkin_INCLUDE_DIRS})

#library
file(GLOB SOURCE_FILES "src/*.cc")
add_library(${PROJECT_NAME}  ${SOURCE_FILES})
target_include_directories(${PROJECT_NAME} PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${EIGEN3_INCLUDE_DIRS}
)
target_link_libraries(${PROJECT_NAME} ${OpenCV_LIBS} ${catkin_LIBRARIES})

#demo (optional, requires libv4l2 - not always in sysroot for cross-compilation)
if(NOT APPLE)
  find_package(PkgConfig QUIET)
  pkg_check_modules(v4l2 QUIET libv4l2)
  if(v4l2_FOUND)
    add_executable(apriltags_demo src/example/apriltags_demo.cpp src/example/Serial.cpp)
    target_include_directories(apriltags_demo PRIVATE ${v4l2_INCLUDE_DIRS})
    target_link_libraries(apriltags_demo ${PROJECT_NAME} ${v4l2_LIBRARIES})
  endif()
endif()

##################
## Installation ##
##################

install(TARGETS ${PROJECT_NAME}
  ARCHIVE DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
  LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

## Mark cpp header files for installation
install(DIRECTORY include/
  DESTINATION ${CATKIN_GLOBAL_INCLUDE_DESTINATION}
)
