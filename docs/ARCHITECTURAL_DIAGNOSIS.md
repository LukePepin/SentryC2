# ARCHITECTURAL DIAGNOSIS: H3 Livelock Mitigation Attempts

## Test Results Summary

| Architecture | n=12 | n=20 | n=24 | Status |
|--------------|------|------|------|--------|
| **Baseline** (Single-Thread) | 8.3% | 45.0% | 54.2% | ❌ Livelock |
| **ThreadPoolExecutor** | 16.7% | 45.0% | 54.2% | ❌ No improvement |
| **MultiThreadedExecutor** | TBD | TBD | TBD | ⏳ Testing |

## Root Cause Analysis

### Attempt 1: ThreadPoolExecutor (FAILED)
**Hypothesis:** Offload crypto to worker threads to unblock main thread.

**Implementation:**
```python
future = self.thread_pool.submit(self._verify_crypto_heavy, request)
result = future.result(timeout=10.0)  # BLOCKS HERE
```

**Failure Mode:** `future.result()` blocks the callback, preventing ROS2 from accepting new requests.

### Attempt 2: MultiThreadedExecutor (FAILED)
**Hypothesis:** ROS2's native multi-threading with ReentrantCallbackGroup allows true parallelism.

**Implementation:**
```python
# ReentrantCallbackGroup on service
executor = MultiThreadedExecutor(num_threads=4)
```

**Failure Mode:** Even with 4 threads, requests still timeout at same rate.

## Probable Root Causes

### 1. **DDS Queue Saturation**
CycloneDDS may be queuing requests before they reach ROS2 callbacks:
- WHC (Write History Cache) limit: 500kB
- Network buffer exhaustion
- QoS reliability backpressure

### 2. **Client-Side Timeout Too Aggressive**
Current timeout: 5.0s
- If 20 requests burst simultaneously
- Only 4 can process concurrently (4 threads)
- Each takes ~10-11ms (observed from successful requests)
- Queue depth: 20 - 4 = 16 waiting
- Time for request #20: 4 batches × 11ms ≈ 44ms
- **BUT** clients timeout after 5000ms

**This should NOT cause 45% timeout unless:**
- Network latency is high (100ms+)
- DDS discovery/negotiation adds overhead
- Queue is actually serial, not parallel

### 3. **Executor Not Actually Parallel**
Verify on Pi4:
```bash
# Check if multiple supervisor callbacks execute simultaneously
ps -eLf | grep supervisor_node  # Should show 4+ threads
```

## Diagnostic Commands

### On Pi4 (while supervisor running):
```bash
# Check thread count
ps -eLf | grep supervisor_node | wc -l

# Monitor CPU usage (should hit ~400% if all 4 cores busy)
top -p $(pgrep -f supervisor_node)

# Check if truly parallel
watch -n 0.1 'ros2 service list | grep authenticate'
```

### On Local Machine (during test):
```bash
# Increase timeout to 30s to see if requests eventually succeed
# Modify livelock_sim.py: AUTH_TIMEOUT = 30.0
```

## Next Steps

### Option A: Increase Client Timeout
If requests are queuing but eventually succeeding:
```python
# tests/livelock_sim.py
AUTH_TIMEOUT: float = 30.0  # Was 5.0
```

### Option B: DDS QoS Tuning
Increase queue depths in cyclonedds_pi4.xml:
```xml
<Watermarks>
    <WhcHigh>2000kB</WhcHigh>  <!-- Was 500kB -->
</Watermarks>
```

### Option C: Rate Limiting (Admission Control)
Instead of parallel processing, implement queue with backpressure:
```python
# Return "503 Service Unavailable" if queue full
if len(self.pending_requests) > 10:
    response.success = False
    response.message = "QUEUE_FULL"
```

### Option D: Accept H3 Result
**Acknowledge architectural limit:**
- Single Pi4 cannot handle >10 concurrent auth requests
- Document scalability boundary
- Recommend distributed supervisor architecture (multiple Pi4s)

## Expected Behavior (If Parallel Works)

With 4 threads and n=20 burst:
- Batch 1 (requests 1-4): ~11ms
- Batch 2 (requests 5-8): ~22ms  
- Batch 3 (requests 9-12): ~33ms
- Batch 4 (requests 13-16): ~44ms
- Batch 5 (requests 17-20): ~55ms

**All should complete <100ms - well within 5s timeout.**

If still timing out → DDS/network issue, not threading.

## Recommended Action

Run diagnostic on Pi4 to confirm threads are actually executing in parallel:

```bash
# On Pi4 during test run
watch -n 0.5 'ps -eLf | grep supervisor_node | wc -l'
```

Expected: 5-8 threads (1 main + 4 workers + ROS2 internal)
If seeing only 1-2 threads → Executor not parallelizing
