import os
import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.substitutions import Command, EnvironmentVariable
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_scout_description = get_package_share_directory('scout_description')
    pkg_scout_gazebo = get_package_share_directory('scout_mini_dual_lidar_gazebo')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Launch configuration variables
    world = LaunchConfiguration('world')
    model = LaunchConfiguration('model')
    use_sim_time = LaunchConfiguration('use_sim_time')
    verbose = LaunchConfiguration('verbose')
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config = LaunchConfiguration('rviz_config')
    spawn_yaw = LaunchConfiguration('spawn_yaw')

    # Declare launch arguments
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_scout_gazebo, 'worlds', 'simple_test_world.world'),
        description='Full path to the world model file to load')

    declare_model_cmd = DeclareLaunchArgument(
        'model',
        default_value=os.path.join(pkg_scout_gazebo, 'urdf', 'scout_mini_gazebo.xacro'),
        description='Full path to the robot URDF/XACRO file')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')

    declare_verbose_cmd = DeclareLaunchArgument(
        'verbose',
        default_value='false',
        description='Enable verbose output')

    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Launch RViz2 for visualization')

    declare_rviz_config_cmd = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(pkg_scout_gazebo, 'rviz', 'display.rviz'),
        description='Path to RViz configuration file')

    declare_spawn_yaw_cmd = DeclareLaunchArgument(
        'spawn_yaw',
        default_value='3.14159',
        description='Initial yaw angle (radians) for robot spawn')

    # Get URDF via xacro with mesh_prefix parameter
    # Use file:// URI for Gazebo compatibility
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ',
        model,
        ' mesh_prefix:=file://' + pkg_scout_description,
    ])

    robot_description = {'robot_description': ParameterValue(robot_description_content, value_type=str)}

    # Robot State Publisher - publishes static TFs from URDF
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description, {'use_sim_time': use_sim_time}])

    # Gazebo launch using Ignition Gazebo (ros_gz_sim)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': ['-v 4 ', world] if verbose else world,
        }.items(),
    )

    # Spawn robot in Gazebo using ros_gz_sim
    # z = |wheel_vertical_offset| + wheel_radius = 0.100998 + 0.080 = 0.181m
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'scout_mini',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.181',  # |wheel_vertical_offset| + wheel_radius = 0.100998 + 0.080
            '-Y', spawn_yaw,
        ],
        output='screen')

    # ROS-Gazebo Bridges
    # Use gz.msgs namespace for ros-humble-ros-gz-bridge compatibility
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_bridge',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'qos_overrides./front/scan.subscription.reliability': 'best_effort',
            'qos_overrides./rear/scan.subscription.reliability': 'best_effort',
        }],
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
            '/front/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/rear/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        ])

    # Static TF publisher - maps Gazebo sensor frame to URDF frame
    # Gazebo sensors are placed at the URDF link position (<pose>0 0 0 0 0 0</pose>),
    # so the static TF should be identity (0,0,0,0,0,0). The Gazebo frame_id
    # "scout_mini/base_link/front_lidar_sensor" is at the same position as
    # the URDF frame "front_lidar_link".
    front_lidar_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='front_lidar_static_tf',
        arguments=[
            '0', '0', '0',  # identity - sensor IS at link position
            '0', '0', '0',  # identity rotation
            'front_lidar_link',                    # parent frame (URDF frame)
            'scout_mini/base_link/front_lidar_sensor'  # child frame (Gazebo frame)
        ],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    rear_lidar_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='rear_lidar_static_tf',
        arguments=[
            '0', '0', '0',  # identity - sensor IS at link position
            '0', '0', '0',  # identity rotation
            'rear_lidar_link',                     # parent frame (URDF frame)
            'scout_mini/base_link/rear_lidar_sensor'  # child frame (Gazebo frame)
        ],
        parameters=[{'use_sim_time': use_sim_time}],
    )



    # Bridge Gazebo model name prefix to ROS standard frame names
    model_prefix_tf_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='model_prefix_tf_odom',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'scout_mini/odom'],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    model_prefix_tf_base_link = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='model_prefix_tf_base_link',
        arguments=['0', '0', '0', '0', '0', '0', 'scout_mini/base_link', 'base_link'],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # IMU-corrected odometry — replaces DiffDrive angular with IMU gyro
    # Fixes skid-steer rotation drift in odometry
    imu_odom_corrector = Node(
        package='scout_mini_dual_lidar_gazebo',
        executable='imu_odom_corrector.py',
        name='imu_odom_corrector',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # Merge front + rear lidar scans into 360° scan for SLAM
    laser_merger = Node(
        package='scout_mini_dual_lidar_gazebo',
        executable='laser_merger.py',
        name='laser_merger',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # RViz2 - visualization (optional, controlled by use_rviz argument)
    node_rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz))

    # Set environment variables for Gazebo resource paths
    # Gazebo uses model:// URI which looks for model_name/meshes/... in resource paths
    # So we need to point to the parent directory containing scout_description folder
    scout_description_parent = os.path.dirname(pkg_scout_description)
    gz_resource_path = scout_description_parent + ':' + pkg_scout_gazebo + '/worlds'

    set_env_vars = [
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=gz_resource_path
        ),
        SetEnvironmentVariable(
            name='IGN_GAZEBO_RESOURCE_PATH',
            value=gz_resource_path
        ),
        SetEnvironmentVariable(
            name='GAZEBO_MODEL_PATH',
            value=scout_description_parent
        ),
    ]

    # Create the launch description and populate
    ld = LaunchDescription()

    # Add environment variables FIRST - MUST be set BEFORE Gazebo starts
    for env_var in set_env_vars:
        ld.add_action(env_var)

    # Declare the launch options
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_model_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_verbose_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_rviz_config_cmd)
    ld.add_action(declare_spawn_yaw_cmd)

    # Add the nodes to the launch description
    ld.add_action(gazebo)
    ld.add_action(node_robot_state_publisher)
    ld.add_action(spawn_entity)
    ld.add_action(gz_bridge)
    ld.add_action(front_lidar_static_tf)
    ld.add_action(rear_lidar_static_tf)
    ld.add_action(model_prefix_tf_odom)
    ld.add_action(model_prefix_tf_base_link)
    ld.add_action(imu_odom_corrector)
    ld.add_action(laser_merger)
    ld.add_action(node_rviz)


    return ld
