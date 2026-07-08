#!/usr/bin/env python3
"""Convert /odom (nav_msgs/Odometry) to TF broadcast: odom -> base_link."""
import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class OdomToTF(Node):
    def __init__(self):
        super().__init__('odom_to_tf')
        self.sub = self.create_subscription(Odometry, '/odom', self.callback, 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.get_logger().info('Broadcasting odom->base_link TF from /odom (yaw negated)')

    def callback(self, msg):
        q = msg.pose.pose.orientation

        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z

        t.transform.rotation = q

        self.tf_broadcaster.sendTransform(t)


def main():
    rclpy.init()
    rclpy.spin(OdomToTF())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
