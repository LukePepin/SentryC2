#!/bin/bash
# SentryC2 H3 Boot Storm Test Execution Script
# ============================================
# Automates complete test sequence from Pi4 setup to test execution

set -e  # Exit on error

echo "========================================="
echo "SentryC2 H3 BOOT STORM TEST SEQUENCE"
echo "========================================="
echo ""

# -----------------------------------------
# STEP 1: Verify ROS2 Installation on Pi4
# -----------------------------------------
echo "[STEP 1/6] Verifying ROS2 installation on Pi4..."
ssh sentry-supervisor@192.168.0.105 << 'EOF'
if [ -f /opt/ros/humble/setup.bash ]; then
    echo "✓ ROS2 Humble detected"
    source /opt/ros/humble/setup.bash
    ros2 --version
else
    echo "✗ ROS2 Humble NOT installed. Install with:"
    echo "  sudo apt update"
    echo "  sudo apt install -y ros-humble-ros-base python3-colcon-common-extensions"
    exit 1
fi
EOF

echo ""

# -----------------------------------------
# STEP 2: Build sentry_logic on Pi4
# -----------------------------------------
echo "[STEP 2/6] Building sentry_logic package on Pi4..."
ssh sentry-supervisor@192.168.0.105 << 'EOF'
cd ~/SentryC2/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select sentry_logic --symlink-install
echo "✓ Build complete"
EOF

echo ""

# -----------------------------------------
# STEP 3: Start Supervisor Node on Pi4
# -----------------------------------------
echo "[STEP 3/6] Starting Supervisor Node on Pi4 (background)..."
ssh sentry-supervisor@192.168.0.105 << 'EOF'
cd ~/SentryC2/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

# Kill any existing supervisor processes
pkill -f supervisor_node || true

# Start supervisor in background with logging
nohup ros2 run sentry_logic supervisor_node --ros-args -p auth_enabled:=true > ~/supervisor.log 2>&1 &
sleep 3

# Verify process started
if pgrep -f supervisor_node > /dev/null; then
    echo "✓ Supervisor node running (PID: $(pgrep -f supervisor_node))"
else
    echo "✗ Supervisor node failed to start. Check ~/supervisor.log"
    exit 1
fi
EOF

echo ""

# -----------------------------------------
# STEP 4: Verify ROS2 Discovery (Laptop)
# -----------------------------------------
echo "[STEP 4/6] Verifying ROS2 discovery from laptop..."
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=0

echo "Waiting 5s for discovery..."
sleep 5

echo "Active ROS2 nodes:"
ros2 node list || echo "⚠ No nodes discovered"

echo ""
echo "Available services:"
ros2 service list | grep -i auth || echo "⚠ No authentication service found"

echo ""

# -----------------------------------------
# STEP 5: Execute Baseline Test (n=1)
# -----------------------------------------
echo "[STEP 5/6] Running baseline test (n=1)..."
cd /home/sentry/sentry/SentryC2
source /opt/ros/humble/setup.bash

python3 tests/livelock_sim.py --ros-args -p node_count:=1 -p burst_interval:=0.1 -p auth_timeout:=5.0

echo ""

# -----------------------------------------
# STEP 6: Manual Boot Storm Execution
# -----------------------------------------
echo "[STEP 6/6] READY FOR BOOT STORM"
echo "========================================="
echo ""
echo "To execute full test sequence, run:"
echo ""
echo "  # Test A: Baseline (n=1) - COMPLETED"
echo "  python3 tests/livelock_sim.py --ros-args -p node_count:=3"
echo "  python3 tests/livelock_sim.py --ros-args -p node_count:=5"
echo ""
echo "  # Test C: Boot Storm"
echo "  python3 tests/livelock_sim.py --ros-args -p node_count:=10"
echo "  python3 tests/livelock_sim.py --ros-args -p node_count:=20"
echo ""
echo "Results will be saved to: data/h3_test_n*_YYYYMMDD_HHMMSS.csv"
echo ""
echo "⚠ REMINDER: Email all CSV files to PC data repository after test completion"
echo ""
