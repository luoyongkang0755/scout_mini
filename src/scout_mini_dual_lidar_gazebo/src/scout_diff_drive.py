#!/usr/bin/env python3
"""
Scout Mini differential drive controller node.
Converts /cmd_vel to wheel joint velocity commands.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64

class ScoutDiffDrive(Node):
    def __init__(self):
        super().__init__('scout_diff_drive')
        
        # Parameters
        self.declare_parameter('wheel_separation', 0.416503)
        self.declare_parameter('wheel_radius', 0.100998)        
        
        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.wheel_radius = self.get_parameter('wheel_radius').value
        
        # Subscribe to cmd_vel
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10)
        
        # Publishers for wheel velocity controllers
        # For Ignition Gazebo, we use /model/scout_mini/joint/controller_name
        self.left_wheel_pub = self.create_publisher(
            Float64,
            '/model/scout_mini/joint/rear_left_wheel/cmd_pos',
            10)
        self.right_wheel_pub = self.create_publisher(
            Float64,
            '/model/scout_mini/joint/rear_right_wheel/cmd_pos',
            10)
        
        self.get_logger().info('Scout Diff Drive initialized')
        self.get_logger().info(f'Wheel separation: {self.wheel_separation}')
        self.get_logger().info(f'Wheel radius: {self.wheel_radius}')
    
    def cmd_vel_callback(self, msg):
        # Convert Twist to wheel velocities
        # v_left = (v.linear.x - v.angular.z * wheel_separation / 2) / wheel_radius
        # v_right = (v.linear.x + v.angular.z * wheel_separation / 2) / wheel_radius
        
        v_linear = msg.linear.x
        v_angular = msg.angular.z
        
        v_left = (v_linear - v_angular * self.wheel_separation / 2) / self.wheel_radius
        v_right = (v_linear + v_angular * self.wheel_separation / 2) / self.wheel_radius
        
        # Publish as position commands (for position controller)
        # or velocity commands depending on Gazebo configuration
        left_msg = Float64()
        right_msg = Float64()
        
        # Use velocity mode - small position increments for continuous rotation
        left_msg.data = v_left * 0.01  # Scale factor for velocity
        right_msg.data = v_right * 0.01
        
        self.left_wheel_pub.publish(left_msg)
        self.right_wheel_pub.publish(right_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScoutDiffDrive()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
