cmake_minimum_required(VERSION 3.0.2)
project(sm_opencv)

set(CMAKE_CXX_STANDARD 14)

find_package(catkin REQUIRED COMPONENTS sm_common)
find_package(Boost REQUIRED COMPONENTS system)

catkin_package(
  INCLUDE_DIRS include  ${catkin_INCLUDE_DIRS}
  CATKIN_DEPENDS sm_common
  DEPENDS Boost
)
add_definitions(-D__STRICT_ANSI__)

# Header-only: create INTERFACE library for include propagation
add_library(${PROJECT_NAME} INTERFACE)
target_include_directories(${PROJECT_NAME} INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${Boost_INCLUDE_DIRS}
)
target_link_libraries(${PROJECT_NAME} INTERFACE ${catkin_LIBRARIES})

install(DIRECTORY include/
  DESTINATION ${CATKIN_GLOBAL_INCLUDE_DESTINATION}
)
