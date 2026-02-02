# SVP: Software Verification Plan
## SentryC2 Edge-First Robotics Framework

**Document Classification:** Internal - Federal Disclosure Candidate  
**Version:** 0.1-alpha  
**Date:** 2026-02-02  
**Prepared by:** Verification Lead  
**Standard:** DO-178C Level A  

---

## Executive Summary

This Software Verification Plan (SVP) establishes the testing strategy, coverage requirements, and verification methods to validate that SentryC2 meets all safety-critical and functional requirements. 

**Verification Approach:**
1. **Unit Testing** (Isolation): Individual components (ZKP prover, verifier, ROS nodes)
2. **Integration Testing** (Composition): ROS middleware, message passing, state synchronization
3. **System Testing** (End-to-End): Full robot control stack with physical Niryo Ned2
4. **Safety Testing** (Failure Modes): Network isolation, crypto failures, thermal stress
5. **Performance Testing** (Metrics): Latency, throughput, resource utilization

**Compliance:** All test results are traceable to requirements via [tests/traceability_matrix.csv](../tests/traceability_matrix.csv)

---

## 1. Test Strategy Overview

### 1.1 V-Model Alignment (DO-178C)

```
Requirements (REQUIREMENTS.md)
    ↓
    └─→ Unit Test (TC-001 through TC-010)
        ├─→ Code Review (2+ approvals)
        ├─→ Static Analysis (pylint, mypy)
        └─→ Integration Test
            ├─→ ROS2 composition tests
            ├─→ Hardware-in-the-loop (HIL)
            └─→ System Test
                ├─→ Physical Niryo robot
                ├─→ Network isolation
                └─→ Acceptance
                    └─→ Thesis advisor sign-off
```

### 1.2 Coverage Goals

| Coverage Type | Goal | Method |
|---------------|------|--------|
| **Code Coverage** | ≥85% | pytest + coverage.py |
| **Branch Coverage** | ≥75% | conditional path execution |
| **Safety-Critical Path** | 100% | manual review + test |
| **Requirement Coverage** | 100% | traceability matrix |
| **Test Case Execution** | 100% | per release cycle |

---

## 2. Unit Test Specification

### 2.1 Python ROS2 Nodes (pytest)

#### TC-005A: ROS2 Topic Publication/Subscription

**Test File:** `tests/test_ros2_integration.py`

```python
import pytest
from sentry_logic.joints_publisher import JointsPublisher

class TestJointsPublisher:
    @pytest.fixture
    def publisher(self):
        return JointsPublisher()
    
    def test_joint_state_message_format(self, publisher):
        """Verify JointState message has all required fields [REQ-005]"""
        msg = publisher.get_latest_state()
        assert hasattr(msg, 'header')
        assert hasattr(msg, 'name')
        assert hasattr(msg, 'position')
        assert hasattr(msg, 'velocity')
        assert hasattr(msg, 'effort')
        
    def test_publication_rate(self, publisher):
        """Verify /joint_states published at 10 Hz ±2% [REQ-005, REQ-006]"""
        timestamps = []
        for _ in range(100):
            publisher.timer_callback()
            timestamps.append(time.time())
        
        periods = np.diff(timestamps)
        mean_freq = 1 / np.mean(periods)
        assert 9.8 <= mean_freq <= 10.2  # ±2% tolerance
```

**Acceptance Criteria:**
- ✓ All fields present in JointState message
- ✓ Publication frequency: 10.0 ± 0.2 Hz
- ✓ No message drops over 1000+ messages

---

#### TC-003A: ZKP Proof Generation (Schnorr Protocol)

**Test File:** `tests/test_zkp_prover.py`

```python
import pytest
from sentry_logic.zkp_auth_prover import SchnorrProver

class TestSchnorrProver:
    @pytest.fixture
    def prover(self):
        return SchnorrProver(private_key=PROVER_PRIVATE_KEY)
    
    def test_proof_structure(self, prover):
        """Verify proof contains R (commitment) and S (response) [REQ-003]"""
        proof = prover.generate_proof(challenge=CHALLENGE_HASH)
        assert len(proof.commitment) == 32  # R component
        assert len(proof.response) == 32     # S component
        
    def test_proof_determinism(self, prover):
        """Verify same challenge produces same proof (Schnorr is deterministic) [REQ-003]"""
        proof1 = prover.generate_proof(challenge=CHALLENGE_HASH, nonce=NONCE)
        proof2 = prover.generate_proof(challenge=CHALLENGE_HASH, nonce=NONCE)
        assert proof1.bytes() == proof2.bytes()
        
    def test_proof_latency(self, prover):
        """Verify proof generation completes < 50ms [REQ-003]"""
        import time
        start = time.perf_counter()
        prover.generate_proof(challenge=CHALLENGE_HASH)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Proof generation took {elapsed_ms}ms"
```

**Acceptance Criteria:**
- ✓ Proof structure valid (R || S || challenge_hash)
- ✓ Latency < 50ms on Pi4
- ✓ Deterministic for same inputs

---

#### TC-003B: ZKP Proof Verification (Oracle Resistance)

**Test File:** `tests/test_zkp_verifier.py`

```python
import pytest
from sentry_logic.zkp_auth_verifier import SchnorrVerifier

class TestSchnorrVerifier:
    @pytest.fixture
    def verifier(self):
        return SchnorrVerifier(public_key=PROVER_PUBLIC_KEY)
    
    def test_valid_proof_acceptance(self, verifier):
        """Verify valid proofs are accepted [REQ-003]"""
        proof = VALID_PROOF_VECTOR
        result = verifier.verify(proof)
        assert result == True
        
    def test_forged_proof_rejection(self, verifier):
        """Cryptographic oracle: attempt to forge proofs without private key [SAF-001]"""
        # Try 10,000 random proof attempts
        forged_count = 0
        for attempt in range(10000):
            forged_proof = secrets.token_bytes(64)  # Random R || S
            if verifier.verify(forged_proof):
                forged_count += 1
        
        assert forged_count == 0, f"Accepted {forged_count} forged proofs!"
        
    def test_proof_replay_attack(self, verifier):
        """Verify same proof rejected on second use (nonce binding) [SAF-001]"""
        proof_with_nonce1 = PROOF_WITH_NONCE_1
        proof_with_nonce2 = PROOF_WITH_NONCE_2  # Different nonce
        
        assert verifier.verify(proof_with_nonce1) == True
        assert verifier.verify(proof_with_nonce2) == True
        # Replay with same nonce should fail
        assert verifier.verify(proof_with_nonce1) == False
        
    def test_verification_latency(self, verifier):
        """Verify proof verification completes < 20ms [REQ-002]"""
        import time
        start = time.perf_counter()
        verifier.verify(VALID_PROOF_VECTOR)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 20, f"Verification took {elapsed_ms}ms"
```

**Acceptance Criteria:**
- ✓ Valid proofs accepted
- ✓ 0/10,000 forged proofs accepted (oracle resistance)
- ✓ Replay attacks blocked via nonce binding
- ✓ Verification latency < 20ms

---

### 2.2 Arduino Unit Tests (Arduino IDE / PlatformIO)

#### TC-003C: Nano33 BLE ZKP Prover

**Test File:** `arduino/nano33_zkp_prover/test_zkp.cpp`

```cpp
#include <unity.h>
#include "zkp_prover.h"

void test_proof_generation_completes() {
    // Verify ZKP generation on Nano33 BLE completes without crash
    uint8_t proof[64];
    uint32_t start_ms = millis();
    int result = schnorr_generate_proof(private_key, challenge, proof);
    uint32_t elapsed_ms = millis() - start_ms;
    
    TEST_ASSERT_EQUAL(0, result);  // Success
    TEST_ASSERT_LESS_THAN(100, elapsed_ms);  // <100ms on 64 MHz Cortex-M4
}

void test_proof_size_fixed() {
    // Schnorr proof must be exactly 64 bytes (R=32 || S=32)
    uint8_t proof[64];
    schnorr_generate_proof(private_key, challenge, proof);
    
    TEST_ASSERT_EQUAL(64, sizeof(proof));
}

void test_sram_usage_bounded() {
    // Ensure proof generation does not exhaust 256KB SRAM
    // Use __builtin_frame_address to track stack depth
    extern char __bss_end;
    char* heap_start = (char*)malloc(1);
    int heap_usage = (int)heap_start - (int)&__bss_end;
    
    TEST_ASSERT_LESS_THAN(50000, heap_usage);  // <50KB heap
    free(heap_start);
}
```

**Test Execution:**
```bash
cd arduino/nano33_zkp_prover
pio test  # PlatformIO unit test runner
```

**Acceptance Criteria:**
- ✓ Proof generation completes without crash
- ✓ SRAM usage < 50KB (leaves >200KB for main loop)
- ✓ Proof size = 64 bytes

---

## 3. Integration Test Specification

### 3.1 ROS2 Node Composition Tests

#### TC-005B: Multi-Node Message Passing

**Test File:** `tests/test_ros2_composition.py`

```python
import pytest
from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from rclpy.node import Node

class TestROS2Composition:
    def test_joint_publisher_subscriber_chain(self):
        """Verify joint states flow from publisher → subscriber [REQ-005, REQ-006]"""
        # 1. Start publisher node
        # 2. Start subscriber node
        # 3. Publish 10 messages
        # 4. Verify subscriber received all messages
        # 5. Assert latency < 100ms (DDS QoS)
        
        messages_received = []
        
        def subscriber_callback(msg):
            messages_received.append(msg)
        
        # Create publisher
        pub_node = Node('test_publisher')
        pub = pub_node.create_publisher(JointState, '/joint_states', 10)
        
        # Create subscriber
        sub_node = Node('test_subscriber')
        sub = sub_node.create_subscription(
            JointState, '/joint_states', subscriber_callback, 10
        )
        
        # Publish messages
        for i in range(10):
            pub.publish(JOINT_STATE_MSG)
            rclpy.spin_once(pub_node, timeout_sec=0.1)
            rclpy.spin_once(sub_node, timeout_sec=0.1)
        
        assert len(messages_received) == 10
```

**Acceptance Criteria:**
- ✓ All published messages received by subscriber
- ✓ Message latency < 100ms (p99)
- ✓ No message corruption

---

### 3.2 Hardware-in-the-Loop (HIL) Tests

#### TC-007B: Physical Niryo Ned2 Control

**Test File:** `tests/test_niryo_control.py`

```python
import pytest
from sentry_logic.niryo_tcp_bridge import NiryoTCPBridge

class TestNiryoControl:
    @pytest.fixture
    async def bridge(self):
        bridge = NiryoTCPBridge(robot_ip='192.168.0.244')
        await bridge.connect()
        yield bridge
        await bridge.disconnect()
    
    @pytest.mark.asyncio
    async def test_robot_calibration(self, bridge):
        """Verify robot auto-calibrates on connection [REQ-007]"""
        calibration_status = await bridge.get_calibration_status()
        assert calibration_status['is_calibrated'] == True
        
    @pytest.mark.asyncio
    async def test_trajectory_execution_6dof(self, bridge):
        """Execute 62-second test trajectory; verify all 6 DOF move [REQ-007, TC-007]"""
        # Load test trajectory (6 joints x N waypoints)
        trajectory = load_test_trajectory('test_trajectory_62s.json')
        
        start_time = time.time()
        await bridge.execute_trajectory(trajectory)
        elapsed = time.time() - start_time
        
        assert elapsed > 60  # Should take ~62 seconds
        assert elapsed < 65  # Allow 5% tolerance
        
    @pytest.mark.asyncio
    async def test_joint_state_feedback(self, bridge):
        """Verify /joint_states topic publishes feedback at 10 Hz [REQ-007, TC-007]"""
        states = []
        async def collect_states():
            async for state in bridge.joint_states_stream():
                states.append(state)
                if len(states) >= 100:
                    break
        
        await asyncio.wait_for(collect_states(), timeout=15)  # 10 Hz × 100 msgs = ~10s
        
        # Verify ~10 messages per second
        assert 90 < len(states) <= 110
```

**Acceptance Criteria:**
- ✓ Robot calibrates successfully
- ✓ All 6 DOF execute trajectory within 62±5 seconds
- ✓ Joint state feedback at 10 Hz ±10%
- ✓ No timeout/connection failures

---

## 4. System Test Specification

### 4.1 Network Isolation Test (Kill Switch Validation)

#### TC-001: Edge-First Mesh Topology

**Test Procedure:**
```bash
# Terminal 1: Start ROS2 workspace
cd /workspace/ros2_ws
source install/setup.bash
ros2 run sentry_logic cyclic_server &
ros2 run sentry_logic zkp_auth_verifier &

# Terminal 2: Run test suite
cd /workspace && python tests/test_network_isolation.py

# Inside test_network_isolation.py:
def test_edge_auth_during_wan_blackout():
    """
    1. Verify baseline: auth succeeds with WAN connected
    2. Simulate WAN disconnect: 'sudo iptables -I OUTPUT -d 0.0.0.0/0 -j DROP'
    3. Issue local auth command; assert succeeds
    4. Verify proof verified locally (no cloud contact)
    5. Restore WAN connectivity
    
    Acceptance: 100 auth cycles succeed during blackout
    """
    for trial in range(100):
        # Generate ZKP proof locally
        proof = prover.generate_proof(challenge)
        # Verify locally
        assert verifier.verify(proof) == True
```

**Expected Output:**
```
test_edge_auth_during_wan_blackout PASSED
✓ Local auth succeeded 100/100 times during network blackout
```

---

#### TC-002: Sub-500ms Recovery Latency

**Test Procedure:**
```bash
# Use tc/netem for packet loss injection
sudo tc qdisc add dev eth0 root netem loss 100%  # Simulate 100% packet loss

# Run latency measurement
python tests/test_recovery_latency.py
```

**Python Test:**
```python
import statistics

def test_sub_500ms_recovery():
    """
    Measure time from network disconnect to first valid auth
    """
    latencies_ms = []
    
    for trial in range(1000):
        # Inject network fault
        os.system('sudo iptables -I OUTPUT -d 0.0.0.0/0 -j DROP')
        
        # Measure recovery time
        start = time.perf_counter_ns()
        proof = prover.generate_proof(challenge)
        result = verifier.verify(proof)
        elapsed_ns = time.perf_counter_ns() - start
        
        # Restore network
        os.system('sudo iptables -D OUTPUT -d 0.0.0.0/0 -j DROP')
        
        latencies_ms.append(elapsed_ns / 1_000_000)
    
    p95 = statistics.quantiles(latencies_ms, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(latencies_ms, n=100)[98] # 99th percentile
    
    print(f"Recovery latency: p95={p95:.2f}ms, p99={p99:.2f}ms")
    
    assert p95 < 500, f"p95 recovery = {p95}ms EXCEEDS 500ms limit"
    assert p99 < 750, f"p99 recovery = {p99}ms EXCEEDS 750ms limit"
```

**Acceptance Criteria:**
- ✓ p95 recovery < 500ms (over 1000 trials)
- ✓ p99 recovery < 750ms
- ✓ Zero failed authentications

---

### 4.2 Safety-Critical Tests

#### TC-008: Fail-Safe on Crypto Failure

**Test Procedure:**
```python
def test_robot_halt_on_proof_rejection():
    """
    Verify robot halts immediately upon ZKP verification failure
    """
    # Start robot in motion
    ros2_pub.publish(TrajectoryGoal(...))
    
    # Inject malformed proof
    bad_proof = secrets.token_bytes(64)  # Random garbage
    
    # Send verification request
    start = time.perf_counter()
    result = verifier.verify(bad_proof)
    elapsed = time.perf_counter() - start
    
    assert result == False  # Verification fails
    assert elapsed < 0.010  # < 10ms rejection latency
    
    # Query robot state
    robot_state = query_robot_state()
    assert robot_state.velocity == 0  # Robot halted
    assert robot_state.is_safe_stop == True
```

**Acceptance Criteria:**
- ✓ Bad proof rejected < 10ms
- ✓ Robot halts immediately
- ✓ Safety alert logged (SAF-002)

---

#### TC-009: Audit Trail Completeness

**Test Procedure:**
```python
def test_audit_log_100_percent_coverage():
    """
    Execute 10 robot commands; verify 100% logged
    """
    commands = [
        TrajectoryGoal(joint_values=[0, 0, 0, 0, 0, 0]),
        TrajectoryGoal(joint_values=[1.57, 0.79, 0, 0, 0, 0]),
        # ... 8 more commands
    ]
    
    for cmd in commands:
        ros2_pub.publish(cmd)
        time.sleep(0.1)
    
    # Parse audit log
    with open('/var/log/sentry_audit.log') as f:
        lines = f.readlines()
    
    # Verify format: JSON with [timestamp, proof_hash, operator, command_digest]
    parsed_logs = [json.loads(line) for line in lines]
    
    assert len(parsed_logs) >= 10
    assert all('timestamp' in log for log in parsed_logs)
    assert all('proof_hash' in log for log in parsed_logs)
    assert all('command_digest' in log for log in parsed_logs)
```

**Acceptance Criteria:**
- ✓ 100% command coverage (10/10 logged)
- ✓ Log format conforms to schema
- ✓ No timestamp gaps

---

#### TC-010: Thermal Management

**Test Procedure:**
```bash
# Stress CPU to trigger thermal throttling
stress-ng --cpu 4 --timeout 60s &

# Monitor temperature
watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp'
```

**Python Monitoring:**
```python
def test_thermal_graceful_shutdown():
    """
    Verify Pi4 shuts down gracefully when CPU > 80°C
    """
    import subprocess
    
    # Start stress test
    stress = subprocess.Popen(['stress-ng', '--cpu', '4', '--timeout', '60s'])
    
    shutdown_triggered = False
    shutdown_time = None
    
    for poll_count in range(120):  # Poll for 2 minutes
        try:
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                temp_c = int(f.read()) / 1000
            
            if temp_c > 80 and not shutdown_triggered:
                shutdown_triggered = True
                shutdown_time = time.time()
                print(f"✓ Shutdown triggered at {temp_c}°C")
            
            if shutdown_triggered:
                elapsed_s = time.time() - shutdown_time
                if elapsed_s > 2:  # Should halt within 1s
                    raise AssertionError(f"Shutdown took {elapsed_s}s (> 1s limit)")
        
        except FileNotFoundError:
            # System may have shut down
            print("✓ System halted")
            break
        
        time.sleep(1)
    
    assert shutdown_triggered, "Thermal shutdown never triggered"
```

**Acceptance Criteria:**
- ✓ Shutdown triggers at 80°C
- ✓ Graceful halt < 1s
- ✓ No filesystem corruption

---

## 5. Test Automation & CI/CD

### 5.1 GitHub Actions Workflow

**File:** `.github/workflows/verify.yml`

```yaml
name: Verification Pipeline

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  static-analysis:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3
      - name: Pylint
        run: pylint ros2_ws/src/sentry_logic/**/*.py
      - name: Mypy
        run: mypy ros2_ws/src/sentry_logic

  unit-tests:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3
      - name: Run pytest
        run: |
          cd /workspace
          pytest tests/ -v --cov=sentry_logic --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  docker-build:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t sentry-c2:test .
      - name: Verify reproducibility
        run: |
          docker build -t sentry-c2:test1 .
          docker build -t sentry-c2:test2 .
          # Compare SHA256(manifest)

  integration-tests:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3
      - name: Start ROS2 container
        run: docker-compose up -d
      - name: Run TC-005, TC-006, TC-007
        run: pytest tests/test_ros2_composition.py -v
```

---

### 5.2 Test Execution Schedule

| Test Suite | Frequency | Duration | Owner |
|------------|-----------|----------|-------|
| Static analysis | Per commit | 2 min | CI/CD |
| Unit tests (TC-003A,B,C) | Per commit | 5 min | CI/CD |
| Docker build (TC-004) | Per release | 10 min | CI/CD |
| Integration tests (TC-005,6,7) | Per release | 20 min | Integration Lead |
| Network isolation (TC-001,2) | Per release candidate | 30 min | Performance Lead |
| Thermal test (TC-010) | Quarterly | 10 min | Systems Lead |
| Physical HIL (TC-007) | Before release | 90 min | Hardware Lead |

---

## 6. Test Result Documentation

### 6.1 Result Format

**Example:** `tests/results/tc-002_latency_histogram_v0.2.0-beta.csv`

```csv
trial,recovery_ms,status,notes
1,487.2,PASS,
2,493.1,PASS,
...
1000,512.8,FAIL,"exceeds 500ms limit"

SUMMARY:
Total trials: 1000
Pass: 998
Fail: 2
P95: 498.3ms
P99: 742.1ms
Status: CONDITIONAL_PASS (p95 < 500ms, p99 < 750ms)
```

### 6.2 Release Gate Criteria

**For v0.2.0-beta Release:**
- [ ] Unit tests: >85% code coverage
- [ ] TC-003 oracle: 0 accepted forgeries / 10K attempts
- [ ] TC-002 latency: p95 < 500ms (1000 trials)
- [ ] TC-007 HIL: 100% successful trajectory execution
- [ ] TC-010 thermal: graceful shutdown verified
- [ ] Zero regressions vs. v0.1-alpha baseline

---

## 7. Verification Metrics & Dashboard

**Metrics Collected Per Release:**

| Metric | Target | v0.1-alpha | v0.2.0-beta | v1.0.0 |
|--------|--------|-----------|------------|--------|
| Code coverage | ≥85% | 72% | TBD | TBD |
| Recovery latency p95 | <500ms | N/A | TBD | TBD |
| ZKP proof gen | <50ms | N/A | TBD | TBD |
| Test pass rate | 100% | 94% | TBD | TBD |
| Security issues | 0 | 0 | TBD | TBD |

---

## 8. Test Case Sign-Off Template

```
Test Case: TC-002 (Sub-500ms Recovery)
Version Tested: v0.2.0-beta
Date: 2026-03-15
Executed By: Integration Test Lead
Platform: Ubuntu 22.04 LTS (Docker)

Results:
✓ p95 latency: 498.2ms (target <500ms)
✓ p99 latency: 742.8ms (target <750ms)
✓ Zero failed authentications
✓ 1000 trial completions

Status: PASS

Verified By: _____________________
Date: _____________
```

---

## References

- [tests/traceability_matrix.csv](../tests/traceability_matrix.csv) — Full TC mapping
- [docs/PSAC.md](../docs/PSAC.md) — Software aspects of certification
- [DO-178C](https://www.faa.gov/aircraft/air_cert/design_approvals/air_software/) — Airborne software standard

---

**Prepared by:** Verification Lead  
**Date:** 2026-02-02  
**Next Review:** 2026-02-28 (or upon test failure)

