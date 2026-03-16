# Standalone version of add_python_export_library (no catkin)
# Mirrors catkin behavior: PREFIX "lib", placed inside source Python package dir.
FUNCTION(add_python_export_library TARGET_NAME PYTHON_MODULE_DIRECTORY)

  get_filename_component(TMP "${PYTHON_MODULE_DIRECTORY}/garbage.txt" PATH)
  get_filename_component(PYTHON_PACKAGE_NAME "${TMP}.txt" NAME_WE)
  get_filename_component(PYTHON_MODULE_DIRECTORY_PREFIX "${TMP}.txt" PATH)

  # Use Python3
  find_package(Python3 REQUIRED COMPONENTS Development)

  # Boost.Python for Python3 (match Python3 version, e.g. python310 for 3.10)
  if(APPLE)
    set(BOOST_COMPONENTS system)
  else()
    string(REPLACE "." "" _py_ver "${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}")
    set(BOOST_COMPONENTS python${_py_ver})
  endif()
  find_package(Boost REQUIRED COMPONENTS ${BOOST_COMPONENTS})

  add_library(${TARGET_NAME} SHARED ${ARGN})
  target_link_libraries(${TARGET_NAME}
    Python3::Python
    ${catkin_LIBRARIES}
    ${Boost_LIBRARIES}
  )
  target_include_directories(${TARGET_NAME} PRIVATE
    ${Python3_INCLUDE_DIRS}
    ${Python3_NumPy_INCLUDE_DIRS}
  )

  # Mirror catkin: PREFIX "lib" so the .so becomes lib${TARGET_NAME}.so,
  # placed directly inside the Python source package directory so that
  # __init__.py can do "from .lib${TARGET_NAME} import *".
  set_target_properties(${TARGET_NAME} PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${PYTHON_MODULE_DIRECTORY}"
    PREFIX "lib"
    SUFFIX ".so"
  )

  install(TARGETS ${TARGET_NAME}
    LIBRARY DESTINATION ${CATKIN_GLOBAL_PYTHON_DESTINATION}/${PYTHON_PACKAGE_NAME}
  )

ENDFUNCTION()
