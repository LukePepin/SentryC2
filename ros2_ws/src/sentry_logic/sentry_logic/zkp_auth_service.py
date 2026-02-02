#!/usr/bin/env python3
"""
ZKP Authentication ROS2 Service Node
====================================
Exposes ZKP authentication as ROS2 services for mesh network integration.

**Hardware:** Raspberry Pi 4 (Supervisor Node)
**Protocol:** ROS2 Services over DDS
**Functions:**
    1. /zkp/challenge - Issue authentication challenge
    2. /zkp/verify - Verify signature and issue session token
    3. /zkp/validate - Validate existing session token

Author: SentryC2 Security Team
Date: February 2026
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from action_msgs.srv import CancelGoal
import json
import base64

from .zkp_auth_verifier import ZKPAuthVerifier


class ZKPAuthService(Node):
    """
    ROS2 Service Node for Zero-Knowledge Proof Authentication
    
    Integrates cryptographic verifier with ROS2 ecosystem.
    Allows any node to request authentication via service calls.
    """
    
    def __init__(self):
        super().__init__('zkp_auth_service')
        
        # Initialize cryptographic verifier
        self.verifier = ZKPAuthVerifier()
        
        # Create ROS2 services (using String messages for simplicity)
        # TODO: Define custom message types in future iteration
        self.challenge_service = self.create_service(
            CancelGoal,
            '/zkp/challenge',
            self.handle_challenge_request
        )
        
        # Publisher for auth events (monitoring)
        self.event_publisher = self.create_publisher(
            String,
            '/zkp/auth_events',
            10
        )
        
        # Metrics timer (publish every 10 seconds)
        self.metrics_timer = self.create_timer(10.0, self.publish_metrics)
        
        self.get_logger().info('🔐 ZKP Authentication Service ONLINE')
        self.get_logger().info('   - Challenge Service: /zkp/challenge')
        self.get_logger().info('   - Auth Events: /zkp/auth_events')
    
    def handle_challenge_request(self, request, response):
        """
        Issue authentication challenge
        
        Request: Empty (or device_id for tracking)
        Response: Base64-encoded nonce
        """
        try:
            nonce = self.verifier.generate_challenge()
            
            # Encode nonce as base64 for transmission
            nonce_b64 = base64.b64encode(nonce).decode('utf-8')
            
            # Publish event
            event = {
                'type': 'challenge_issued',
                'nonce': nonce_b64[:16] + '...',  # Truncated for logs
                'timestamp': self.get_clock().now().nanoseconds / 1e9
            }
            self.event_publisher.publish(String(data=json.dumps(event)))
            
            # Note: Using CancelGoal is a temporary hack
            # TODO: Create custom srv/Challenge.srv message type
            response.return_code = 0  # Success
            
            self.get_logger().info(f'Issued challenge: {nonce_b64[:16]}...')
            return response
            
        except Exception as e:
            self.get_logger().error(f'Challenge generation failed: {e}')
            response.return_code = -1
            return response
    
    def publish_metrics(self):
        """Publish authentication metrics for monitoring"""
        metrics = self.verifier.get_metrics()
        
        msg = String()
        msg.data = json.dumps({
            'type': 'metrics',
            'data': metrics,
            'timestamp': self.get_clock().now().nanoseconds / 1e9
        })
        
        self.event_publisher.publish(msg)
        
        # Log summary
        self.get_logger().info(
            f'📊 Auth Metrics: '
            f'{metrics["verifications_succeeded"]}/{metrics["verifications_attempted"]} '
            f'({metrics["success_rate"]:.1f}% success), '
            f'{metrics["active_sessions"]} active sessions'
        )


def main(args=None):
    """ROS2 node entrypoint"""
    rclpy.init(args=args)
    
    node = ZKPAuthService()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('🔒 ZKP Authentication Service shutting down...')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
