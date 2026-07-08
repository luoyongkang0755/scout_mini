import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_scout_description = get_package_share_directory('scout_description')
    pkg_scout_gazebo_sim = get_package_share_directory('scout_gazebo_sim')

    world_file = os.path.join(pkg_scout_gazebo_sim, 'worlds', 'simple_test_world.world')

    robot_description_content = Command([
        PathJoinSubstitution(['xacro']), ' ',
        PathJoinSubstitution([
            FindPackageShare('scout_description'), 'urdf', 'scout_mini.xacro'
        ]),
        ' mesh_prefix:=package://scout_description',
    ])

    return LaunchDescription([
        # Let Gazebo Ignition find mesh files via package:// URIs
        SetEnvironmentVariable('GAZEBO_MODEL_PATH', pkg_scout_description),

        DeclareLaunchArgument('world', default_value=world_file,
                              description='Path to the Gazebo world file'),
        DeclareLaunchArgument('robot_name', default_value='scout_mini',
                              description='Name for the robot in Gazebo'),
        DeclareLaunchArgument('start_x', default_value='0.0',
                              description='X starting position'),
        DeclareLaunchArgument('start_y', default_value='0.0',
                              description='Y starting position'),
        DeclareLaunchArgument('start_z', default_value='0.25',
                              description='Z starting position'),
        DeclareLaunchArgument('start_yaw', default_value='1.57',
                              description='Yaw starting orientation'),

        # Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'robot_description': ParameterValue(robot_description_content, value_type=str),
            }],
        ),

        # Launch Gazebo server (headless)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
                ])
            ]),
            launch_arguments={
                'gz_args': [
                    '-r ', LaunchConfiguration('world')
                ],
                'on_exit_shutdown': 'true',
            }.items(),
        ),

        # Spawn robot in Gazebo Ignition
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', LaunchConfiguration('robot_name'),
                '-topic', '/robot_description',
                '-x', LaunchConfiguration('start_x'),
                '-y', LaunchConfiguration('start_y'),
                '-z', LaunchConfiguration('start_z'),
                '-Y', LaunchConfiguration('start_yaw'),
            ],
            output='screen',
        ),

        # Bridge for TF and clock
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/model/scout_mini/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            ],
            output='screen',
        ),
    ])
