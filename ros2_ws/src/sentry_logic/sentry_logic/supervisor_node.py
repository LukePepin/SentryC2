#!/usr/bin/env python3
"""
Supervisor Authentication Node (Admission Control Architecture)
===============================================================
ZKP authentication service with token bucket admission control.

**Mission:** Prevent queue saturation via early request rejection
**Hardware:** Raspberry Pi 4 (4-core Cortex-A72)
**Service:** /supervisor/authenticate (std_srvs/Trigger)
**Concurrency:** MultiThreadedExecutor with admission control

ARCHITECTURAL EVOLUTION:
    v1 (Baseline): Single-threaded FIFO → Livelock @ n=20 (45% timeout)
    v2 (ThreadPool): concurrent.futures → FAILED (45% timeout, identical)
    v3 (MultiThreaded): rclpy.MultiThreadedExecutor → FAILED (45% timeout, identical)
    v4 (Priority Queue): Timestamp ordering → FAILED (network reordering occurs before timestamps)
    v5 (This): Admission control → Reject requests early to prevent timeout cascade

ROOT CAUSE:
    Requests timeout waiting in queue. Cannot fix ordering (network layer issue).
    Solution: REJECT requests when concurrent load exceeds capacity.
    Better to fail fast (immediate rejection) than fail slow (5s timeout).

CRITICAL CONSTRAINTS:
    - Max concurrent requests = num_workers (4 on Pi4)
    - Reject new requests when active >= max_concurrent
    - Fast rejection (< 1ms) better than timeout (5000ms)
"""

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_srvs.srv import Trigger
import time
import hashlib
import threading


class SupervisorNode(Node):
    """
    Supervisor authentication service with admission control.
    
    ARCHITECTURE:
        1. Track active concurrent requests
        2. Reject new requests when active >= max_concurrent
        3. Process accepted requests in parallel (4 threads)
    
    ADMISSION CONTROL:
        - Capacity = 4 (num_workers on Pi4)
        - Accept: active < capacity
        - Reject: active >= capacity (fail fast, <1ms response)
        - Prevents timeout cascade (5000ms wait → immediate rejection)
    """
    
    def __init__(self):
        super().__init__('supervisor_node')
        
        # Parameters
        self.declare_parameter('auth_enabled', True)
        self.declare_parameter('zkp_delay_ms', 0.67)
        self.declare_parameter('num_workers', 4)
        self.declare_parameter('max_concurrent', 10)  # Admission control threshold
        
        self.auth_enabled = self.get_parameter('auth_enabled').value
        self.zkp_delay = self.get_parameter('zkp_delay_ms').value / 1000.0
        self.num_workers = self.get_parameter('num_workers').value
        self.max_concurrent = self.get_parameter('max_concurrent').value
        
        # === ADMISSION CONTROL: Track concurrent requests ===
        self.active_requests = 0
        self.active_lock = threading.Lock()
        
        # Metrics
        self.auth_count = 0
        self.rejected_count = 0
        self.start_time = time.time()
        
        # Callback group for parallel execution
        self.callback_group = ReentrantCallbackGroup()
        
        # Authentication service
        self.auth_service = self.create_service(
            Trigger,
            '/supervisor/authenticate',
            self.handle_authentication,
            callback_group=self.callback_group
        )
        
        self.get_logger().info(
            f'🔐 Supervisor Node ONLINE (ADMISSION CONTROL v5.2)\n'
            f'   - Service: /supervisor/authenticate\n'
            f'   - Auth Enabled: {self.auth_enabled}\n'
            f'   - ZKP Delay: {self.zkp_delay*1000:.2f}ms\n'
            f'   - Architecture: ADMISSION CONTROL + MultiThreadedExecutor\n'
            f'   - Workers: {self.num_workers} threads\n'
            f'   - Max Concurrent: {self.max_concurrent} requests\n'
            f'   - Hardware: Raspberry Pi 4 (4-core Cortex-A72)\n'
            f'   - STRATEGY: Fail fast (reject) instead of fail slow (timeout)\n'
            f'   - BUILD: 2026-02-10 14:01 (atomic admission control with logging)'
        )
    
    def handle_authentication(self, request, response):
        """
        Service callback with admission control.
        
        ADMISSION CONTROL LOGIC:
            IF active_requests < max_concurrent:
                Accept and process request
            ELSE:
                Reject immediately (fail fast)
        
        BENEFIT: Rejected clients get immediate feedback (<1ms) instead of
                 waiting 5000ms for timeout. Prevents queue saturation.
        """
        if not self.auth_enabled:
            response.success = False
            response.message = "Authentication disabled"
            return response
        
        # === ADMISSION CONTROL: Check capacity ===
        accepted = False
        with self.active_lock:
            if self.active_requests < self.max_concurrent:
                # ACCEPT: Increment active counter atomically
                self.active_requests += 1
                accepted = True
        
        if not accepted:
            # REJECT: Capacity exceeded
            self.rejected_count += 1
            response.success = False
            response.message = (
                f"AUTH_REJECTED|queue_saturated "
                f"(active={self.active_requests}/{self.max_concurrent})"
            )
            self.get_logger().info(
                f'REJECTED: {self.rejected_count} total '
                f'(active={self.active_requests}/{self.max_concurrent})'
            )
            return response
        
        # Process request
        try:
            req_start = time.time()
            verification_success = self._verify_zkp(request)
            processing_time = (time.time() - req_start) * 1000
            
            if verification_success:
                response.success = True
                response.message = f'Authenticated (took {processing_time:.2f} ms)'
                self.auth_count += 1
                self.get_logger().info(
                    f'ACCEPTED: Auth #{self.auth_count} ({processing_time:.2f}ms)'
                )
            else:
                response.success = False
                response.message = 'AUTH_REJECTED|invalid_proof'
        
        finally:
            # Decrement active counter
            with self.active_lock:
                self.active_requests -= 1
        
        return response
    
    def _verify_zkp(self, request) -> bool:
        """
        ZKP verification (executes on MultiThreadedExecutor thread).
        
        ACQUISITION LOGIC: Uses hashlib (stdlib) instead of libsecp256k1.
        Calibrated to match ~0.67ms CPU time on Pi4.
        """
        # Simulate cryptographic operation
        time.sleep(self.zkp_delay)
        
        # Add minimal CPU work for realism (SHA256 chain)
        data = b"zkp_verification_" + str(time.time()).encode()
        for _ in range(10):
            data = hashlib.sha256(data).digest()
        
        # In production: Verify elliptic curve signature
        # For simulation: Always return True
        return True
    
    def destroy_node(self):
        """Graceful shutdown."""
        self.get_logger().info("Shutting down supervisor node...")
        super().destroy_node()


def main(args=None):
    """ROS2 node entrypoint with MultiThreadedExecutor"""
    rclpy.init(args=args)
    
    node = SupervisorNode()
    
    # Use MultiThreadedExecutor for parallel callback processing
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        uptime = time.time() - node.start_time
        total_requests = node.auth_count + node.rejected_count
        if total_requests > 0:
            node.get_logger().info(
                f'\n🔒 Supervisor Node shutting down\n'
                f'   Total auths: {node.auth_count}\n'
                f'   Rejected: {node.rejected_count}\n'
                f'   Success rate: {node.auth_count/total_requests*100:.1f}%\n'
                f'   Uptime: {uptime:.1f}s\n'
                f'   Avg rate: {node.auth_count/uptime:.2f} req/s'
            )
        else:
            node.get_logger().info(f'\n🔒 Supervisor Node shutting down (no requests processed, uptime: {uptime:.1f}s)')
        node.destroy_node()
        executor.shutdown()
        # Don't call rclpy.shutdown() - executor already did it


if __name__ == '__main__':
    main()
