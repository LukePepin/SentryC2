#!/bin/bash
# H3 Livelock Test Runner (Remote Supervisor on Pi4)
# =================================================
# Configure DDS for cross-machine ROS2 discovery

set -e

cd ~/sentry/SentryC2

# === CRITICAL: Match Pi4 Configuration ===
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$(pwd)/cyclonedds_local.xml

# Source ROS2
source /opt/ros/humble/setup.bash

# Verify supervisor discovery
echo "🔍 Discovering nodes..."
timeout 5 ros2 node list || {
    echo "❌ ERROR: No ROS2 nodes discovered!"
    echo "   Ensure Pi4 supervisor is running and network is configured."
    echo "   Pi4 should be on same subnet with multicast enabled."
    exit 1
}

echo "✓ Nodes discovered:"
ros2 node list

echo ""
echo "🔍 Discovering services..."
ros2 service list | grep authenticate || {
    echo "❌ ERROR: /supervisor/authenticate not found!"
    echo "   Check Pi4 supervisor node status."
    exit 1
}

echo "✓ Service found: /supervisor/authenticate"
echo ""

# === Execute H3 Tests ===
echo "🚀 STARTING H3 LIVELOCK TESTS"
echo "=============================="

for N in 1 3 5 10 12 14 16 18 20 22 24; do
    echo ""
    echo "--- Test: n=$N nodes ---"
    python3 tests/livelock_sim.py --ros-args -p node_count:=$N
    
    if [ $? -ne 0 ]; then
        echo "❌ Test failed for n=$N"
        exit 1
    fi
    
    sleep 2  # Cooldown between tests
done

echo ""
echo "✅ ALL H3 TESTS COMPLETE"
echo "📊 Results saved to: data/h3_test_n*.csv"
echo ""
echo "Next step: python3 generate_figure_4_3_h3_livelock.py"
