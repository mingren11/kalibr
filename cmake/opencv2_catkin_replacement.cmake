# Replace opencv2_catkin with direct OpenCV
add_library(opencv2_catkin INTERFACE)
target_link_libraries(opencv2_catkin INTERFACE ${OpenCV_LIBS})
target_include_directories(opencv2_catkin INTERFACE ${OpenCV_INCLUDE_DIRS})
set(opencv2_catkin_LIBRARIES ${OpenCV_LIBS})
set(opencv2_catkin_INCLUDE_DIRS ${OpenCV_INCLUDE_DIRS})
