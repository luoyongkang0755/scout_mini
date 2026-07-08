# Scout Mini 双激光雷达 Nav2 导航项目 — 进展报告

**日期**: 2026-07-08

---

## 一、我完成了什么？

### 1.1 项目初始化 & 目录结构搭建

创建了完整的 ROS 2 项目目录结构：

```
scout_mini_dual_lidar_nav2/
├── src/
│   ├── scout_mini_dual_lidar_gazebo/    # 主功能包
│   │   ├── config/   (nav2_params.yaml, navigate_w_recovery.xml)
│   │   ├── launch/   (scout_mini_gazebo.launch.py, slam.launch.py, nav2_launch.py)
│   │   ├── maps/     (my_map.yaml, my_map.pgm)
│   │   ├── src/      (自定义 Python 节点)
│   │   ├── urdf/     (scout_mini_gazebo.xacro)
│   │   ├── worlds/   (simple_test_world.world)
│   │   ├── rviz/     (display.rviz)
│   │   └── params/   (slam_toolbox_params.yaml)
│   └── external/
│       └── scout_ros2/   # 原厂 ROS 1 仓库（scout_base, scout_description, scout_msgs）
├── maps/
├── worlds/
├── docker/
├── reports/
└── log/
```

### 1.2 尝试从头重建项目

将导航功能拆分为多个独立的 launch 文件：

| Launch 文件 | 功能 | 路径 |
|---|---|---|
| `scout_mini_gazebo.launch.py` | Gazebo 仿真 + 机器人模型加载 | `launch/` |
| `slam.launch.py` | SLAM 建图（slam_toolbox） | `launch/` |
| `nav2_launch.py` | Nav2 导航栈启动 | `launch/` |

自定义 Python 节点：

| 文件 | 功能 |
|---|---|
| `scout_diff_drive.py` | 差速驱动控制器 |
| `scout_diff_drive_controller.py` | 控制器接口 |
| `laser_merger.py` | 双激光雷达融合 |
| `odom_to_tf.py` | 里程计 TF 发布 |
| `tf_to_odom.py` | TF → Odom 转换 |
| `tf_static_relay.py` | 静态 TF 中继 |
| `imu_odom_corrector.py` | IMU 里程计校正 |
| `auto_path_driver.py` | 自动路径行驶 |

### 1.3 成功项

- Gazebo 中成功显示了 Scout Mini 机器人模型
- RViz 中成功显示了机器人模型和传感器数据
- 使用 SLAM 成功建立了环境地图（`maps/my_map.yaml`）
- 使用原厂 UGV SDK 可以自由手动控制小车运行

---

## 二、遇到的问题

### 2.1 ROS 1 → ROS 2 版本不兼容（核心问题）

原厂 `scout_ros2` 仓库本质上是 ROS 1 风格的代码，存在严重的 ROS 2 适配问题：

- **STL 文件无法正确解析**: ROS 2 的 URDF/Gazebo 对 STL 网格的支持有限，机器人模型中的 STL 文件在 Gazebo 中渲染异常
- **Gazebo 插件不兼容**: 原厂使用的是 ROS 1 的 Gazebo 差速驱动插件，ROS 2 必须用 `gazebo_ros_diff_drive` 替代，但参数映射不完整
- **无法正常控制小车运动**: 尽管使用了原厂的差速驱动框架，但 ROS 2 下的控制指令（`/cmd_vel`）无法正确驱动 Gazebo 中的模型

### 2.2 Nav2 导航失败

**现象**:
- 可以手动控制小车运行，建图正常
- 加载地图后启用 Nav2 导航，小车不响应导航目标
- AMCL 节点虽然运行，但定位输出异常（`/amcl_pose` 话题无有效数据或为空）

**根因分析**:

1. **AMCL 扫描话题配置问题**
   - 配置文件 `nav2_params.yaml` 中 AMCL 订阅 `/merged/scan`（双激光雷达融合话题）
   - 若 `laser_merger.py` 未成功发布融合后的 `/merged/scan`，AMCL 收不到激光数据，无法进行粒子滤波定位

2. **Lifecycle Manager 未自动激活**
   - `nav2_lifecycle_manager` 包未安装在系统中
   - 运行 `ros2 pkg list | grep lifecycle` 未发现 `nav2_lifecycle_manager`
   - 导致所有 Nav2 节点（AMCL、planner_server、controller_server 等）虽然启动了，但停留在 `unconfigured` 状态
   - 需要手动逐个配置+激活生命周期节点

3. **行为树配置问题**
   - 自定义的 `navigate_w_recovery.xml` 可能存在节点引用或结构问题
   - `bt_loop_duration` 设置为 10（毫秒），可能过短导致行为树来不及执行

**证据**:
```bash
# AMCL 生命周期状态停留在 unconfigured
$ ros2 lifecycle list /amcl
- configure [1]
     Start: unconfigured
     Goal: configuring

# lifecycle_manager 节点不存在
$ ros2 lifecycle list /lifecycle_manager_navigation
# 无输出，节点未启动

# nav2_lifecycle_manager 包未安装
$ ros2 pkg prefix nav2_lifecycle_manager
Package nav2_lifecycle_manager NOT installed
```

4. **TF 变换缺失 — map 坐标系不存在**

由于 AMCL 未激活（停留在 unconfigured 状态），`map -> odom` 静态变换从未发布，导致 planner_server 无法将路径规划的起始/目标位姿变换到 `map` 坐标系，全局路径规划直接失败：

```
[planner_server-3] [ERROR] [transformPoseInTargetFrame]: Failed to transform from  to map
[planner_server-3] [WARN] [planner_server]: Could not transform the start or goal pose in the costmap frame
[planner_server-3] [WARN] [planner_server]: [compute_path_to_pose] [ActionServer] Aborting handle.
```

**现象链**：
1. Nav2 收到导航目标 → planner_server 尝试计算全局路径
2. planner_server 需要将起终点变换到 `map` 坐标系 → TF 查询失败（`map` 帧不存在）
3. `compute_path_to_pose` action 被 abort → 触发 recovery（清理 costmap、wait）
4. recovery 后重新尝试 → 再次失败 → 最终 `navigate_to_pose` goal failed
5. **根本原因**：AMCL 未激活 → 没有 `map -> odom` 发布 → 整个 TF 树缺少 `map` 帧

这实际上是问题 2（Lifecycle Manager 未激活）的直接后果，两者是同一根因。

---

## 三、我打算怎么解决？

### 3.1 短期方案

1. **安装缺失的包**: `sudo apt install ros-jazzy-nav2-lifecycle-manager`
2. **手动激活生命周期节点**: 在 lifecycle manager 修复前，先手动 transition 节点状态
3. **验证 `/merged/scan` 话题**: 确保激光融合节点正常工作
4. **替换为官方默认行为树**: 使用 `nav2_bt_navigator` 内置的默认 BT XML，避免自定义文件引入的未知问题

### 3.2 长期方案

- 考虑使用官方 Nav2 的 brings up launch 文件作为模板重新配置
- 逐步排查并解决 ROS 2 兼容性问题
- 如果 AMCL 定位问题持续，考虑切换为 slam_toolbox 的 localization 模式

---

## 四、相关文件清单

| 类别 | 文件路径 |
|---|---|
| Nav2 参数配置 | `src/scout_mini_dual_lidar_gazebo/config/nav2_params.yaml` |
| 自定义行为树 | `src/scout_mini_dual_lidar_gazebo/config/navigate_w_recovery.xml` |
| Nav2 启动 | `src/scout_mini_dual_lidar_gazebo/launch/nav2_launch.py` |
| Gazebo 启动 | `src/scout_mini_dual_lidar_gazebo/launch/scout_mini_gazebo.launch.py` |
| SLAM 启动 | `src/scout_mini_dual_lidar_gazebo/launch/slam.launch.py` |
| 机器人 URDF | `src/scout_mini_dual_lidar_gazebo/urdf/scout_mini_gazebo.xacro` |
| 地图文件 | `src/scout_mini_dual_lidar_gazebo/maps/my_map.yaml` |
| 原厂 ROS 包 | `src/external/scout_ros2/` |
| 任务日志 | `TASK_LOG.md` |

---

## 五、2026-07-08 下午进展：问题定位与修复

### 5.1 SLAM 丢帧问题

**现象**:
```
Message Filter dropping message: frame 'base_link' at time XXX for reason 'discarding message because the queue is full'
```
以及：
```
the timestamp on the message is earlier than all the data in the transform cache
```

**修复**:
- `slam_toolbox_params.yaml`: `transform_tolerance: 0.1 → 0.5`, 新增 `scan_queue_size: 30`
- `odom_frame: odom_corrected → odom`（因 `imu_odom_corrector` 自身订阅/发布同一 topic，不可靠）

### 5.2 建图碎点问题

**修复**: `slam_toolbox_params.yaml`
- `occ_thresh: 0.35 → 0.65`（提高占据阈值，过滤单次扫描噪声）
- `max_laser_range: 25 → 12`（缩短有效距离，减少远距离噪声）
- `minimum_time_interval: 0.3 → 0.5`、`minimum_travel_heading: 0.25 → 0.5`（减少关键帧密度）
- `map_update_interval: 1.0 → 2.0`

### 5.3 Nav2 导航不响应 Goal

**现象**:
1. 地图加载正常
2. `/merged/scan` 20Hz 正常工作
3. AMCL lifecycle 状态为 active
4. 但 `planner_server` 报错 `Failed to transform from  to map`（frame_id 为空）

**根因**:

| 问题 | 修复 |
|---|---|
| AMCL `initial_pose.yaw: 3.14` 与 Gazebo spawn yaw `1.57` 不匹配 | `nav2_params.yaml`: `yaw: 3.14 → 1.57` |
| RViz `display.rviz` Fixed Frame 设为了 `base_link` 而非 `map`，导致 Nav2 Goal 发布时 frame_id 为空 | `display.rviz`: `Fixed Frame: base_link → map` |
| `nav2_launch.py` 同时包含 map_server+AMCL 和 SLAM 模式，缺少条件分支 | 重写为双模式：`mode:=slam` / `mode:=localization` |
| Lifecycle manager `node_names` 中缺少 map_server 和 amcl | 已添加到列表中 |

### 5.4 放弃 scout_gazebo_sim 方案

创建了 `src/scout_gazebo_sim/` 包尝试从头构建，但发现：
- `scout_description` 本质是 ROS 1 风格，STL/gazebo 插件全部不兼容
- ROS 2 下 `libgazebo_ros_diff_drive.so` 不存在，必须用 Ignition `gz-sim-diff-drive-system`
- `package://` URI 在 Ignition 中不支持，需要 `file://$(find ...)` + 环境变量
- 最终放弃，继续使用 `scout_mini_dual_lidar_gazebo` 包

### 5.5 当前状态与待解决

- Gazebo 仿真 + 遥控：**正常**
- SLAM 建图：**正常**（已保存地图 `maps/my_map.pgm`）
- Nav2 导航规划（planner/controller）：**修复后待验证**
- 需在 RViz 中手动用 "2D Pose Estimate" 设置初始位姿后，AMCL 才会发布 `map -> odom` TF

---

## 六、Launch 文件速查

```bash
# 终端 1: Gazebo 仿真
ros2 launch scout_mini_dual_lidar_gazebo scout_mini_gazebo.launch.py

# 终端 2: SLAM 建图
ros2 launch scout_mini_dual_lidar_gazebo slam.launch.py

# 终端 2: Nav2 导航（建好地图后）
ros2 launch scout_mini_dual_lidar_gazebo nav2_launch.py mode:=localization

# 保存地图
ros2 run nav2_map_server map_saver_cli -f <path>/maps/my_map
```
