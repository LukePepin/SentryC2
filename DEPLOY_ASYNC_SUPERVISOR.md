# DEPLOYMENT INSTRUCTIONS: Async Parallel Supervisor

## MISSION: Deploy refactored supervisor_node.py to Raspberry Pi 4

### Step 1: Copy Updated Code to Pi4
```bash
# From your local machine
scp ros2_ws/src/sentry_logic/sentry_logic/supervisor_node.py \
    sentry-supervisor@192.168.0.105:~/SentryC2/ros2_ws/src/sentry_logic/sentry_logic/
```

### Step 2: SSH into Pi4 and Rebuild
```bash
ssh sentry-supervisor@192.168.0.105
cd ~/SentryC2/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select sentry_logic --symlink-install
```

### Step 3: Configure Environment and Run Async Supervisor
```bash
source install/setup.bash
export CYCLONEDDS_URI=file:///tmp/cyclonedds_pi4.xml
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0

# Launch async parallel supervisor (4 worker threads)
ros2 run sentry_logic supervisor_node \
    --ros-args \
    -p auth_enabled:=true \
    -p max_workers:=4 \
    -p zkp_delay_ms:=0.67
```

**Expected Output:**
```
[INFO] [supervisor_node]: 🔐 Supervisor Node ONLINE (ASYNC PARALLEL)
   - Service: /supervisor/authenticate
   - Auth Enabled: True
   - ZKP Delay: 0.67ms
   - Architecture: THREAD POOL (max_workers=4)
   - Hardware: Raspberry Pi 4 (4-core Cortex-A72)
```

### Step 4: Run H3 Async Parallel Tests (Local Machine)
```bash
cd ~/sentry/SentryC2
./run_h3_async_test_remote.sh
```

### Step 5: Analyze Results
```bash
# Compare failure rates
echo "Baseline @ n=20: 45.0% timeout"
grep -r "Timeout Rate" data/h3_test_n20_*.csv | tail -1

echo "Async Parallel @ n=20:"
grep -r "Timeout Rate" data/h3_async_parallel/h3_test_n20_*.csv | tail -1
```

## ARCHITECTURAL VALIDATION CRITERIA

| Metric | Baseline (Single-Thread) | Target (Async Parallel) |
|--------|-------------------------|------------------------|
| Failure @ n=12 | 8.3% | <3% |
| Failure @ n=20 | 45.0% | <5% |
| Failure @ n=24 | 54.2% | <10% |

**SUCCESS CRITERIA:** Async architecture must reduce n=20 failure rate from 45% → <5%

## TROUBLESHOOTING

### Issue: "No executable found"
- Ensure `colcon build` completed successfully
- Check `install/lib/sentry_logic/supervisor_node` exists

### Issue: Import errors (concurrent.futures)
- Python 3.10+ includes concurrent.futures in stdlib
- Verify: `python3 -c "import concurrent.futures; print('OK')"`

### Issue: ThreadPool not utilizing cores
- Check CPU affinity: `taskset -c -p $(pgrep supervisor_node)`
- Pi4 thermal throttling: Monitor `vcgencmd measure_temp` (should be <80°C)
