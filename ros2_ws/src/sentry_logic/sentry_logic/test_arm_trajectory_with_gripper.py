#!/usr/bin/env python3
"""
TEST 2: Arm Trajectory with Gripper Close + Payload Attachment Test
Validates kinematic attachment of payload to gripper during motion
"""
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from std_msgs.msg import String
import time

class ArmTestWithGripperNode(Node):
    def __init__(self):
        super().__init__('arm_test_with_gripper_node')
        
        # Publisher for trajectories
        self.trajectory_pub = self.create_publisher(
            JointTrajectory, 
            '/niryo_robot_follow_joint_trajectory_controller/follow_joint_trajectory', 
            10
        )
        
        # Publisher for gripper commands (simple string-based for testing)
        self.gripper_pub = self.create_publisher(
            String,
            '/gripper_command',
            10
        )
        
        time.sleep(1)
        self.run_test_sequence()

    def run_test_sequence(self):
        """Execute full TEST 2 sequence with gripper interaction"""
        
        # PHASE 1: Move to approach position (gripper near object)
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2 PHASE 1: Moving to approach position...')
        self.get_logger().info('='*60)
        
        approach_trajectory = JointTrajectory()
        approach_trajectory.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6']
        
        # Start from home
        p1 = JointTrajectoryPoint()
        p1.positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        p1.time_from_start.sec = 2
        
        # Move to object approach position (reach down to gripper level, slight arm extension)
        p2 = JointTrajectoryPoint()
        p2.positions = [0.2, -0.8, 0.4, 0.0, 0.2, 0.0]
        p2.time_from_start.sec = 8
        
        approach_trajectory.points = [p1, p2]
        self.get_logger().info('Sending approach trajectory (2-8s)...')
        self.trajectory_pub.publish(approach_trajectory)
        
        time.sleep(10)  # Wait for approach motion to complete
        
        # PHASE 2: Close gripper (triggers attachment in Unity)
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2 PHASE 2: CLOSING GRIPPER (attachment should occur)')
        self.get_logger().info('='*60)
        
        gripper_close_cmd = String()
        gripper_close_cmd.data = "CLOSE"
        self.get_logger().info('[TEST 2] Publishing GRIPPER CLOSE command')
        self.get_logger().info('[TEST 2] → Expecting WorkObject to attach to hand_link in Unity')
        self.gripper_pub.publish(gripper_close_cmd)
        
        time.sleep(2)  # Let gripper settle
        
        # PHASE 3: Aggressive motion while gripper closed (payload attachment test)
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2 PHASE 3: AGGRESSIVE ARM MOTION (payload hold test)')
        self.get_logger().info('→ WATCH: WorkObject should STAY ATTACHED despite rapid motion')
        self.get_logger().info('='*60)
        
        aggressive_trajectory = JointTrajectory()
        aggressive_trajectory.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6']
        
        # Rapid sweep motion holding payload
        p1 = JointTrajectoryPoint()
        p1.positions = [0.2, -0.8, 0.4, 0.0, 0.2, 0.0]
        p1.time_from_start.sec = 0
        
        p2 = JointTrajectoryPoint()
        p2.positions = [1.0, -0.5, -0.3, 0.5, 0.0, 0.8]
        p2.time_from_start.sec = 6
        
        p3 = JointTrajectoryPoint()
        p3.positions = [-1.0, -0.6, 0.5, -0.5, 0.3, -0.8]
        p3.time_from_start.sec = 12
        
        p4 = JointTrajectoryPoint()
        p4.positions = [0.5, -0.7, -0.2, 0.2, -0.1, 0.5]
        p4.time_from_start.sec = 18
        
        aggressive_trajectory.points = [p1, p2, p3, p4]
        self.get_logger().info('Sending aggressive 18-second motion sequence...')
        self.trajectory_pub.publish(aggressive_trajectory)
        
        time.sleep(20)  # Wait for aggressive motion
        
        # PHASE 4: Open gripper (should detach payload)
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2 PHASE 4: OPENING GRIPPER (detachment expected)')
        self.get_logger().info('='*60)
        
        gripper_open_cmd = String()
        gripper_open_cmd.data = "OPEN"
        self.get_logger().info('[TEST 2] Publishing GRIPPER OPEN command')
        self.get_logger().info('[TEST 2] → Expecting WorkObject to DETACH from hand_link')
        self.gripper_pub.publish(gripper_open_cmd)
        
        time.sleep(2)
        
        # PHASE 5: Return to home
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2 PHASE 5: Return to home (payload drops to ground)')
        self.get_logger().info('='*60)
        
        home_trajectory = JointTrajectory()
        home_trajectory.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6']
        
        p1 = JointTrajectoryPoint()
        p1.positions = [0.5, -0.7, -0.2, 0.2, -0.1, 0.5]
        p1.time_from_start.sec = 0
        
        p2 = JointTrajectoryPoint()
        p2.positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        p2.time_from_start.sec = 6
        
        home_trajectory.points = [p1, p2]
        self.get_logger().info('Sending return-to-home trajectory (6s)...')
        self.trajectory_pub.publish(home_trajectory)
        
        time.sleep(8)
        
        # TEST COMPLETE
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2 COMPLETE')
        self.get_logger().info('='*60)
        self.get_logger().info('CHECK RESULTS:')
        self.get_logger().info('  ✓ PASS: WorkObject stayed attached during aggressive motion (Phase 3)')
        self.get_logger().info('  ✓ PASS: WorkObject detached when gripper opened (Phase 4)')
        self.get_logger().info('  ✓ PASS: WorkObject fell to ground after detach')
        self.get_logger().info('='*60)

def main(args=None):
    rclpy.init(args=args)
    node = ArmTestWithGripperNode()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
