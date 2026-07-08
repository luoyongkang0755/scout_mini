#!/bin/bash
set -e

cd "$(dirname "$0")/.."
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_NAME="scout_mini_nav2:latest"

xhost +local:docker 2>/dev/null || true

echo "Running container with GUI support.."
docker run -it --rm \
    --name scout_gazebo_mini \
    --net=host \
    --env="DISPLAY=$DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    --volume="/tmp/.x11-unix:/tmp/.x11-unix:rw" \
    --volume="$HOME/.Xauthority:/root/.Xauthority:rw" \
    --volume "$REPO_ROOT"/src:/ws/src \
    --env="XAUTHORITY=/root/.Xauthority" \
    --privileged \
    --device=/dev/dri:/dev/dri \
    "$IMAGE_NAME"

xhost -local:docker 2>/dev/null || true
