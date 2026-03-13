# Fake Findcatkin for standalone build - handles COMPONENTS as workspace package targets
set(catkin_FOUND TRUE)
set(catkin_INCLUDE_DIRS "")
set(catkin_LIBRARIES "")

foreach(_comp ${catkin_FIND_COMPONENTS})
  if(TARGET ${_comp})
    list(APPEND catkin_LIBRARIES ${_comp})
  endif()
endforeach()
