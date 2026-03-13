# Fake catkinConfig for standalone build - shadows system catkin when ROS is installed
# Placed at <prefix>/catkinConfig.cmake so find_package(catkin) finds this first

set(catkin_FOUND TRUE)
set(catkin_INCLUDE_DIRS "")
set(catkin_LIBRARIES "")
set(catkin_LIBRARY_DIRS "")
set(catkin_EXPORTED_TARGETS "")
set(catkin_FOUND_CATKIN_PROJECT TRUE)

# Include our compatibility layer (provides catkin_package, etc.)
get_filename_component(_this_dir "${CMAKE_CURRENT_LIST_FILE}" PATH)
get_filename_component(_kalibr_cmake_dir "${_this_dir}/.." ABSOLUTE)
include("${_kalibr_cmake_dir}/catkin_compat.cmake")

# Handle COMPONENTS: workspace packages are CMake targets, not installed pkgs
foreach(_comp ${catkin_FIND_COMPONENTS})
  if(TARGET ${_comp})
    list(APPEND catkin_LIBRARIES ${_comp})
  endif()
endforeach()

# Add dummy target if empty (some packages expect catkin_EXPORTED_TARGETS)
if(NOT catkin_EXPORTED_TARGETS)
  if(NOT TARGET _catkin_empty_exported_target)
    add_custom_target(_catkin_empty_exported_target)
  endif()
  list(APPEND catkin_EXPORTED_TARGETS _catkin_empty_exported_target)
endif()
