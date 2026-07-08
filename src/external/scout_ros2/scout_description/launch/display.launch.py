import os
import launch
import launch_ros

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import FindExecutable, PathJoinSubstitution
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    model_name = LaunchConfiguration('model')
    rviz_config_arg = LaunchConfiguration('rviz_config')

    # Get package directories
    pkg_scout_description = get_package_share_directory('scout_description')

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]), " ",
        PathJoinSubstitution(
            [FindPackageShare("scout_description"), "urdf", model_name]
        ),
        " mesh_prefix:=package://scout_description",
    ])

    default_rviz_path = os.path.join(pkg_scout_description, 'rviz', 'display.rviz')

    return launch.LaunchDescription([
        DeclareLaunchArgument('model', default_value='scout_mini.xacro',
            description='URDF/XACRO model file'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
            description='Use simulation clock if true'),
        DeclareLaunchArgument('rviz_config', default_value=default_rviz_path,
            description='Path to RViz configuration file'),
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false'],
            description='Enable GUI if true'),


        launch_ros.actions.Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'robot_description': ParameterValue(robot_description_content, value_type=str)
            }]),

        launch_ros.actions.Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time')
            }],
            condition=UnlessCondition(LaunchConfiguration('gui'))
        ),

        launch_ros.actions.Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            condition=IfCondition(LaunchConfiguration('gui'))
        ),

        launch_ros.actions.Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_arg],
        ),
    ])
