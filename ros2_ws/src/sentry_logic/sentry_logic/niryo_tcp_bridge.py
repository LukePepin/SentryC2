#!/usr/bin/env python3
"""
Niryo Ned2 TCP Bridge Node
Connects to Niryo Ned2 via PyNiryo2 and publishes joint states to ROS2
Subscribes to trajectory commands and executes them on the robot
"""
from pyniryo2 import *
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from std_msgs.msg import Header
import threading


class NiryoTCPBridge(Node):
    def __init__(self):
        super().__init__('niryo_tcp_bridge')
        
        # Parameters
        self.declare_parameter('robot_ip', '192.168.0.244')
        self.declare_parameter('publish_rate', 10.0)  # Hz
        
        self.robot_ip = self.get_parameter('robot_ip').value
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
        
        # Niryo robot client
        self.robot = None
        self.connected = False
        self.executing_trajectory = False
        self.trajectory_lock = threading.Lock()
        
        # Timer for publishing
        self.timer = self.create_timer(
            1.0 / self.publish_rate,
            self.timer_callback
        )
        
        self.get_logger().info(f'Niryo TCP Bridge initialized')
        self.get_logger().info(f'Connecting to robot at {self.robot_ip}')
        
        self.connect_to_robot()
    
    def connect_to_robot(self):
        """Establish connection to the robot using PyNiryo2"""
        try:
            self.robot = NiryoRobot(self.robot_ip)
            self.robot.arm.calibrate_auto()
            self.connected = True
            self.get_logger().info('Successfully connected to Niryo robot!')
            self.get_logger().info(f'Robot info: {self.robot.arm.get_joints()}')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to robot: {e}')
            self.connected = False
    
    def trajectory_callback(self, msg):
        """Handle incoming trajectory commands"""
        if not self.connected or self.robot is None:
            self.get_logger().error('Cannot execute trajectory: Robot not connected')
            return
        
        if self.executing_trajectory:
            self.get_logger().warn('Trajectory already in progress, ignoring new command')
            return
        
        # Execute trajectory in a separate thread to avoid blocking
        trajectory_thread = threading.Thread(
            target=self._execute_trajectory,
            args=(msg,)
        )
        trajectory_thread.daemon = True
        trajectory_thread.start()
    
    def _execute_trajectory(self, msg):
        """Execute trajectory on the physical robot"""
        with self.trajectory_lock:
            self.executing_trajectory = True
            
            try:
                self.get_logger().info(f'Executing trajectory with {len(msg.points)} points')
                
                # Execute each point in the trajectory
                for i, point in enumerate(msg.points):
                    if len(point.positions) != 6:
                        self.get_logger().error(f'Invalid trajectory point {i}: expected 6 joints, got {len(point.positions)}')
                        continue
                    
                    # Calculate duration for this segment
                    if i == 0:
                        duration = point.time_from_start.sec + point.time_from_start.nanosec / 1e9
                    else:
                        prev_time = msg.points[i-1].time_from_start.sec + msg.points[i-1].time_from_start.nanosec / 1e9
                        curr_time = point.time_from_start.sec + point.time_from_start.nanosec / 1e9
                        duration = curr_time - prev_time
                    
                    self.get_logger().info(f'Moving to point {i+1}/{len(msg.points)}: {point.positions} (duration: {duration}s)')
                    
                    # Move the robot to the target position
                    # PyNiryo2 expects a list of joint positions, not unpacked arguments
                    self.robot.arm.move_joints(list(point.positions))
                    
                self.get_logger().info('Trajectory execution completed successfully')
                
            except Exception as e:
                self.get_logger().error(f'Error executing trajectory: {e}')
                
            finally:
                self.executing_trajectory = False
    
    def timer_callback(self):
        """Periodically publish joint states"""
        if not self.connected or self.robot is None:
            self.get_logger().warn('Not connected to robot, attempting reconnect...')
            self.connect_to_robot()
            return
        
        try:
            # Get joint positions
            joints = self.robot.arm.get_joints()
            
            # Create and publish JointState message
            joint_state = JointState()
            joint_state.header = Header()
            joint_state.header.stamp = self.get_clock().now().to_msg()
            
            # Niryo Ned2 has 6 joints
            joint_state.name = [
                'joint_1',
                'joint_2', 
                'joint_3',
                'joint_4',
                'joint_5',
                'joint_6'
            ]
            joint_state.position = joints
            
            self.joint_state_pub.publish(joint_state)
            self.get_logger().info(f'Published joint states: {joints}', throttle_duration_sec=2.0)
            
        except Exception as e:
            self.get_logger().error(f'Error getting joint states: {e}')
            self.connected = False
    
    def destroy_node(self):
        """Cleanup on shutdown"""
        if self.robot:
            try:
                self.robot.end()
            except:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = NiryoTCPBridge()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
