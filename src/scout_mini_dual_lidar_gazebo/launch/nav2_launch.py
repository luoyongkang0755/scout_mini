#!/usr/bin/env python3
"""
Minimal Nav2 Launch File for Scout Mini
Task 19 — Get all Nav2 lifecycle nodes active before tuning navigation behavior.

Usage:
    ros2 launch scout_mini_dual_lidar_gazebo nav2_launch.py

Prerequisites:
    1. Gazebo simulation running: ros2 launch scout_mini_dual_lidar_gazebo scout_mini_gazebo.launch.py
    2. Saved map: src/maps/my_map.yaml + my_map.pgm
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Package paths
    pkg_nav2 = get_package_share_directory('scout_mini_dual_lidar_gazebo')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock if true')

    declare_map_yaml = DeclareLaunchArgument(
        'map',
        default_value=os.path.abspath(os.path.join(pkg_nav2, 'maps', 'my_map.yaml')),
        description='Full path to map yaml file')

    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_nav2, 'config', 'nav2_params.yaml'),
        description='Full path to Nav2 params file')

    # Nav2 lifecycle manager — controls activation of all Nav2 nodes
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time,
                     'autostart': True,
                     'node_names': [
                         'map_server',
                         'amcl',
                         'planner_server',
                         'controller_server',
                         'recoveries_server',
                         'bt_navigator',
                         'waypoint_follower',
                     ]}])

    # Map server — serves the pre-saved map
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time,
                     'yaml_filename': map_yaml_file}])

    # AMCL — Adaptive Monte Carlo Localization
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time}])

    # Planner server — global path planning (NavFn)
    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time}])

    # Controller server — local path following (DWB)
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time}])

    # Recoveries server — spin, backup, wait behaviors
    recoveries_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='recoveries_server',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time}])

    # BT Navigator — behavior tree engine for Nav2
    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time,
                     'default_nav_to_pose_bt_xml':
                         os.path.join(pkg_nav2, 'config', 'navigate_w_recovery.xml'),
                     'default_nav_through_poses_bt_xml':
                         os.path.join(pkg_nav2, 'config', 'navigate_w_recovery.xml')}])

    # Waypoint follower
    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[params_file,
                    {'use_sim_time': use_sim_time}])

    # RViz2 with Nav2 configuration
    rviz_config = os.path.join(pkg_nav2_bringup, 'rviz', 'nav2_default_view.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('use_rviz', default='true')))

    ld = LaunchDescription()

    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_map_yaml)
    ld.add_action(declare_params_file)

    ld.add_action(map_server)
    ld.add_action(amcl)
    ld.add_action(planner_server)
    ld.add_action(controller_server)
    ld.add_action(recoveries_server)
    ld.add_action(bt_navigator)
    ld.add_action(waypoint_follower)
    ld.add_action(lifecycle_manager)
    ld.add_action(rviz)

    return ld
