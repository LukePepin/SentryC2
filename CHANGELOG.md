# Changelog

All notable changes to SentryC2 will be documented in this file per [Keep a Changelog](http://keepachangelog.com/) and [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## Version Tagging Policy
- **v0.1-alpha** → H0 Baseline (Environment setup & simulation)
- **v0.2-beta** → H1 Hypothesis (Kill Switch behavior & ZKP auth)
- **v1.0.0** → H2 & Thesis Defense (Production-ready certification)

All commits to `main` REQUIRE CHANGELOG updates in the [Unreleased](#unreleased) section.

---

## [Unreleased]

### Added
- Initial structure for DO-178C certification artifacts
- PSAC (Plan for Software Aspects of Certification)
- SVP (Software Verification Plan)
- Requirements traceability matrix (docs/REQUIREMENTS.md)
- Federal disclosure checklist (docs/FEDERAL_DISCLOSURE_CHECKLIST.md)
- Hardened .gitignore with Bayh-Dole compliance safeguards
- Docker reproducibility validation (deterministic builds)

### Changed
- Enhanced .gitignore to prevent Library/, __pycache__, build/, install/, log/ commits
- Added .env and secrets/ patterns to prevent credential leakage

### Fixed
- None yet

### Security
- **CRITICAL**: Implemented exclusion patterns for credential files (.env, *.key, *.pem)
- Validated Apache 2.0 license (no GPL/viral code)

---

## [v0.1.1-bridge] - 2026-01-22

### Added
- Niryo TCP Bridge Node for bidirectional ROS1 ↔ ROS2 communication
- Joint states publisher (10 Hz) to `/joint_states` topic
- Trajectory command subscriber for robot control
- Auto-calibration on robot connection
- PyNiryo2 integration for physical Niryo Ned2 robot

### Changed
- Downgraded roslibpy to <2.0.0 for PyNiryo2 compatibility
- Updated README with physical robot integration instructions

### Fixed
- Resolved actionlib module unavailability in roslibpy 2.0+
- Fixed thread-safe command execution during trajectories

### Verified
- ✅ Ubuntu 22.04 LTS (Docker)
- ✅ ROS2 Humble middleware (rmw_cyclonedds_cpp)
- ✅ Physical robot control (Niryo Ned2 @ 192.168.0.244)

---

## [v0.1-alpha] - 2026-01-12

### Added
- Initial SentryC2 repository structure
- Docker containerization (Ubuntu 22.04, ROS2 Humble)
- Unity-ROS2 integration via ROS-TCP-Endpoint
- Digital twin simulator (Unity 2022.3)
- Arduino Nano 33 BLE ZKP prover skeleton
- Niryo Ned2 URDF import and physics simulation
- Initial architecture documentation

### Infrastructure
- Docker Compose for dev environment
- VS Code Dev Container configuration
- GitHub Actions CI/CD template (pending)

### Security Baseline
- Apache 2.0 license (Bayh-Dole compliant)
- No proprietary/GPL dependencies

---

## Certification Compliance

### DO-178C Alignment
All entries in this changelog MUST map to:
1. **Requirements** (docs/REQUIREMENTS.md)
2. **Test Cases** (tests/traceability_matrix.csv)
3. **Code Changes** (commit hash)

Example format:
```
### Added
- Feature X [REQ-001] via commit abc1234
```

### Bayh-Dole Compliance
- No university proprietary keys/credentials in commits ✓
- All external libraries documented in requirements ✓
- License compatibility verified (Apache 2.0) ✓

---

## Contributing

When creating a PR to `main`:
1. Update CHANGELOG.md in the [Unreleased](#unreleased) section
2. Add `[REQ-XXX]` tags for traceability
3. Include commit hash reference
4. Ensure no secrets are committed (pre-commit hooks pending)

---

## References
- [SentryC2 Architecture](docs/architecture_diagram.png)
- [ZKP Deployment Guide](docs/zkp_deployment_guide.md)
- [Development Log (Jan 2026)](docs/Jan22.md)
