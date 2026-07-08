#!/usr/bin/env python3
"""Auto-drive test path — square loop in world (-4,0)→(-4,2)→(0,2)→(0,0)"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time

class AutoPathDriver(Node):
    def __init__(self):
        super().__init__('auto_path_driver')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def go(self, linear, angular, duration):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        end = self.get_clock().now().nanoseconds * 1e-9 + duration
        while self.get_clock().now().nanoseconds * 1e-9 < end:
            self.pub.publish(msg)
            time.sleep(0.05)
        # stop briefly between segments
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self.pub.publish(msg)
        time.sleep(0.5)

    def run(self):
        self.get_logger().info('Starting auto path in 3 seconds...')
        time.sleep(3)

        # 1. Forward 4m (robot faces -X, so go 4m at 0.5 m/s = 8s)
        self.get_logger().info('Step 1/4: Forward 4m')
        self.go(0.5, 0.0, 8.0)

        # 2. Right turn 90° (0.8 rad/s * ~2s ≈ 90°)
        self.get_logger().info('Step 2/4: Right turn 90°')
        self.go(0.0, -0.8, 2.2)

        # 3. Forward 2m
        self.get_logger().info('Step 3/4: Forward 2m')
        self.go(0.5, 0.0, 4.0)

        # 4. Right turn 90°
        self.get_logger().info('Step 4/4: Right turn 90°')
        self.go(0.0, -0.8, 2.2)

        # 5. Forward 4m back to start
        self.get_logger().info('Step 5/6: Forward 4m')
        self.go(0.5, 0.0, 8.0)

        # 6. Right turn 90°
        self.get_logger().info('Step 6/6: Right turn 90°')
        self.go(0.0, -0.8, 2.2)

        # 7. Forward 2m back to origin
        self.get_logger().info('Step 7/7: Forward 2m (back to start)')
        self.go(0.5, 0.0, 4.0)

        self.get_logger().info('Path complete! Check RViz map.')

def main():
    rclpy.init()
    node = AutoPathDriver()
    node.run()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
