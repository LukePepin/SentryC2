#!/bin/bash
set -e

cd ~/sentry/SentryC2

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$(pwd)/cyclonedds_local.xml
export H3_TEST_MODE=multithreaded

source /opt/ros/humble/setup.bash

echo "🚀 H3 MULTITHREADED EXECUTOR TESTS"
echo "===================================="

for N in 1 3 5 10 12 14 16 18 20 22 24; do
    echo "--- Test: n=$N nodes (MultiThreadedExecutor) ---"
    python3 tests/livelock_sim.py --ros-args -p node_count:=$N
    sleep 2
done

echo ""
echo "✅ ALL TESTS COMPLETE"
echo "📊 Results: data/h3_multithreaded/h3_test_n*.csv"
