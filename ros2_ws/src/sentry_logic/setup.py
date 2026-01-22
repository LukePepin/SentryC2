from setuptools import find_packages, setup

package_name = 'sentry_logic'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='lukepepin@outlook.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'cyclic_server = sentry_logic.cyclic_action_server:main',
            'niryo_tcp_bridge = sentry_logic.niryo_tcp_bridge:main',
            'test_arm_trajectory = sentry_logic.test_arm_trajectory:main',
            'network_sniffer = sentry_logic.network_sniffer:main',
        ],
    },
)
