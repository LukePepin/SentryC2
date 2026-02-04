#!/usr/bin/env python3
"""
H1 VALIDATION DATA LISTENER
============================
Records network latency, heartbeat events, and packet loss during chaos testing.

Output: CSV file with columns:
  - timestamp_ms: Milliseconds since test start
  - event_type: HEARTBEAT|TIMEOUT|PACKET_LOSS|SAFETY_HOLD
  - latency_ms: RTT estimate (or 0 if no measurement)
  - rtt_confidence: 0.0-1.0 (how confident in the latency measurement)
  - notes: Free-form event description

**MISSION:** Capture the exact moment when:
  1. Packets start dropping (latency spikes)
  2. TCP RTO kicks in (RTT jumps > 1000ms)
  3. Watchdog timeout fires (safetyHoldActive = TRUE)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
import csv
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class TelemetryEvent:
    """Atomic telemetry data point for H1 validation."""
    timestamp_ms: float
    event_type: str  # HEARTBEAT|TIMEOUT|PACKET_LOSS|SAFETY_HOLD
    latency_ms: float
    rtt_confidence: float
    notes: str


class H1TestListener(Node):
    """
    ROS2 Node: Subscribes to /joint_states and records network telemetry.
    
    **Operational Logic:**
    - On each message arrival: record latency (now - header.stamp)
    - Track inter-arrival time (should be ~100ms @ 10Hz)
    - If inter-arrival > 200ms: flag as PACKET_LOSS
    - If inter-arrival > 2000ms: flag as TIMEOUT
    """
    
    def __init__(self):
        super().__init__('h1_test_listener')
        
        # Create output directory if needed
        self.output_dir = Path("/workspace/ros2_ws/data/h1_validation")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Timestamp the run for unique filenames
        self.test_id = time.strftime("%Y%m%d_%H%M%S")
        self.csv_file = self.output_dir / f"h1_test_{self.test_id}.csv"
        
        # Test timing
        self.test_start_time = time.time()
        self.last_message_time = None
        self.last_message_arrival_ms = 0
        
        # Expected interval at 10Hz (100ms)
        self.expected_interval_ms = 100.0
        self.packet_loss_threshold_ms = 150.0  # Allow 50% jitter
        self.timeout_threshold_ms = 2500.0  # Watchdog is 2.0s
        
        # CSV writer setup
        self.csv_file.write_text("")  # Clear file
        self.writer = None
        self.csvfile = None
        
        # Subscription
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10
        )
        
        # Safety state listener (optional: listen to Unity via ROS topic)
        # For now, we'll infer from latency patterns
        
        self.get_logger().info(
            f"[H1 LISTENER] Active. Output: {self.csv_file}"
        )
        self.get_logger().info(
            f"[H1 LISTENER] Expected interval: {self.expected_interval_ms}ms"
        )
        
    def joint_state_callback(self, msg: JointState):
        """Called on every JointState message arrival."""
        
        now = time.time()
        elapsed_ms = (now - self.test_start_time) * 1000.0
        
        # Initialize CSV writer on first message
        if self.writer is None:
            self._init_csv()
        
        # Calculate inter-arrival time
        if self.last_message_time is None:
            inter_arrival_ms = 0.0
            latency_ms = 0.0
            rtt_confidence = 0.0
            event_type = "HEARTBEAT"
            notes = "First message (baseline)"
        else:
            inter_arrival_ms = (now - self.last_message_time) * 1000.0
            
            # **LATENCY ESTIMATION:**
            # ROS2 DDS provides header.stamp from the publisher.
            # RTT ≈ (arrival_time - msg_stamp)
            try:
                if msg.header.stamp.sec > 0:
                    msg_time = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
                    latency_ms = (now - msg_time) * 1000.0
                    rtt_confidence = 0.9  # High confidence if timestamp exists
                else:
                    latency_ms = inter_arrival_ms * 0.5  # Rough estimate
                    rtt_confidence = 0.3
            except:
                latency_ms = 0.0
                rtt_confidence = 0.0
            
            # **EVENT CLASSIFICATION:**
            if inter_arrival_ms > self.timeout_threshold_ms:
                event_type = "TIMEOUT"
                notes = f"No message for {inter_arrival_ms:.0f}ms (> 2.5s threshold)"
            elif inter_arrival_ms > self.packet_loss_threshold_ms:
                event_type = "PACKET_LOSS"
                notes = f"Delayed arrival: {inter_arrival_ms:.0f}ms (expected {self.expected_interval_ms:.0f}ms)"
            else:
                event_type = "HEARTBEAT"
                notes = f"Normal cycle: {inter_arrival_ms:.0f}ms"
        
        # **RECORD TO CSV**
        event = TelemetryEvent(
            timestamp_ms=elapsed_ms,
            event_type=event_type,
            latency_ms=latency_ms,
            rtt_confidence=rtt_confidence,
            notes=notes
        )
        self._write_event(event)
        
        # **CONSOLE LOG (Critical Events Only)**
        if event_type != "HEARTBEAT":
            self.get_logger().warn(
                f"[H1 EVENT] {event.event_type} @ {elapsed_ms:.1f}ms | "
                f"Latency: {latency_ms:.1f}ms (confidence: {rtt_confidence:.2f})"
            )
        
        self.last_message_time = now
        self.last_message_arrival_ms = elapsed_ms
    
    def _init_csv(self):
        """Initialize CSV file with header."""
        self.csvfile = open(self.csv_file, 'w', newline='')
        fieldnames = [
            'timestamp_ms',
            'event_type',
            'latency_ms',
            'rtt_confidence',
            'notes'
        ]
        self.writer = csv.DictWriter(self.csvfile, fieldnames=fieldnames)
        self.writer.writeheader()
        self.get_logger().info(f"[H1 LISTENER] CSV initialized: {self.csv_file}")
    
    def _write_event(self, event: TelemetryEvent):
        """Write a single telemetry event to CSV."""
        if self.writer is None:
            return
        
        self.writer.writerow({
            'timestamp_ms': f"{event.timestamp_ms:.1f}",
            'event_type': event.event_type,
            'latency_ms': f"{event.latency_ms:.1f}",
            'rtt_confidence': f"{event.rtt_confidence:.2f}",
            'notes': event.notes
        })
        self.csvfile.flush()  # Ensure write to disk immediately
    
    def __del__(self):
        """Cleanup on shutdown."""
        if self.csvfile:
            self.csvfile.close()
            self.get_logger().info(f"[H1 LISTENER] CSV closed. File: {self.csv_file}")


def main(args=None):
    rclpy.init(args=args)
    node = H1TestListener()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
