#!/usr/bin/env python3
"""
Mock Niryo TCP Bridge - Hardware-Free Testing
Simulates bridge behavior without PyNiryo2 dependency
Executes full JointTrajectory sequences with proper waypoint interpolation
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from std_msgs.msg import Header
import math


class MockNiryoTCPBridge(Node):
    def __init__(self):
        super().__init__('mock_niryo_bridge')
        
        # Parameters
        self.declare_parameter('publish_rate', 10.0)  # Hz
        
        self.publish_rate = self.get_parameter('publish_rate').value
        
        # Publisher for joint states
        self.joint_state_pub = self.create_publisher(
            JointState,
            '/joint_states',
            10
        )
        
        # Subscriber for trajectory commands
        self.trajectory_sub = self.create_subscription(
            JointTrajectory,
            '/niryo_robot_follow_joint_trajectory_controller/follow_joint_trajectory',
            self.trajectory_callback,
            10
        )
        
        # Simulated robot state
        self.current_positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.trajectory_waypoints = []  # List of (time_sec, [joint_positions])
        self.trajectory_active = False
        self.trajectory_start_time = None
        
        # Timer for publishing
        self.timer = self.create_timer(
            1.0 / self.publish_rate,
            self.timer_callback
        )
        
        self.get_logger().info('Mock Niryo Bridge initialized (Hardware-Free Mode)')
        self.get_logger().info(f'Publishing joint states at {self.publish_rate} Hz')
    
    def trajectory_callback(self, msg):
        """Handle incoming trajectory commands - execute full sequence with waypoint interpolation"""
        self.get_logger().info(f'Received trajectory with {len(msg.points)} points')
        
        # Validate trajectory structure
        if not msg.points:
            self.get_logger().error('Empty trajectory received')
            return
        
        # Extract all waypoints with timing
        self.trajectory_waypoints = []
        for i, point in enumerate(msg.points):
            # Only accept first 6 joints (ignore gripper if present)
            if len(point.positions) < 6:
                self.get_logger().error(
                    f'Invalid point {i}: expected at least 6 joints, got {len(point.positions)}'
                )
                return
            
            duration = point.time_from_start.sec + point.time_from_start.nanosec / 1e9
            positions = list(point.positions[:6])
            self.trajectory_waypoints.append((duration, positions))
            
            self.get_logger().info(
                f'  Waypoint {i+1}: positions={[f"{p:.3f}" for p in positions]}, '
                f'time={duration:.2f}s'
            )
        
        # Start trajectory execution
        self.trajectory_active = True
        self.trajectory_start_time = self.get_clock().now()
        self.get_logger().info(f'Trajectory execution started - {len(self.trajectory_waypoints)} waypoints')
    
    def timer_callback(self):
        """Publish joint states; interpolate if trajectory active"""
        
        if self.trajectory_active and self.trajectory_start_time is not None:
            # Calculate elapsed time since trajectory start
            elapsed = (self.get_clock().now() - self.trajectory_start_time).nanoseconds / 1e9
            
            # Get last waypoint time
            last_waypoint_time = self.trajectory_waypoints[-1][0]
            
            if elapsed >= last_waypoint_time:
                # Trajectory complete - hold at final position
                self.current_positions = self.trajectory_waypoints[-1][1]
                self.trajectory_active = False
                self.get_logger().info('Trajectory execution complete')
            else:
                # Find interpolation interval
                self.current_positions = self._interpolate_waypoint(elapsed)
        
        # Create and publish JointState message
        joint_state = JointState()
        joint_state.header = Header()
        joint_state.header.stamp = self.get_clock().now().to_msg()
        
        joint_state.name = [
            'joint_1',
            'joint_2', 
            'joint_3',
            'joint_4',
            'joint_5',
            'joint_6'
        ]
        joint_state.position = self.current_positions
        
        self.joint_state_pub.publish(joint_state)
        
        # Log at reduced rate to avoid spam
        if hasattr(self, '_log_counter'):
            self._log_counter += 1
        else:
            self._log_counter = 0
        
        if self._log_counter % 20 == 0:  # Log every 2 seconds at 10Hz
            pos_str = ', '.join([f'{p:.3f}' for p in self.current_positions])
            self.get_logger().info(f'Joint states: [{pos_str}]')
    
    def _interpolate_waypoint(self, elapsed_time):
        """Linear interpolation between waypoints"""
        # Find the two surrounding waypoints
        prev_time, prev_positions = 0.0, [0.0] * 6
        
        for time_sec, positions in self.trajectory_waypoints:
            if time_sec > elapsed_time:
                # Interpolate between prev and current
                if elapsed_time <= 0:
                    return prev_positions
                
                dt = time_sec - prev_time
                if dt == 0:
                    return positions
                
                # Linear interpolation factor
                alpha = (elapsed_time - prev_time) / dt
                alpha = max(0.0, min(1.0, alpha))  # Clamp to [0, 1]
                
                interpolated = []
                for i in range(6):
                    pos = prev_positions[i] + alpha * (positions[i] - prev_positions[i])
                    interpolated.append(pos)
                
                return interpolated
            
            prev_time = time_sec
            prev_positions = positions
        
        # If we get here, return last waypoint
        return self.trajectory_waypoints[-1][1]
        """Periodically publish simulated joint states"""
        
        # Simulate smooth motion toward target (simple proportional control)
        if self.trajectory_active:
            for i in range(6):
                error = self.target_positions[i] - self.current_positions[i]
                self.current_positions[i] += error * 0.1  # 10% step
                
                # Stop when close enough
                if abs(error) < 0.001:
                    self.current_positions[i] = self.target_positions[i]
            
            # Check if trajectory complete
            if all(abs(self.current_positions[i] - self.target_positions[i]) < 0.001 
                   for i in range(6)):
                self.trajectory_active = False
                self.get_logger().info('Simulated trajectory execution complete')
        
        # Create and publish JointState message
        joint_state = JointState()
        joint_state.header = Header()
        joint_state.header.stamp = self.get_clock().now().to_msg()
        
        joint_state.name = [
            'joint_1',
            'joint_2', 
            'joint_3',
            'joint_4',
            'joint_5',
            'joint_6'
        ]
        joint_state.position = self.current_positions
        
        self.joint_state_pub.publish(joint_state)
        
        # Log at reduced rate to avoid spam
        if hasattr(self, '_log_counter'):
            self._log_counter += 1
        else:
            self._log_counter = 0
        
        if self._log_counter % 20 == 0:  # Log every 2 seconds at 10Hz
            pos_str = ', '.join([f'{p:.3f}' for p in self.current_positions])
            self.get_logger().info(f'Joint states: [{pos_str}]')


def main(args=None):
    rclpy.init(args=args)
    node = MockNiryoTCPBridge()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
