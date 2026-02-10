import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_srvs.srv import Trigger
import time
import hashlib


class SupervisorNode(Node):
    def __init__(self):
        super().__init__('supervisor_node')
        
        self.declare_parameter('auth_enabled', True)
        self.declare_parameter('zkp_delay_ms', 0.67)
        self.declare_parameter('num_threads', 4)
        
        self.auth_enabled = self.get_parameter('auth_enabled').value
        self.zkp_delay = self.get_parameter('zkp_delay_ms').value / 1000.0
        self.num_threads = self.get_parameter('num_threads').value
        
        # CRITICAL: ReentrantCallbackGroup allows parallel callback execution
        self.callback_group = ReentrantCallbackGroup()
        
        self.auth_service = self.create_service(
            Trigger,
            '/supervisor/authenticate',
            self.handle_authentication,
            callback_group=self.callback_group
        )
        
        self.auth_count = 0
        self.start_time = time.time()
        
        self.get_logger().info(
            f'🔐 Supervisor Node ONLINE (MULTITHREADED EXECUTOR)\n'
            f'   - Service: /supervisor/authenticate\n'
            f'   - Auth Enabled: {self.auth_enabled}\n'
            f'   - ZKP Delay: {self.zkp_delay*1000:.2f}ms\n'
            f'   - Architecture: MultiThreadedExecutor (num_threads={self.num_threads})'
        )
    
    def handle_authentication(self, request, response):
        req_start = time.time()
        
        if not self.auth_enabled:
            response.success = False
            response.message = "Authentication disabled"
            return response
        
        # Execute ZKP verification directly (executor handles parallelism)
        time.sleep(self.zkp_delay)
        data = b"zkp_verification_" + str(time.time()).encode()
        for _ in range(10):
            data = hashlib.sha256(data).digest()
        
        self.auth_count += 1
        processing_time = (time.time() - req_start) * 1000
        
        response.success = True
        response.message = f"AUTH_OK|count={self.auth_count}|latency={processing_time:.2f}ms"
        
        if self.auth_count % 10 == 0:
            uptime = time.time() - self.start_time
            rate = self.auth_count / uptime
            self.get_logger().info(
                f'📊 [{self.auth_count}] auths, {rate:.1f} req/s, {processing_time:.2f}ms'
            )
        
        return response


def main(args=None):
    rclpy.init(args=args)
    node = SupervisorNode()
    
    # CRITICAL: Use MultiThreadedExecutor for parallel callback processing
    executor = MultiThreadedExecutor(num_threads=node.num_threads)
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        uptime = time.time() - node.start_time
        node.get_logger().info(
            f'\n🔒 Supervisor shutting down\n'
            f'   Total auths: {node.auth_count}\n'
            f'   Uptime: {uptime:.1f}s'
        )
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()