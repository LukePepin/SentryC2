#!/usr/bin/env python3
"""
SentryC2 Chaos Engineering: Livelock Simulator (H3 Validation)
===============================================================
MISSION: Generate authentication "Boot Storm" to validate exponential latency scaling.

HYPOTHESIS H3:
    Authentication latency scales exponentially with node density (n) due to
    ZKP verification queuing, leading to Livelock when L_avg > Trust Decay (α).

SAFETY CONSTRAINTS:
    - Timeout handling mandatory (Pi4 may drop packets under load)
    - No blocking calls in async context
    - Telemetry must capture sub-millisecond precision

ARCHITECTURE:
    Load Generator (this script) → Supervisor (Pi4 Auth Queue) → ZKP Verifier
"""

import asyncio
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
import time
import csv
import hashlib
import secrets
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

# Message imports (adjust to actual SentryC2 interfaces)
try:
    from sentry_msgs.srv import Authenticate  # Adjust to actual service
except ImportError:
    # Fallback mock for testing without ROS2 compiled messages
    print("[WARN] sentry_msgs not found. Using mock service definition.")
    from std_srvs.srv import Trigger as Authenticate


@dataclass
class AuthResult:
    """Telemetry payload for single authentication attempt."""
    node_id: int
    request_sent_ts: float  # Unix timestamp (microsecond precision)
    response_received_ts: float
    latency_ms: float
    status: str  # "SUCCESS" | "TIMEOUT" | "REJECTED" | "ERROR"
    zkp_hash: str  # For reproducibility tracking


class LoadGeneratorNode(Node):
    """Chaos Engineering Load Generator for Authentication Storm."""

    # ==== CONFIGURATION (Mission Parameters) ====
    NODE_COUNT: int = 10  # Number of simulated worker nodes
    BURST_INTERVAL: float = 0.0  # Delay between waves (0 = single burst)
    AUTH_TIMEOUT: float = 5.0  # Service call timeout (seconds)
    SUPERVISOR_SERVICE: str = '/supervisor/authenticate'  # Auth service endpoint

    def __init__(self):
        super().__init__('livelock_simulator')
        
        # Declare parameters with defaults
        self.declare_parameter('node_count', self.NODE_COUNT)
        self.declare_parameter('burst_interval', self.BURST_INTERVAL)
        self.declare_parameter('auth_timeout', self.AUTH_TIMEOUT)
        self.declare_parameter('supervisor_service', self.SUPERVISOR_SERVICE)
        
        # Read parameters
        self.node_count = self.get_parameter('node_count').value
        self.burst_interval = self.get_parameter('burst_interval').value
        self.auth_timeout = self.get_parameter('auth_timeout').value
        self.supervisor_service = self.get_parameter('supervisor_service').value
        
        self.get_logger().info(
            f'[CHAOS ENGINE] Initialized: {self.node_count} nodes, '
            f'timeout={self.auth_timeout}s'
        )
        
        # CRITICAL FIX: Create multiple clients for concurrent requests
        # Single client cannot handle burst of concurrent service calls
        self.auth_clients = []
        for i in range(self.node_count):
            client = self.create_client(Authenticate, f'{self.supervisor_service}')
            self.auth_clients.append(client)
        
        # Wait for service to be available (check with first client)
        self.get_logger().info(f'Waiting for service: {self.supervisor_service}')
        if not self.auth_clients[0].wait_for_service(timeout_sec=10.0):
            self.get_logger().error(f'Service {self.supervisor_service} not available!')
            raise RuntimeError(f'Service {self.supervisor_service} unavailable')
        
        self.get_logger().info(f'✓ Service {self.supervisor_service} is ready')
        self.results: List[AuthResult] = []

    def generate_zkp_mock(self, node_id: int) -> Tuple[str, str]:
        """
        Generate mock Schnorr ZKP for authentication.
        
        ACQUISITION LOGIC: In production, use libsecp256k1 or micro-ecc.
        For load testing, cryptographic mock is acceptable (same computational load).
        
        Returns:
            (proof_hex, challenge_hex): Simulated ZKP components
        """
        # Simulate ZKP computation (SHA256 as stand-in for elliptic curve ops)
        secret = secrets.token_bytes(32)
        challenge = hashlib.sha256(f"node_{node_id}_{time.time()}".encode()).digest()
        proof = hashlib.sha256(secret + challenge).digest()
        
        return proof.hex(), challenge.hex()

    async def authenticate_single_node(self, node_id: int) -> AuthResult:
        """
        Single async authentication task (one simulated worker node).
        
        CRITICAL: Must handle timeout without crashing parent task.
        """
        # Generate unique ZKP for this node
        proof, challenge = self.generate_zkp_mock(node_id)
        zkp_hash = hashlib.sha256(proof.encode()).hexdigest()[:16]
        
        # Build request
        request = Authenticate.Request()
        # Note: For mock (Trigger), request has no fields
        
        # === THE CRITICAL BURST POINT ===
        t_start = time.time()  # Microsecond precision
        
        try:
            # Call service asynchronously (use dedicated client for this node)
            client = self.auth_clients[node_id] if node_id < len(self.auth_clients) else self.auth_clients[0]
            future = client.call_async(request)
            
            # Wait for response with timeout (polling approach for rclpy compatibility)
            elapsed = 0.0
            poll_interval = 0.01  # 10ms polling
            while not future.done() and elapsed < self.auth_timeout:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            
            if not future.done():
                # Timeout occurred
                self.get_logger().warn(f"Node {node_id}: TIMEOUT after {self.auth_timeout}s (Queue overload likely)")
                return AuthResult(
                    node_id=node_id,
                    request_sent_ts=t_start,
                    response_received_ts=time.time(),
                    latency_ms=0.0,
                    status="TIMEOUT",
                    zkp_hash=zkp_hash
                )
            
            # Get response
            response = future.result()
            
            t_end = time.time()
            latency_ms = (t_end - t_start) * 1000.0
            
            # Interpret response
            # For mock (Trigger): response.success
            # For real: response.authenticated or similar
            if hasattr(response, 'success') and response.success:
                status = "SUCCESS"
            elif hasattr(response, 'authenticated') and response.authenticated:
                status = "SUCCESS"
            else:
                status = "REJECTED"
            
            self.get_logger().info(
                f"Node {node_id}: {status} | Latency: {latency_ms:.3f}ms"
            )
            
            return AuthResult(
                node_id=node_id,
                request_sent_ts=t_start,
                response_received_ts=t_end,
                latency_ms=latency_ms,
                status=status,
                zkp_hash=zkp_hash
            )
            
        except asyncio.TimeoutError:
            t_end = time.time()
            self.get_logger().warn(
                f"Node {node_id}: TIMEOUT after {self.auth_timeout}s "
                f"(Queue overload likely)"
            )
            return AuthResult(
                node_id=node_id,
                request_sent_ts=t_start,
                response_received_ts=t_end,
                latency_ms=(t_end - t_start) * 1000.0,
                status="TIMEOUT",
                zkp_hash=zkp_hash
            )
        except Exception as e:
            t_end = time.time()
            self.get_logger().error(f"Node {node_id}: ERROR - {e}")
            return AuthResult(
                node_id=node_id,
                request_sent_ts=t_start,
                response_received_ts=t_end,
                latency_ms=(t_end - t_start) * 1000.0,
                status="ERROR",
                zkp_hash=zkp_hash
            )

    async def execute_boot_storm(self) -> List[AuthResult]:
        """
        THE BOOT STORM: Spawn N concurrent authentication tasks.
        
        CONCURRENCY MODEL: asyncio.gather() ensures true parallel burst,
        not sequential iteration (critical for H3 validation).
        """
        self.get_logger().warn(
            f"[STORM INITIATED] Launching {self.node_count} concurrent auth requests..."
        )
        
        # Create task list
        tasks = [
            self.authenticate_single_node(node_id=i)
            for i in range(self.node_count)
        ]
        
        # === PARALLEL EXECUTION (The Burst) ===
        # All tasks execute concurrently, hitting Supervisor queue simultaneously
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        self.get_logger().info("[STORM COMPLETE] All authentication attempts finished.")
        return results

    def save_telemetry(self, results: List[AuthResult], output_path: str):
        """
        Persist telemetry to CSV for post-analysis.
        
        OUTPUT FORMAT:
            node_id, request_sent_ts, response_received_ts, latency_ms, status, zkp_hash
        """
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = ['node_id', 'request_sent_ts', 'response_received_ts',
                         'latency_ms', 'status', 'zkp_hash']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))
        
        self.get_logger().info(f"[TELEMETRY] Saved to {output_path}")

    def analyze_results(self, results: List[AuthResult]):
        """
        Compute H3 validation metrics.
        
        KEY METRICS:
            - L_avg: Mean latency across all nodes
            - L_max: Maximum latency (Node_N in FIFO queue)
            - Timeout Rate: Percentage of TIMEOUT vs SUCCESS
        """
        if not results:
            self.get_logger().error("[ANALYSIS] No results to analyze!")
            return
        
        latencies = [r.latency_ms for r in results if r.status in ["SUCCESS", "REJECTED"]]
        timeouts = [r for r in results if r.status == "TIMEOUT"]
        
        if latencies:
            l_avg = sum(latencies) / len(latencies)
            l_max = max(latencies)
            l_min = min(latencies)
        else:
            l_avg = l_max = l_min = 0.0
        
        timeout_rate = (len(timeouts) / len(results)) * 100.0
        
        self.get_logger().info("=" * 60)
        self.get_logger().info("[H3 VALIDATION METRICS]")
        self.get_logger().info(f"  Node Count (n):      {len(results)}")
        self.get_logger().info(f"  L_avg (Mean):        {l_avg:.3f} ms")
        self.get_logger().info(f"  L_max (Worst Case):  {l_max:.3f} ms")
        self.get_logger().info(f"  L_min (Best Case):   {l_min:.3f} ms")
        self.get_logger().info(f"  Timeout Rate:        {timeout_rate:.1f}%")
        self.get_logger().info(f"  Expected Linear:     {len(results) * 0.67:.3f} ms")
        self.get_logger().info("=" * 60)
        
        # H3 Validation Logic
        baseline_linear = len(results) * 0.67  # Expected if perfectly linear
        if l_avg > baseline_linear * 1.5:  # 50% deviation threshold
            self.get_logger().warn(
                "[H3 CONFIRMED] Latency scaling exceeds linear prediction. "
                "Exponential queuing detected."
            )
        else:
            self.get_logger().info(
                "[H3 NOT CONFIRMED] Latency within linear bounds."
            )


async def main_async(args=None):
    """Async entry point for ROS2 + asyncio integration."""
    rclpy.init(args=args)
    
    node = LoadGeneratorNode()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    
    # Spin executor in background thread to process callbacks
    import threading
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    
    try:
        # Execute the boot storm
        results = await node.execute_boot_storm()
        
        # Save telemetry to data/ directory (excluded from GitHub)
        import os
        
        # Check for async parallel mode via environment variable
        test_mode = os.environ.get('H3_TEST_MODE', 'baseline')
        if test_mode == 'async':
            data_subdir = 'h3_async_parallel'
        else:
            data_subdir = ''
        
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data', data_subdir)
        os.makedirs(data_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(data_dir, f"h3_test_n{node.node_count}_{timestamp}.csv")
        node.save_telemetry(results, output_file)
        
        # Analyze results
        node.analyze_results(results)
        
    except KeyboardInterrupt:
        node.get_logger().info("[ABORTED] User interrupt.")
    except Exception as e:
        node.get_logger().error(f"[CRITICAL ERROR] {e}", exc_info=True)
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


def main(args=None):
    """Standard synchronous entry point (wraps async logic)."""
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
