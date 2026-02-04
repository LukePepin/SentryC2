import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

# Hardcoded home and target joint configurations (rad)
POSE_HOME = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
POSE_TARGET = [1.57, -0.7, -0.7, 0.0, -0.5, 0.0]


class CyclicActionServer(Node):
    def __init__(self) -> None:
        super().__init__('sentry_logic_node')
        self.publisher_ = self.create_publisher(JointState, 'joint_states', 10)
        self.timer = self.create_timer(2.0, self.execute_cycle)
        self.state = 'HOME'  # HOME -> TARGET -> HOME
        self.auth_token_valid = True
        self.get_logger().info('SentryC2 Logic Node Started. Mode: CYCLIC.')

        # Kill Switch: Flip auth_token_valid after configurable delay
        self.declare_parameter('auth_expiry_seconds', 120.0)
        self.auth_expiry_seconds = float(self.get_parameter('auth_expiry_seconds').value)
        if self.auth_expiry_seconds < 1.0:
            self.auth_expiry_seconds = 1.0
        self.kill_switch_timer = self.create_timer(self.auth_expiry_seconds, self.trigger_kill_switch)
        self.get_logger().info(
            f'Kill switch armed: auth will expire in {self.auth_expiry_seconds:.1f}s'
        )

    def execute_cycle(self) -> None:
        if not self.auth_token_valid:
            self.get_logger().error('AUTH EXPIRED. SAFETY STOP TRIGGERED.')
            return

        msg = JointState()
        msg.name = [
            'joint_1',
            'joint_2',
            'joint_3',
            'joint_4',
            'joint_5',
            'joint_6',
        ]

        if self.state == 'HOME':
            self.get_logger().info('Status: Moving to TARGET...')
            self.publish_trajectory(POSE_HOME, POSE_TARGET)
            self.state = 'TARGET'
        elif self.state == 'TARGET':
            self.get_logger().info('Status: Returning HOME...')
            self.publish_trajectory(POSE_TARGET, POSE_HOME)
            self.state = 'HOME'

    def trigger_kill_switch(self) -> None:
        """Kill switch callback - simulates authorization expiration."""
        self.auth_token_valid = False
        self.get_logger().warn('⚠️ KILL SWITCH ACTIVATED: Authorization token expired!')
        self.kill_switch_timer.cancel()  # Only trigger once

    def publish_trajectory(self, start_pose, end_pose) -> None:
        steps = 100
        msg = JointState()
        msg.name = [
            'joint_1',
            'joint_2',
            'joint_3',
            'joint_4',
            'joint_5',
            'joint_6',
        ]

        for i in range(steps):
            if not self.auth_token_valid:
                break

            t = i / float(steps)
            current_joints = []
            for j in range(6):
                val = (1 - t) * start_pose[j] + t * end_pose[j]
                current_joints.append(val)

            msg.position = current_joints
            self.publisher_.publish(msg)
            time.sleep(0.05)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CyclicActionServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
