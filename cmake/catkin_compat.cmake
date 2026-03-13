# Catkin compatibility layer for standalone CMake build
# Provides minimal catkin-like macros and variables.
# Packages must use target_link_libraries() for workspace deps instead of find_package(catkin COMPONENTS).

set(catkin_FOUND TRUE)
set(catkin_INCLUDE_DIRS "")
set(catkin_LIBRARIES "")

# Minimal catkin_package - no-op
macro(catkin_package)
endmacro()

# Replace catkin_add_gtest (handles WORKING_DIRECTORY, etc.)
function(catkin_add_gtest target)
  if(NOT CATKIN_ENABLE_TESTING)
    return()
  endif()
  find_package(GTest QUIET)
  if(NOT GTest_FOUND)
    return()
  endif()
  set(_sources)
  set(_working_dir)
  set(_skip 0)
  foreach(_arg ${ARGN})
    if(_arg STREQUAL "WORKING_DIRECTORY")
      set(_skip 1)
    elseif(_skip EQUAL 1)
      set(_working_dir ${_arg})
      set(_skip 0)
    else()
      list(APPEND _sources ${_arg})
    endif()
  endforeach()
  add_executable(${target} ${_sources})
  target_link_libraries(${target} GTest::gtest GTest::gtest_main)
  if(_working_dir)
    set_property(TARGET ${target} PROPERTY WORKING_DIRECTORY ${_working_dir})
  endif()
endfunction()

# catkin_python_setup - no-op
macro(catkin_python_setup)
endmacro()

# catkin_add_nosetests - no-op
macro(catkin_add_nosetests)
endmacro()

# catkin_install_python - install Python scripts
macro(catkin_install_python)
  cmake_parse_arguments(_cip "" "DESTINATION" "PROGRAMS" ${ARGN})
  if(_cip_PROGRAMS AND _cip_DESTINATION)
    install(PROGRAMS ${_cip_PROGRAMS} DESTINATION ${_cip_DESTINATION})
  endif()
endmacro()
