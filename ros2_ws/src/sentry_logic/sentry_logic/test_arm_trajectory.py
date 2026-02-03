import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import time

class ArmTestNode(Node):
    def __init__(self):
        super().__init__('arm_test_node')
        
        # TOPIC: This targets the Niryo Driver (The Wrapper)
        # Ensure this matches the topic found in 'ros2 topic list'
        self.publisher_ = self.create_publisher(
            JointTrajectory, 
            '/niryo_robot_follow_joint_trajectory_controller/follow_joint_trajectory', 
            10
        )
        
        # 1 Second startup delay to ensure connection
        time.sleep(1)
        self.move_robot()

    def move_robot(self):
        msg = JointTrajectory()
        
        # CRITICAL: These names must match the robot's internal ROS1 names exactly
        msg.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6']

        # Point 1: Home Position (All Zeros)
        point1 = JointTrajectoryPoint()
        point1.positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        point1.time_from_start.sec = 3

        # Point 2: Base Rotation + Shoulder Lift
        point2 = JointTrajectoryPoint()
        point2.positions = [0.8, -0.5, 0.3, 0.0, 0.0, 0.0]
        point2.time_from_start.sec = 10

        # Point 3: Test Wrist Pitch (Joint 5)
        point3 = JointTrajectoryPoint()
        point3.positions = [0.8, -0.5, 0.3, 0.0, 0.6, 0.0]
        point3.time_from_start.sec = 17

        # Point 4: Test Wrist Roll (Joint 4) + Wrist Rotation (Joint 6)
        point4 = JointTrajectoryPoint()
        point4.positions = [0.8, -0.5, 0.3, 0.7, 0.6, 0.8]
        point4.time_from_start.sec = 24

        # Point 5: Sentry Scan Position - High Alert
        point5 = JointTrajectoryPoint()
        point5.positions = [-0.6, -0.3, -0.4, 0.0, 0.5, 0.0]
        point5.time_from_start.sec = 32

        # Point 6: Full Base Rotation with Wrist Test
        point6 = JointTrajectoryPoint()
        point6.positions = [-0.6, -0.3, -0.4, -0.5, 0.5, 1.2]
        point6.time_from_start.sec = 40

        # Point 7: Extended Reach Position
        point7 = JointTrajectoryPoint()
        point7.positions = [0.3, 0.4, -0.8, 0.3, -0.4, -0.6]
        point7.time_from_start.sec = 48

        # Point 8: Compact Position
        point8 = JointTrajectoryPoint()
        point8.positions = [0.0, -0.8, 0.5, 0.0, 0.3, 0.0]
        point8.time_from_start.sec = 55

        # Point 9: Return Home
        point9 = JointTrajectoryPoint()
        point9.positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        point9.time_from_start.sec = 62

        # Pack the message
        msg.points = [point1, point2, point3, point4, point5, point6, point7, point8, point9]

        self.get_logger().info('Sending 62-second Full Joint Test Trajectory to Physical Robot...')
        self.get_logger().info('Testing: Base, Shoulder, Elbow, Wrist Roll, Wrist Pitch, Wrist Rotation')
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ArmTestNode()
    # Run once then exit
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
