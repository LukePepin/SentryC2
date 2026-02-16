import rclpy

from sentry_logic.cyclic_action_server import CyclicActionServer


def test_auth_expiry_default_is_slow():
    rclpy.init()
    node = CyclicActionServer()
    try:
        assert node.auth_expiry_seconds >= 120.0
    finally:
        node.destroy_node()
        rclpy.shutdown()
