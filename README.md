# SentryC2: Edge-First Resiliency Framework
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-green)](https://docs.ros.org/en/humble/)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)]()
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue)](https://github.com/lpep64/SentryC2/pkgs/container/sentryc2)

## 1. Problem Statement
Current Industry 4.0 architectures rely on centralized Identity Providers (IdP). When backhaul connectivity fails, authorization leases expire, triggering a "Kill Switch" that halts production regardless of local hardware status.

**SentryC2** replaces this with an **Edge-First** mesh topology, utilizing local Zero-Knowledge Proofs (ZKP) to ensure sub-500ms recovery during network blackouts.

## 2. Architecture
![Kill Switch vs Edge Mesh](docs/architecture_diagram.png)

*Figure 1: Comparison of Cloud-First Fragility vs. SentryC2 Edge Mesh*

## 3. Quick Start (Docker)
This repository is containerized to ensure full reproducibility across Thinkmate (Dev) and Jetson Orin (Edge) hardware.

### Prerequisites
- Docker Engine (Linux)
- Unity Hub 2022.3+ (Simulation)

### Installation

#### Option 1: Pull from GitHub Container Registry (Recommended)
```bash
# Pull the pre-built image
docker pull ghcr.io/lpep64/sentryc2:alpha

# Run with docker-compose
docker-compose up -d
```

#### Option 2: Build Locally
```bash
# 1. Clone the repository
git clone https://github.com/lpep64/SentryC2.git
cd SentryC2

# 2. Build the Edge-First OS
docker build -t sentry-c2:alpha .

# 3. Run Development Container
docker-compose up -d

# 4. Attach to container
docker exec -it sentry-c2-dev /bin/bash
```

### VS Code Integration
The Docker extension in VS Code will automatically detect your containers. If you don't see them:

1. **Fix Docker Permissions** (one-time setup):
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker  # or log out and back in
   ```

2. **Reload VS Code** to refresh the Docker extension

3. **Right-click container** in Docker sidebar to:
   - Attach shell
   - View logs
   - Stop/Start container
```

## 4. Roadmap (Spring 2026)
*   **Jan 2026:** Environment Setup & Digital Twin Alpha
*   **Feb 2026:** Hardware Interface (Raspberry Pi / Arduino BLE)
*   **Mar 2026:** Chaos Engineering (Packet Loss & ARP Poisoning)
*   **Apr 2026:** Final Integration & Thesis Defense

## License
Copyright 2026 Luke Pepin.
Licensed under the Apache License, Version 2.0.
```
