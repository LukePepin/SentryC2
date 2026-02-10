#!/bin/bash
# H3 Async Parallel Test Runner (Remote Supervisor on Pi4)
# ========================================================
# Test async parallel architecture vs baseline single-threaded

set -e

cd ~/sentry/SentryC2

# === CRITICAL: Match Pi4 Configuration ===
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$(pwd)/cyclonedds_local.xml
export H3_TEST_MODE=async  # Flag for data directory routing

# Source ROS2
source /opt/ros/humble/setup.bash

# Verify supervisor discovery
echo "🔍 Discovering async parallel supervisor..."
timeout 5 ros2 node list || {
    echo "❌ ERROR: No ROS2 nodes discovered!"
    echo "   Ensure Pi4 supervisor is running with async parallel mode."
    exit 1
}

echo "✓ Nodes discovered:"
ros2 node list

echo ""
echo "🔍 Verifying service..."
ros2 service list | grep authenticate || {
    echo "❌ ERROR: /supervisor/authenticate not found!"
    exit 1
}

echo "✓ Service found: /supervisor/authenticate"
echo ""

# === Execute H3 Async Parallel Tests ===
echo "🚀 STARTING H3 ASYNC PARALLEL TESTS"
echo "===================================="
echo "Testing async ThreadPool architecture (max_workers=4)"
echo ""

for N in 1 3 5 10 12 14 16 18 20 22 24; do
    echo ""
    echo "--- Test: n=$N nodes (async parallel) ---"
    python3 tests/livelock_sim.py --ros-args -p node_count:=$N
    
    if [ $? -ne 0 ]; then
        echo "❌ Test failed for n=$N"
        exit 1
    fi
    
    sleep 2  # Cooldown between tests
done

echo ""
echo "✅ ALL H3 ASYNC PARALLEL TESTS COMPLETE"
echo "📊 Results saved to: data/h3_async_parallel/h3_test_n*.csv"
echo ""
echo "COMPARISON ANALYSIS:"
echo "  Baseline (single-threaded): data/h3_test_n*.csv"
echo "  Async Parallel (ThreadPool): data/h3_async_parallel/h3_test_n*.csv"
echo ""
echo "Next: Compare failure rates @ n=20"
echo "  Baseline: 45.0% timeout rate"
echo "  Target: <5% timeout rate"
