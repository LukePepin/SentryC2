# BOOT STORM EXECUTION PROTOCOL
**Chaos Engineering Test Plan for Hypothesis H3 Validation**

**Mission Objective:** Demonstrate exponential authentication latency scaling under node density (n) and identify Livelock threshold.

---

## 0. PRE-FLIGHT CHECKLIST (MANDATORY)

### Hardware Configuration
- [ ] **Device Under Test (DUT):** Raspberry Pi 4 (Supervisor Node)
    - OS: Ubuntu Server 22.04 (Headless)
    - IP Address: `192.168.1.100` (adjust to actual)
    - Thermal Monitor: Ensure `vcgencmd measure_temp` < 80°C before test
- [ ] **Load Generator (LG):** Laptop running Ubuntu 22.04/20.04
    - ROS2 Humble installed
    - Network: Same subnet as Pi4 (via Ethernet, NOT Wi-Fi for latency consistency)
- [ ] **Network Topology:**
    ```
    [Laptop] <--Gigabit Ethernet--> [Switch] <--Ethernet--> [Pi4]
    ```
    - Verify: `ping 192.168.1.100` shows <1ms latency

### Software Configuration
- [ ] **On Pi4 (Supervisor):**
    ```bash
    cd ~/SentryC2/ros2_ws
    source install/setup.bash
    ros2 run sentry_logic supervisor_node --ros-args -p auth_enabled:=true
    ```
    - Verify: `ros2 service list | grep authenticate` shows service active
    
- [ ] **On Laptop (Load Generator):**
    ```bash
    cd ~/SentryC2/tests
    chmod +x livelock_sim.py
    source ~/SentryC2/ros2_ws/install/setup.bash
    ```
    - Verify: `ros2 service list | grep authenticate` shows Pi4 service

---

## 1. BASELINE CALIBRATION (Test A: n=1)

**Purpose:** Establish single-node latency (L₀) as the reference metric.

### Execution
```bash
# On Laptop
python3 livelock_sim.py --ros-args \
    -p node_count:=1 \
    -p auth_timeout:=2.0 \
    -p supervisor_service:=/supervisor/authenticate
```

### Expected Outcome
- **L_avg ≈ 0.67ms + Network Overhead (ε)**
    - Typical: 1-3ms on local network
    - If L_avg > 10ms: NETWORK ISSUE (check switch/cables)

### Success Criteria
- [ ] `h3_test_n1_YYYYMMDD_HHMMSS.csv` generated
- [ ] Status = "SUCCESS" for all rows
- [ ] L_avg recorded as **L₀** (reference value)

**Formula:** `L₀ = L_avg(n=1)`

---

## 2. LINEAR VALIDATION (Test B: n=3, n=5)

**Purpose:** Confirm linear scaling regime before exponential onset.

### Test B1: n=3
```bash
python3 livelock_sim.py --ros-args -p node_count:=3
```

**Expected:** `L_avg ≈ 3 × L₀ ± 20%` (FIFO queue hypothesis)

### Test B2: n=5
```bash
python3 livelock_sim.py --ros-args -p node_count:=5
```

**Expected:** `L_avg ≈ 5 × L₀ ± 30%`

### Success Criteria
- [ ] Linearity holds: `L_avg(n=5) / L_avg(n=3) ≈ 1.67`
- [ ] No TIMEOUT events
- [ ] Pi4 CPU temp < 70°C (check: `ssh pi@192.168.1.100 'vcgencmd measure_temp'`)

---

## 3. THE STORM (Test C: n=10, n=20)

**Purpose:** Induce exponential scaling and observe Livelock entry conditions.

### Test C1: n=10 (Exponential Threshold)
```bash
python3 livelock_sim.py --ros-args \
    -p node_count:=10 \
    -p auth_timeout:=10.0
```

**Critical Observation Point:**
- Monitor Pi4 logs in real-time:
    ```bash
    ssh pi@192.168.1.100
    tail -f ~/.ros/log/latest/supervisor_node-*.log
    ```
- Watch for: Queue depth messages, timeout warnings

**Expected Behavior (H3 Prediction):**
- `L_max ≈ 10 × 0.67ms = 6.7ms` (if linear)
- **OR** `L_max > 20ms` (if exponential due to queue contention)

### Test C2: n=20 (Livelock Candidate)
```bash
python3 livelock_sim.py --ros-args \
    -p node_count:=20 \
    -p auth_timeout:=30.0
```

**Danger Zone:**
- If Trust Decay Interval (α) = 10ms (hypothetical):
    - Nodes 15-20 may timeout before authentication
    - Retry logic triggers → **Livelock Entry**

**Abort Criteria:**
- If Pi4 becomes unresponsive: `Ctrl+C` on both terminals
- If CPU temp > 80°C: Power cycle Pi4

---

## 4. SUCCESS CRITERIA (H3 VALIDATION LOGIC)

### Quantitative Thresholds

| Metric | Condition | Interpretation |
|--------|-----------|----------------|
| **Exponential Scaling** | `L_avg(n=10) > 10 × L₀` | H3 CONFIRMED: Non-linear queuing |
| **Timeout Rate** | `Timeouts > 0%` at n=10 | Queue saturation threshold reached |
| **Livelock Signature** | `Timeout Rate > 50%` at n=20 | System entered infinite retry loop |

### Formula for H3 Confirmation
```
Scaling Factor (SF) = L_avg(n=10) / (10 × L₀)

IF SF > 1.5:
    HYPOTHESIS H3 VALIDATED (Exponential regime)
ELSE:
    HYPOTHESIS H3 REJECTED (Linear regime)
```

### Expected Results (If H3 True)
```
n=1:  L_avg = 2.0ms  (Baseline)
n=3:  L_avg = 6.2ms  (Linear: 3×2.0 = 6.0ms ✓)
n=5:  L_avg = 11.5ms (Linear: 5×2.0 = 10.0ms, +15% overhead)
n=10: L_avg = 35ms   (Exponential: 10×2.0 = 20ms expected, 75% overshoot ✗)
n=20: L_avg = ???    (Livelock: Timeouts dominate)
```

---

## 5. POST-TEST ANALYSIS

### Data Collection
All CSV files should be in `/home/sentry/SentryC2/tests/`:
- `h3_test_n1_*.csv`
- `h3_test_n3_*.csv`
- `h3_test_n5_*.csv`
- `h3_test_n10_*.csv`
- `h3_test_n20_*.csv`

### Visualization (Generate Plot)
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load all test results
dfs = {
    'n=1': pd.read_csv('h3_test_n1_*.csv'),
    'n=3': pd.read_csv('h3_test_n3_*.csv'),
    # ... etc
}

# Plot: Latency vs Node Count
fig, ax = plt.subplots(figsize=(10, 6))
for label, df in dfs.items():
    ax.scatter(df['node_id'], df['latency_ms'], label=label, alpha=0.7)

ax.set_xlabel('Node ID (Request Order)')
ax.set_ylabel('Latency (ms)')
ax.set_title('H3 Validation: Authentication Latency Scaling')
ax.legend()
ax.grid(True, alpha=0.3)
plt.savefig('h3_validation_results.png', dpi=300)
```

### Generate Report
1. Calculate `L_avg`, `L_max`, `Timeout Rate` for each n
2. Compute Scaling Factor: `SF = L_avg(n=10) / (10 × L₀)`
3. Create table in `H3_VALIDATION_REPORT.md`:

```markdown
| n  | L_avg (ms) | L_max (ms) | Timeout % | SF   | Status |
|----|------------|------------|-----------|------|--------|
| 1  | 2.0        | 2.1        | 0%        | 1.0  | ✓      |
| 3  | 6.2        | 6.8        | 0%        | 1.03 | ✓      |
| 5  | 11.5       | 13.2       | 0%        | 1.15 | ✓      |
| 10 | 35.0       | 48.7       | 10%       | 1.75 | ✗ H3   |
| 20 | TIMEOUT    | TIMEOUT    | 85%       | ∞    | ✗ LOCK |
```

---

## 6. FAILURE MODE HANDLING

### If Pi4 Crashes (Kernel Panic / OOM)
1. Power cycle Pi4
2. Check `dmesg | tail -50` for out-of-memory errors
3. **Mitigation:** Reduce `node_count` or add swap space

### If Network Saturates (Packet Loss)
1. Verify with: `iperf3 -c 192.168.1.100`
2. Expected throughput: >900 Mbps (Gigabit Ethernet)
3. If <100 Mbps: Check cable/switch

### If Authentication Service Unavailable
```bash
# On Pi4, restart supervisor node
killall supervisor_node
ros2 run sentry_logic supervisor_node
```

---

## 7. SAFETY CONSTRAINTS (MISSION-FIRST)

### Thermal Protection
- Monitor Pi4 temp every 30s during test:
    ```bash
    watch -n 30 'ssh pi@192.168.1.100 vcgencmd measure_temp'
    ```
- **Abort if temp > 80°C** (thermal throttling triggers)

### Time Budget
- Each test run: <5 minutes
- Total protocol: 30-45 minutes
- If any test exceeds 10 minutes: **ABORT** (deadlock scenario)

### Data Integrity
- Backup CSV files immediately after each test:
    ```bash
    cp h3_test_*.csv ~/SentryC2/tests/results_$(date +%Y%m%d)/
    ```

---

## 8. APPENDIX: TROUBLESHOOTING

### Symptom: "Service Unavailable"
**Cause:** ROS2 discovery timeout (DDS multicast issue)
**Fix:**
```bash
# On both Laptop and Pi4
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

### Symptom: L_avg(n=1) > 100ms
**Cause:** Network latency or Pi4 CPU throttling
**Fix:**
1. Check CPU governor: `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`
   - Should be `performance`, not `powersave`
2. Reboot Pi4 to clear thermal throttling

### Symptom: No CSV file generated
**Cause:** Script crashed before `save_telemetry()`
**Fix:** Check logs: `~/.ros/log/latest/livelock_simulator-*.log`

---

## 9. EXPECTED DELIVERABLES

1. [ ] 5 CSV files (n=1, 3, 5, 10, 20)
2. [ ] Validation plot (`h3_validation_results.png`)
3. [ ] Report with Scaling Factor calculation
4. [ ] Pi4 thermal log (if temperatures > 70°C observed)

**Final Validation Statement:**
```
IF SF > 1.5 AND Timeout_Rate(n=20) > 50%:
    CONCLUSION: "Hypothesis H3 CONFIRMED. Authentication latency exhibits 
                 exponential scaling under node density. Livelock threshold 
                 occurs at n≈15 nodes. Recommend implementing parallel ZKP 
                 verification queue or Trust Decay mitigation."
ELSE:
    CONCLUSION: "Hypothesis H3 REJECTED. System maintains linear scaling. 
                 Current architecture sufficient for tested node density."
```

---

**AUTHORIZED FOR EXECUTION:** Senior Chaos Engineer
**RISK LEVEL:** Medium (Pi4 thermal stress, network saturation)
**ABORT AUTHORITY:** Terminate on thermal violation or >10min deadlock
