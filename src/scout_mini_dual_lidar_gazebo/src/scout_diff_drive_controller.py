#!/usr/bin/env python3
"""
Simple differential drive controller for Scout Mini in Ignition Gazebo.
Directly controls joint velocities via Ignition topics.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import subprocess
import json

class ScoutDiffDriveController(Node):
    def __init__(self):
        super().__init__('scout_diff_drive_controller')
        
        # Parameters
        self.declare_parameter('wheel_separation', 0.416503)  # track width
        self.declare_parameter('wheel_radius', 0.08)           # wheel radius (0.16m diameter / 2)    
        
        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.wheel_radius = self.get_parameter('wheel_radius').value
        
        # Subscribe to cmd_vel
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10)
        
        self.get_logger().info('Scout Diff Drive Controller initialized')
        self.get_logger().info(f'Wheel separation: {self.wheel_separation}m')
        self.get_logger().info(f'Wheel radius: {self.wheel_radius}m')
    
    def cmd_vel_callback(self, msg):
        # Convert Twist to wheel velocities
        v_linear = msg.linear.x
        v_angular = msg.angular.z
        
        # Calculate wheel angular velocities (rad/s)
        left_vel = (v_linear - v_angular * self.wheel_separation / 2) / self.wheel_radius
        right_vel = (v_linear + v_angular * self.wheel_separation / 2) / self.wheel_radius
        
        # Send commands to Ignition Gazebo using ign topic command
        # Rear wheels are the drive wheels
        self.send_joint_cmd('rear_left_wheel', left_vel)
        self.send_joint_cmd('rear_right_wheel', right_vel)
        # Front wheels are free-rolling, but we can set them too
        self.send_joint_cmd('front_left_wheel', left_vel)
        self.send_joint_cmd('front_right_wheel', right_vel)
        
        self.get_logger().info(f'Cmd: linear={v_linear:.2f}, angular={v_angular:.2f} -> L={left_vel:.2f}, R={right_vel:.2f}')
    
    def send_joint_cmd(self, joint_name, velocity):
        """Send joint velocity command to Ignition Gazebo"""
        try:
            # Use ign topic to publish joint velocity command
            cmd = [
                'ign', 'topic', '-t', f'/model/scout_mini/joint/{joint_name}/cmd_vel',
                '-m', 'ignition.msgs.Double',
                '-p', f'{velocity}'
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            self.get_logger().warn(f'Failed to send command to {joint_name}: {e.stderr.decode()}')


def main(args=None):
    rclpy.init(args=args)
    node = ScoutDiffDriveController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
