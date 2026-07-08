#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_gazebo = get_package_share_directory('scout_mini_dual_lidar_gazebo')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    slam_params_file = LaunchConfiguration('slam_params_file')

    declared_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(pkg_gazebo, 'params', 'slam_toolbox_params.yaml'),
            description='Full path to the ROS2 parameters file to use for the SLAM Toolbox node'),
    ]

    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {'use_sim_time': use_sim_time},
        ],
    )

    ld = LaunchDescription(declared_args)
    ld.add_action(slam_toolbox_node)

    return ld
