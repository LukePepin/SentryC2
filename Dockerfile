# 1. Base Image: ROS2 Humble (LTS)
# Matches Thesis ADR 001 for long-term stability [Source 60, 62]
FROM ros:humble-ros-base

# 2. System Dependencies (The "Connective Tissue")
# git: to clone the bridge
# net-tools: for ifconfig (debugging network) [Source 63]
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# 3. Chaos & Security Libraries (The "Munitions")
# scapy: Required for Week 9 ARP Poisoning/Packet Sniffing [Source 66]
# cryptography: Required for Week 7 ECC/ZKP implementation [Source 59]
# numpy: Required for Trust Score (Bayesian) math [Source 76]
RUN pip3 install scapy cryptography numpy

# 4. Setup ROS Workspace Structure
WORKDIR /root/ros2_ws/src

# 5. Install ROS-TCP-Endpoint as Python Package
# The Unity bridge can work as a standalone Python package without building
# This avoids the ROS1/ROS2 incompatibility issue
COPY ros2_ws/src/ROS-TCP-Endpoint /root/ros2_ws/src/ROS-TCP-Endpoint
RUN pip3 install -e /root/ros2_ws/src/ROS-TCP-Endpoint

# 6. Setup Workspace (Create Empty Build for Future Packages)
WORKDIR /root/ros2_ws

# 7. Automate Sourcing
# Prevents "command not found" errors when you log in
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "source /root/ros2_ws/install/setup.bash" >> ~/.bashrc