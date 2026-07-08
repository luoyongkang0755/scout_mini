#!/usr/bin/env python3
"""Relay /tf_static messages to /tf so slam_toolbox receives all transforms on one topic."""
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


class TfStaticRelay(Node):
    def __init__(self):
        super().__init__('tf_static_relay')
        self.pub = self.create_publisher(TFMessage, '/tf', 100)
        self.sub = self.create_subscription(TFMessage, '/tf_static', self.callback, 100)
        self.get_logger().info('Relaying /tf_static -> /tf')

    def callback(self, msg):
        self.pub.publish(msg)


def main():
    rclpy.init()
    rclpy.spin(TfStaticRelay())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
