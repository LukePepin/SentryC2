### Task: Set up SentryC2 Docker dev container on Windows

### Context

- Repo: https://github.com/LukePepin/SentryC2.git
- The repo contains a `docker-compose.yml` (uses `network_mode: host` for Linux)
  and a `docker-compose.windows.yml` override (uses bridge networking + port mappings
  for Docker Desktop). Both files are already committed.
- A `.devcontainer/devcontainer.json` exists that references `docker-compose.yml`.
- ROS2 Humble container based on `ros:humble-ros-base`.
- Unity ROS-TCP-Endpoint uses ports 10000 and 10005.

### Requirements

1. Verify Docker Desktop is installed with WSL 2 backend enabled.
2. Clone the repo INSIDE WSL 2 (not on /mnt/c/) with --recurse-submodules.
3. Build and start the container using BOTH compose files:
   `docker compose -f docker-compose.yml -f docker-compose.windows.yml build --no-cache`
   `docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d`
4. After the container is running, exec into it and run:
   `source /opt/ros/humble/setup.bash && cd /workspace/ros2_ws && colcon build --symlink-install`
5. Verify: container is running, /workspace is mounted, `ros2 topic list` works.

### Constraints

- Do NOT clone onto the Windows NTFS filesystem (/mnt/c/). Volume mount
  performance is 10-50x slower on NTFS. Clone into ~/SentryC2 inside WSL.
- The base docker-compose.yml uses `network_mode: host` which is UNSUPPORTED
  on Docker Desktop. The windows override switches to bridge mode. Always use
  both files together with -f flags.
- Run each step and confirm output before proceeding to the next.
