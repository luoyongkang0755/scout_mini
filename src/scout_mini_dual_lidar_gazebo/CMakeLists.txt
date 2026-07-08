cmake_minimum_required(VERSION 3.8)
project(scout_mini_dual_lidar_gazebo)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(scout_description REQUIRED)
find_package(ros_gz_sim REQUIRED)
find_package(robot_state_publisher REQUIRED)
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)

install(DIRECTORY launch worlds params config urdf rviz maps
  DESTINATION share/${PROJECT_NAME}/
)

install(PROGRAMS
  src/tf_static_relay.py
  src/tf_to_odom.py
  src/laser_merger.py
  src/auto_path_driver.py
  src/imu_odom_corrector.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
