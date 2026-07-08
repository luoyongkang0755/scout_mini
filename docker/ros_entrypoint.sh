#!/bin/bash
set -e
# Source ROS if available
if [ -f "/opt/ros/humble/setup.bash" ]; then
  source "/opt/ros/humble/setup.bash"
fi
# Source workspace install if available
if [ -f "/ws/install/setup.bash" ]; then
  source "/ws/install/setup.bash"
fi
# Execute passed command
exec "$@"
