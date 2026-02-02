# SentryC2 Requirements Specification
## DO-178C Certification Support Document

**Classification:** Internal - Federal Disclosure Candidate
**Version:** 0.1-alpha
**Last Updated:** 2026-02-02
**Prepared By:** Configuration Management (CM)

---

## Executive Summary

SentryC2 is a safety-critical edge-first robotics framework designed to maintain operational continuity during network blackouts. This document establishes traceability between:
1. **Functional Requirements** (What the system must do)
2. **Safety Requirements** (How failures are mitigated)
3. **Design Constraints** (Environmental/hardware limits)
4. **Test Cases** (Verification methods)

All requirements are tagged with unique identifiers (REQ-XXX) for traceability matrix correlation.

---

## 1. Functional Requirements

### REQ-001: Edge-First Mesh Topology
**Category:** Architectural
**Priority:** CRITICAL
**Statement:** The system shall operate in a decentralized mesh topology where edge nodes (Pi 4, Nano 33 BLE) maintain local authorization independent of cloud connectivity.

**Rationale:** Industry 4.0 systems fail when backhaul connectivity drops. SentryC2 eliminates this single point of failure.
**Test Method:** [TC-001] Network isolation test (disconnect WAN, verify local auth succeeds)
**Verification:** Commit hash(es) in CHANGELOG.md

---

### REQ-002: Sub-500ms Recovery on Network Blackout
**Category:** Performance
**Priority:** CRITICAL
**Statement:** Upon network disconnection, the system shall resume operation with valid authorization within 500ms.

**Rationale:** Safety-critical robotics require predictable latency. 500ms is baseline for H1 hypothesis.
**Test Method:** [TC-002] Packet loss injection (use tc/netem), measure recovery time
**Metrics:** Recovery latency histogram, p95 < 500ms, p99 < 750ms
**Acceptance Criteria:** 95% of recovery events < 500ms over 1000 trials

---

### REQ-003: Zero-Knowledge Proof Authentication
**Category:** Security
**Priority:** CRITICAL
**Statement:** The system shall authenticate local operations using non-interactive zero-knowledge proofs (NIZKs) without transmitting secrets.

**Rationale:** Bayh-Dole compliance + military robotics hardening
**Implementation:** Schnorr protocol via micro-ecc or libsodium
**Test Method:** [TC-003] Cryptographic oracle test; verify prover cannot forge proofs
**Verification:** Arduino Nano 33 BLE (zkp_auth_prover.py) + verifier (zkp_auth_verifier.py)

---

### REQ-004: Docker Reproducibility
**Category:** Infrastructure
**Priority:** HIGH
**Statement:** All code and dependencies shall be containerized in Docker. No development on host machine shall be required. Dockerfile shall produce bitwise-identical builds.

**Rationale:** Federal disclosure requires reproducible builds for audit trails.
**Test Method:** [TC-004] Build docker image twice with same Dockerfile; verify SHA256(image) identity
**Acceptance Criteria:** Reproducible build passes on Linux + Windows (WSL2)

---

### REQ-005: ROS2 Middleware Integration
**Category:** Integration
**Priority:** HIGH
**Statement:** System shall communicate via ROS2 Humble with DDS middleware (rmw_cyclonedds_cpp).

**Rationale:** Standard robotics middleware ensures vendor independence
**Test Method:** [TC-005] ROS2 topic subscription/publication latency; verify DDS QoS compliance
**Acceptance Criteria:** Latency p99 < 100ms on local network

---

### REQ-006: Unity Digital Twin Synchronization
**Category:** Integration
**Priority:** MEDIUM
**Statement:** Unity simulator shall maintain real-time joint state synchronization with physical Niryo Ned2 via ROS-TCP-Endpoint bridge.

**Rationale:** Enables simulation-to-reality transfer without firmware recompilation
**Test Method:** [TC-006] Send trajectory to physical robot; verify Unity digital twin tracks positions
**Acceptance Criteria:** Joint position error < 5° over 60-second test trajectory

---

### REQ-007: Physical Robot Control (Niryo Ned2)
**Category:** Hardware Integration
**Priority:** MEDIUM
**Statement:** System shall interface with Niryo Ned2 manipulator (ROS1 Noetic) via TCP bridge; support trajectory execution, joint state monitoring, and auto-calibration.

**Rationale:** H1 hypothesis requires physical validation; Niryo is proof-of-concept platform
**Dependencies:** PyNiryo2 >= 1.0.0, roslibpy < 2.0.0
**Test Method:** [TC-007] Execute 62-second test trajectory; verify all 6 DOF execute correctly
**Acceptance Criteria:** Motion commands executed within 100ms latency, zero calibration failures

---

## 2. Safety Requirements (DO-254 Alignment)

### SAF-001: Fail-Safe on Crypto Verification Failure
**Category:** Safety-Critical
**Statement:** If ZKP verification fails, the system shall immediately halt robot motion and log the event.

**Rationale:** Prevents unauthorized motion; core safety property
**Test Method:** [TC-008] Inject malformed proof; verify robot halts within 10ms
**Acceptance Criteria:** 100% halt rate on verification failure

---

### SAF-002: No Untraced Command Execution
**Category:** Audit Trail
**Statement:** Every robot command shall be logged with timestamp, proof hash, and operator identity (or "edge-autonomous").

**Rationale:** Federal auditing requirement for safety-critical systems
**Test Method:** [TC-009] Execute 10 commands; verify log contains all entries with no gaps
**Acceptance Criteria:** Log completeness = 100%

---

### SAF-003: Thermal Management (Pi 4)
**Category:** Environmental
**Statement:** System shall monitor Pi 4 CPU temperature. If temp > 80°C for > 30s, gracefully shutdown robot and raise alert.

**Rationale:** Resource-constrained embedded systems require thermal limits
**Test Method:** [TC-010] Stress test via `stress-ng`; verify shutdown triggers at 80°C
**Acceptance Criteria:** Graceful shutdown within 1s of threshold breach

---

## 3. Design Constraints

### CON-001: Hardware Specifications
| Component | Spec |
|-----------|------|
| Supervisor | Raspberry Pi 4 (1.5 GHz ARM Cortex-A72, 4GB RAM) |
| Edge Compute | Arduino Nano 33 BLE (64 MHz ARM Cortex-M4, 256KB SRAM) |
| Thermal Limit | 80°C |
| Memory Budget (Robot Control) | < 100MB |

---

### CON-002: Network Assumptions
- **Local Network:** 192.168.0.0/24 (Ethernet or WiFi 5GHz)
- **No WAN Dependency:** System operates autonomously on network loss
- **DDS Multicast:** ROS2 DDS requires multicast support
- **Latency Budget:** Pi↔Nano33: < 100ms

---

### CON-003: Library Compliance
**Approved Dependencies:**
- ROS2 Humble (Ubuntu 22.04)
- micro-ecc (cryptography on Nano33)
- libsodium (cryptography on Pi)
- PyNiryo2 (robot TCP interface)
- Unity 2022.3+ (simulation only)

**Rejected:**
- GPL (viral licensing, Bayh-Dole risk)
- Custom crypto (use audited libraries instead)

---

## 4. Traceability Matrix

| REQ ID | Title | Type | Priority | Test Case | Status |
|--------|-------|------|----------|-----------|--------|
| REQ-001 | Edge-First Mesh | Architecture | CRITICAL | TC-001 | Not Started |
| REQ-002 | Sub-500ms Recovery | Performance | CRITICAL | TC-002 | Not Started |
| REQ-003 | ZKP Authentication | Security | CRITICAL | TC-003 | Partial (code exists) |
| REQ-004 | Docker Reproducibility | Infrastructure | HIGH | TC-004 | In Progress |
| REQ-005 | ROS2 Integration | Integration | HIGH | TC-005 | Partial (running) |
| REQ-006 | Unity Sync | Integration | MEDIUM | TC-006 | Partial (running) |
| REQ-007 | Niryo Control | Hardware | MEDIUM | TC-007 | Partial (running) |
| SAF-001 | Crypto Fail-Safe | Safety | CRITICAL | TC-008 | Not Started |
| SAF-002 | Command Audit Trail | Audit | CRITICAL | TC-009 | Not Started |
| SAF-003 | Thermal Management | Environmental | HIGH | TC-010 | Not Started |

---

## 5. Next Steps (Roadmap)

### Phase 1: Certification Foundation (Feb 2026)
- [ ] Finalize all test cases (TC-001 through TC-010)
- [ ] Establish automated CI/CD pipeline
- [ ] Create pre-commit hooks to block secrets

### Phase 2: H1 Hypothesis Validation (Mar 2026)
- [ ] Execute kill switch experiments (network isolation)
- [ ] Validate ZKP performance on Nano33 BLE
- [ ] Measure recovery latency with packet loss injection

### Phase 3: Final Certification (Apr 2026)
- [ ] Full DO-178C audit trail
- [ ] Cryptographic oracle testing
- [ ] Federal disclosure review

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1-alpha | 2026-02-02 | CM | Initial requirements extraction from architecture |
| | | | |

---

**Approvals:**
- Configuration Manager: ___________________
- Safety Review: ___________________
- Thesis Advisor: ___________________

