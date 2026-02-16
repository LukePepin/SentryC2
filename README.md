# SentryC2: Edge-First Resiliency Framework
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-green)](https://docs.ros.org/en/humble/)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)]()
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue)](https://github.com/lpep64/SentryC2/pkgs/container/sentryc2)

## 1. Problem Statement
Current Industry 4.0 architectures rely on centralized Identity Providers (IdP). When backhaul connectivity fails, authorization leases expire, triggering a "Kill Switch" that halts production regardless of local hardware status.

**SentryC2** replaces this with an **Edge-First** mesh topology, utilizing local Zero-Knowledge Proofs (ZKP) to ensure sub-500ms recovery during network blackouts.

## 2. Architecture
![Kill Switch vs Edge Mesh](docs/architecture_diagram.png)

*Figure 1: Comparison of Cloud-First Fragility vs. SentryC2 Edge Mesh*

## 3. Quick Start (Docker)
This repository is containerized to ensure full reproducibility across Thinkmate (Dev) and Jetson Orin (Edge) hardware.

### Prerequisites
- Docker Engine (Linux)
- Unity Hub 2022.3+ (Simulation)

### Installation

#### Option 1: Pull from GitHub Container Registry (Recommended)
```bash
# Pull the pre-built image
docker pull ghcr.io/lpep64/sentryc2:alpha

# Run with docker-compose
docker-compose up -d
```

#### Option 2: Build Locally
```bash
# 1. Clone the repository
git clone https://github.com/lpep64/SentryC2.git
cd SentryC2

# 2. Build the Edge-First OS
docker build -t sentry-c2:alpha .

# 3. Run Development Container
docker-compose up -d

# 4. Attach to container
docker exec -it sentry-c2-dev /bin/bash
```

### VS Code Integration
The Docker extension in VS Code will automatically detect your containers. If you don't see them:

1. **Fix Docker Permissions** (one-time setup):
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker  # or log out and back in
   ```

2. **Reload VS Code** to refresh the Docker extension

3. **Right-click container** in Docker sidebar to:
   - Attach shell
   - View logs
   - Stop/Start container


## 4. Unity-ROS2 Integration

### Running the Complete System

**Terminal 1 (ROS-TCP Bridge):**
```bash
cd /workspace/ros2_ws
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10005
```

**Terminal 2 (Action Server):**
```bash
cd /workspace/ros2_ws
source install/setup.bash
ros2 run sentry_logic cyclic_server
```

### Connecting to Physical Niryo Ned2 Robot

**Prerequisites:**
- Niryo Ned2 robot on network (default runs ROS1 Noetic)
- Robot IP address (e.g., 192.168.0.244)
- NiryoStudio **disconnected** (only one connection allowed at a time)

> **Note**: Configuration currently static for Lab Bench A. Dynamic IP discovery scheduled for Week 6.

**Terminal 1 (ROS-TCP Bridge for Unity):**
```bash
cd /workspace/ros2_ws
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10005
```

**Terminal 2 (Niryo Bridge - Bidirectional):**
```bash
cd /workspace/ros2_ws
source install/setup.bash
ros2 run sentry_logic niryo_tcp_bridge
```

This bridge:
- **Publishes** real-time joint states to `/joint_states` topic (10 Hz)
- **Subscribes** to `/niryo_robot_follow_joint_trajectory_controller/follow_joint_trajectory` for commands
- Translates between ROS1 (robot) and ROS2 (workspace) bidirectionally

**Verify Connection:**
```bash
ros2 topic list                    # Should show /joint_states
ros2 topic echo /joint_states      # View live robot positions
```

**Test Robot Control:**
```bash
# In a third terminal, send a test trajectory
cd /workspace/ros2_ws && source install/setup.bash
ros2 run sentry_logic test_arm_trajectory
```

This will move the robot through a comprehensive 62-second test sequence:
1. Home position
2. Base rotation + shoulder lift
3. Wrist pitch test (joint 5)
4. Wrist roll (joint 4) + wrist rotation (joint 6)
5. Sentry scan position - high alert
6. Full base rotation with wrist movement
7. Extended reach position
8. Compact position
9. Return home

All 6 joints are tested including the wrist and end effector orientation.

**Change Robot IP (if needed):**
```bash
ros2 run sentry_logic niryo_tcp_bridge --ros-args -p robot_ip:=<YOUR_IP>
```

**Unity Configuration:**
1. **ROSConnection Settings** (GameObject with ROSConnection component):
   - ROS IP: `127.0.0.1`
   - ROS Port: `10005`
   - Protocol: `ROS2`
   - Connect on Startup: ✅ **Enabled**

2. **Robot Components** (niryo_one GameObject):
   - `PhysicsController` - Configures ArticulationBody physics (stiffness: 10000, damping: 1000, forceLimit: 1000)
   - `JointStateSubscriber` - Subscribes to `/joint_states` and applies positions to joints
   - ❌ Remove `Controller` component (causes Input API conflicts)

3. **Press Play** - Robot cycles between HOME and TARGET poses every 2 seconds

### URDF Importer Fix (Linux)
```bash
sudo ln -sf /lib/x86_64-linux-gnu/libdl.so.2 /usr/lib/libdl.so
```

### Verification
- Docker: `[INFO] [UnityEndpoint]: RegisterSubscriber(/joint_states...)`
- Unity: Robot moves smoothly, base rotates ~90°, arm lifts slightly

## 5. Roadmap (Spring 2026)
*   **Jan 2026:** ✅ Environment Setup & Digital Twin Alpha ✅ ROS2 Action Server Integration
*   **Feb 2026:** Hardware Interface (Raspberry Pi / Arduino BLE) & Kill Switch Implementation
*   **Mar 2026:** Zero-Knowledge Proof Auth & Chaos Engineering (Packet Loss / ARP Poisoning)
*   **Apr 2026:** Final Integration & Thesis Defense

## License
Copyright 2026 Luke Pepin.
Licensed under the Apache License, Version 2.0.

