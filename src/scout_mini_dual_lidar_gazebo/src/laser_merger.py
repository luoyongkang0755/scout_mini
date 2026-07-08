#!/usr/bin/env python3
"""Merge /front/scan and /rear/scan into base_link frame via cached single TF lookup."""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener


class LaserMerger(Node):
    def __init__(self):
        super().__init__('laser_merger')

        self.front_scan = None
        self.rear_scan = None

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Cache last valid transforms as (dx, dy, cos_yaw, sin_yaw)
        self.front_tf = None
        self.rear_tf = None

        self.front_sub = self.create_subscription(
            LaserScan, '/front/scan', self.front_callback, 10)
        self.rear_sub = self.create_subscription(
            LaserScan, '/rear/scan', self.rear_callback, 10)

        self.merged_pub = self.create_publisher(LaserScan, '/merged/scan', 10)
        self.get_logger().info('Merging /front/scan + /rear/scan -> /merged/scan (TF-corrected)')

    def get_tf(self, from_frame, stamp):
        """One TF lookup for the whole frame. Returns (dx, dy, cos, sin) or None."""
        try:
            t = self.tf_buffer.lookup_transform(
                'base_link', from_frame, stamp,
                timeout=rclpy.duration.Duration(seconds=0.1))
            dx = t.transform.translation.x
            dy = t.transform.translation.y
            # Extract yaw from quaternion
            q = t.transform.rotation
            sy = 2.0 * (q.w * q.z + q.x * q.y)
            cy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            yaw = math.atan2(sy, cy)
            return (dx, dy, math.cos(yaw), math.sin(yaw))
        except Exception as e:
            self.get_logger().debug(f'TF lookup {from_frame}->base_link: {e}')
            return None

    def front_callback(self, msg):
        self.front_scan = msg
        self.try_publish()

    def rear_callback(self, msg):
        self.rear_scan = msg
        self.try_publish()

    def try_publish(self):
        if self.front_scan is None or self.rear_scan is None:
            return

        fs = self.front_scan
        rs = self.rear_scan

        # One TF lookup per frame per scan pair (cached)
        front_tf = self.get_tf(fs.header.frame_id, fs.header.stamp)
        if front_tf is not None:
            self.front_tf = front_tf
        rear_tf = self.get_tf(rs.header.frame_id, rs.header.stamp)
        if rear_tf is not None:
            self.rear_tf = rear_tf

        merged = LaserScan()
        merged.header.stamp = fs.header.stamp
        merged.header.frame_id = 'base_link'
        merged.angle_min = -math.pi
        merged.angle_max = math.pi
        merged.angle_increment = fs.angle_increment
        merged.range_min = min(fs.range_min, rs.range_min)
        merged.range_max = max(fs.range_max, rs.range_max)
        merged.time_increment = fs.time_increment
        merged.scan_time = fs.scan_time

        n = min(len(fs.ranges), len(rs.ranges))
        merged.ranges = []

        for i in range(n):
            angle = fs.angle_min + i * fs.angle_increment
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            fr = self._correct_range(fs.ranges[i], cos_a, sin_a, self.front_tf)
            rr = self._correct_range(rs.ranges[i], cos_a, sin_a, self.rear_tf)

            if math.isfinite(fr) and math.isfinite(rr):
                merged.ranges.append(min(fr, rr))
            elif math.isfinite(fr):
                merged.ranges.append(fr)
            elif math.isfinite(rr):
                merged.ranges.append(rr)
            else:
                merged.ranges.append(float('inf'))

        self.merged_pub.publish(merged)

    @staticmethod
    def _correct_range(range_val, cos_a, sin_a, tf):
        """Correct a single range by applying lidar-to-base_link offset."""
        if not math.isfinite(range_val) or range_val <= 0.01 or tf is None:
            return range_val

        dx, dy, cos_yaw, sin_yaw = tf
        # Point in lidar frame
        lx = range_val * cos_a
        ly = range_val * sin_a
        # Rotate by lidar frame's yaw, then translate to base_link
        bx = cos_yaw * lx - sin_yaw * ly + dx
        by = sin_yaw * lx + cos_yaw * ly + dy
        return math.sqrt(bx * bx + by * by)


def main():
    rclpy.init()
    rclpy.spin(LaserMerger())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
