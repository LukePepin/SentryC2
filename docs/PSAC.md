# PSAC: Plan for Software Aspects of Certification
## SentryC2 Edge-First Robotics Framework

**Document Classification:** Internal - Federal Disclosure Candidate
**Version:** 0.1-alpha  
**Date:** 2026-02-02  
**Prepared by:** Configuration Management (CM)  
**Standard:** DO-178C Level A (Safety-Critical)  

---

## Executive Summary

This PSAC establishes the software development lifecycle (SDLC), verification & validation (V&V) strategy, configuration management (CM), and certification approach for **SentryC2**: a military robotics framework that maintains operational continuity during network blackouts using edge-first zero-knowledge proof authentication.

**Scope:**
- ROS2 Humble workspace (Supervisor: Raspberry Pi 4)
- Arduino Nano 33 BLE (Edge compute: ZKP prover)
- Unity 2022.3 simulation (Digital twin)
- Niryo Ned2 manipulator (H1 proof-of-concept platform)

**Target Certification:** DO-254/178C Level A (Catastrophic failure risk: loss of operational continuity)

---

## 1. Software Lifecycle Processes

### 1.1 Development Phases (Thesis Roadmap)

#### Phase H0: Baseline & Environment Setup ✅
**Dates:** Jan 2026 | **Release:** v0.1-alpha

**Objectives:**
- Docker containerization for reproducible builds
- ROS2 Humble workspace initialization
- Unity digital twin skeleton + Niryo URDF import
- CI/CD pipeline foundation (GitHub Actions)

**Deliverables:**
- [x] Dockerfile (Ubuntu 22.04 + ROS2 Humble)
- [x] docker-compose.yml
- [x] ROS-TCP-Endpoint bridge (Unity ↔ ROS2)
- [x] Initial URDF + physics simulation
- [ ] GitHub Actions CI/CD (pending)

---

#### Phase H1: Kill Switch Behavior & ZKP Auth (IN PROGRESS)
**Dates:** Feb-Mar 2026 | **Release Target:** v0.2.0-beta

**Objectives:**
- Implement Schnorr NIZK proof protocol on Nano33 BLE
- Validate sub-500ms recovery on network blackout
- Physical robot integration (Niryo Ned2 via TCP bridge)
- Kill switch elimination experiments

**Deliverables:**
- [ ] `zkp_auth_prover.ino` (Nano33 BLE proof generation)
- [ ] `zkp_auth_verifier.py` (ROS2 proof verification)
- [ ] Network isolation test suite (TC-001, TC-002)
- [ ] Latency histogram reports (tc-002_latency_histogram.csv)
- [ ] Physical robot control validated

**Safety-Critical Checkpoints:**
- ZKP cryptographic oracle testing (TC-003)
- Fail-safe proof verification (SAF-001)
- Audit trail completeness (SAF-002)

---

#### Phase H2: Final Certification & Thesis Defense
**Dates:** Apr 2026 | **Release Target:** v1.0.0

**Objectives:**
- Full DO-178C audit trail
- Federal IP disclosure review
- Investor due diligence package
- Thesis manuscript + defense

**Deliverables:**
- [ ] DO-178C compliance report
- [ ] Bayh-Dole certification letter (University IP office)
- [ ] Traceability matrix (REQUIREMENTS.md → test cases)
- [ ] Cryptographic validation report
- [ ] Performance baseline metrics

---

### 1.2 Configuration Management (CM)

#### Git Branching Strategy
```
main (tagged releases only: v0.1-alpha, v0.2.0-beta, v1.0.0)
  ↑
feature/* (experimental, rebased before merge)
  - feature/zkp-prover (Arduino Nano33)
  - feature/kill-switch-test (network simulation)
  - feature/thermal-mgmt (Pi4 thermal limits)

develop (integration branch, unstable)
  ↑
hotfix/* (critical bug fixes, fast-track to main)
```

#### Release Tag Format
```
vX.Y.Z[-prerelease]

Examples:
- v0.1-alpha       (H0 baseline)
- v0.2.0-beta      (H1 hypothesis)
- v0.2.1-beta.1    (H1 bug fix)
- v1.0.0           (H2 production release)
```

#### CHANGELOG.md Requirements
- **Every commit to main MUST update CHANGELOG.md**
- Format: [Keep a Changelog](http://keepachangelog.com/)
- Sections: Added, Changed, Fixed, Security, Verified
- REQ/SAF traceability tags (e.g., `[REQ-001]`, `[SAF-002]`)
- Commit hash reference

**Example Entry:**
```markdown
### Added
- Schnorr NIZK proof implementation on Nano33 BLE [REQ-003] via a1b2c3d
- Sub-500ms recovery test suite [REQ-002] via e4f5g6h
```

---

### 1.3 Verification & Validation (V&V)

#### Verification (Are we building it right?)

**Code Review:**
- All PRs require 2 technical approvals before merge
- Security review for cryptographic code
- DO-254 compliance checklist on every merge

**Automated Testing:**
- Unit tests: pytest + ROS2 test framework
- Integration tests: ROS2 node composition tests
- Hardware-in-the-loop (HIL): physical Niryo robot tests
- Network simulation: tc/netem packet loss injection

**Static Analysis:**
- Pylint + mypy for Python code (ROS2 nodes)
- clang-format for C++ (if used)
- MISRA C compliance for Arduino (Nano33 BLE)

---

#### Validation (Are we building the right thing?)

**Requirements Traceability:**
- Every REQ/SAF maps to ≥1 test case (TC-XXX)
- Every test case maps to ≥1 requirement
- Traceability matrix maintained: [docs/REQUIREMENTS.md](../docs/REQUIREMENTS.md)

**Test Execution:**
- Baseline metrics collected (v0.1-alpha): [baseline_metrics_h0.csv](../docs/data/baseline_metrics_h0.csv)
- Kill switch experiments (H1): network isolation, packet loss injection
- Thermal stress tests (H2): cpu throttling limits

**User Acceptance Testing (UAT):**
- Thesis advisor signs off on experiment results
- Federal auditors review traceability
- Investor due diligence validation

---

## 2. Safety-Critical Development (DO-254 / IEC 61508)

### 2.1 Hazard Analysis

| Hazard | Failure Mode | Effect | Severity | Risk Mitigation |
|--------|--------------|--------|----------|-----------------|
| Unauthorized Motion | Crypto verification fails | Robot moves without authorization | **CATASTROPHIC** | SAF-001: Crypto fail-safe halt within 10ms |
| Command Spoofing | Network packet injection | Attacker issues move commands | **CRITICAL** | REQ-003: NIZK authentication required |
| Lost Connectivity | Network blackout > 500ms | Robot halts (cascade failure) | **CRITICAL** | REQ-002: Local auth enables sub-500ms recovery |
| Thermal Runaway | Pi4 CPU temp > 85°C | Hardware failure / data corruption | **HIGH** | SAF-003: Graceful shutdown at 80°C |
| Audit Trail Loss | Crash during logging | Non-compliant traceability | **HIGH** | SAF-002: Dual-write audit log (RAM + NVMe) |

---

### 2.2 Assurance Case

**Claim:** "SentryC2 maintains safety-critical robot control during network blackouts."

**Evidence:**
1. **Zero-Knowledge Proof Verification** (SAF-001)
   - Cryptographic oracle: 0/10K forgery attempts succeed
   - Proof verification latency: p99 < 50ms
   - Failure mode: immediate halt + alert

2. **Sub-500ms Recovery** (REQ-002)
   - Network isolation tests: p95 recovery < 500ms
   - 1000+ trial latency histogram
   - No data loss during recovery

3. **Audit Trail Integrity** (SAF-002)
   - 100% log coverage for all commands
   - Cryptographic hash verification
   - Tamper detection: log rotation with secure deletion

4. **Environmental Limits** (SAF-003)
   - Thermal sensor monitoring every 1s
   - Graceful shutdown < 1s at threshold
   - Filesystem sync before power loss

---

## 3. Configuration Management (CM) Procedures

### 3.1 Version Control Rules

**Secrets Prevention:**
- .gitignore blocks: `.env`, `*.key`, `*.pem`, `secrets/`
- Pre-commit hooks reject files with embedded credentials
- GitHub security scanning active

**Reproducible Builds:**
- Dockerfile with pinned base image: `ubuntu:22.04`
- pip requirements locked: `requirements-lock.txt`
- ROS packages: explicit version tags

**Code Ownership:**
- Arduino code: `/arduino/` (microcontroller-specific)
- ROS2 code: `/ros2_ws/src/` (robot software)
- Unity code: `/Sentry_Simulation/` (simulation only)

---

### 3.2 Build & Deployment

**Local Development (Docker):**
```bash
cd /workspace
docker-compose up -d
docker exec -it sentry-c2-dev /bin/bash
cd ros2_ws && colcon build
source install/setup.bash
ros2 run sentry_logic cyclic_server
```

**CI/CD Pipeline (GitHub Actions):**
1. Run linting (pylint, mypy)
2. Execute unit tests (pytest)
3. Build Docker image
4. Push to ghcr.io/lpep64/sentryc2:TAG
5. Deploy to development environment

**Release Process:**
1. Update CHANGELOG.md with [Unreleased] → [vX.Y.Z]
2. Tag commit: `git tag vX.Y.Z`
3. Push: `git push origin main --tags`
4. GitHub Actions builds + pushes to container registry
5. Announce release in repository discussions

---

### 3.3 Bayh-Dole Compliance

**University IP Management:**
- All code is **Apache 2.0** (compliant with university IP policy)
- No proprietary university keys/credentials in commits
- Thesis advisor approval required before public release
- IP office notification on release: [template pending]

**Third-Party Dependencies:**
- [x] ROS2 Humble: Apache 2.0 + BSD (compliant)
- [x] micro-ecc: All rights reserved (embedded, non-viral)
- [x] libsodium: ISC license (permissive)
- [x] PyNiryo2: Apache 2.0 (compliant)
- [ ] Unity: EULA (simulation only, not distributed)

---

## 4. Traceability & Verification Matrix

### 4.1 Requirements → Test Cases Mapping

**Format:** Maintained in [docs/REQUIREMENTS.md](../docs/REQUIREMENTS.md)  
**CSV Export:** [tests/traceability_matrix.csv](../tests/traceability_matrix.csv)

| Requirement | Category | Test Case | Method | Acceptance | Status |
|-------------|----------|-----------|--------|-----------|--------|
| REQ-001 | Architecture | TC-001 | Network isolation | 100% success | Not Started |
| REQ-002 | Performance | TC-002 | Latency histogram | p95 < 500ms | Not Started |
| REQ-003 | Security | TC-003 | ZKP oracle | 0 forgeries/10K | Partial |
| SAF-001 | Safety | TC-008 | Fail-safe halt | < 10ms | Not Started |
| SAF-002 | Audit | TC-009 | Log completeness | 100% coverage | Not Started |
| SAF-003 | Environmental | TC-010 | Thermal shutdown | 80°C trigger | Not Started |

---

### 4.2 Test Case Ownership

| Test ID | Owner | Frequency | Schedule |
|---------|-------|-----------|----------|
| TC-001 → TC-010 | Integration Test Lead | Per release | Pre-release validation |
| TC-003, TC-008 | Safety Lead | Per cryptography change | Post-commit |
| TC-004 | DevOps Lead | Per Docker change | CI/CD pipeline |
| TC-005, TC-006, TC-007 | Hardware Integration Lead | Per ROS node change | Manual validation |

---

## 5. Documentation Standards

### 5.1 Required Artifacts (DO-178C)

- [x] PSAC (this document)
- [ ] SVP (Software Verification Plan)
- [x] REQUIREMENTS.md (System/software requirements)
- [ ] Architecture design document
- [ ] Detailed design document (per module)
- [ ] Source code with inline comments
- [x] Traceability matrix
- [ ] Test cases + test results
- [ ] Code review records
- [ ] Change management log (CHANGELOG.md)

---

### 5.2 Comment Guidelines (DO-178C Intent)

**Mandatory Comments:**
- Function/class **Why** (not what)
- Algorithm **rationale** (cryptographic assumptions, performance trade-offs)
- Edge cases & error handling
- Proof of safety property (e.g., "Mutex ensures no data race in joint state update")

**Example (Python):**
```python
def verify_zkp_proof(proof: bytes, challenge: bytes) -> bool:
    """
    Schnorr NIZK verification: non-interactive zero-knowledge proof
    
    WHY: Enables authorization without transmitting shared secret. Resilient
    to network isolation (no server contact required for local decisions).
    
    SAFETY: If verification fails, robot motion is blocked within 10ms [SAF-001].
    Proof must match challenge nonce to prevent replay attacks.
    
    Args:
        proof: Schnorr proof bytes (R || S)
        challenge: Hash(message || nonce) from prover
        
    Returns:
        True if proof is valid, False otherwise
        
    References:
        [1] Schnorr (1989) "Efficient identification and signatures for smart cards"
        [2] NIST SP 800-207: Zero-Trust Architecture
    """
    # Cryptographic oracle: assumes discrete log is hard
    # If this fails, Bayh-Dole compliance broken
    ...
```

---

## 6. Pre-Release Checklist (GO/NO-GO Criteria)

### Before Release (Main Branch):
- [ ] All tests pass: `pytest`, ROS2 tests, HIL tests
- [ ] CHANGELOG.md updated with version tag
- [ ] No secrets in commit (GitHub security scanning passes)
- [ ] Code review approved by 2+ maintainers
- [ ] Traceability matrix 100% traced (REQ → TC → code)
- [ ] Docker reproducibility verified: SHA256(build1) == SHA256(build2)
- [ ] Baseline metrics collected (performance regression check)
- [ ] Thesis advisor sign-off (for major releases)
- [ ] Federal IP office notification (if applicable)

---

## 7. Post-Release Validation

### 7.1 Release Notes Template

```markdown
## v0.2.0-beta - 2026-03-31

**Summary:** H1 Hypothesis Validation - Kill Switch Elimination via ZKP Auth

### New Features
- Schnorr NIZK proof authentication on Arduino Nano33 BLE [REQ-003]
- Sub-500ms recovery test suite [REQ-002, TC-002]
- Thermal management daemon for Pi4 [SAF-003, TC-010]

### Performance
- Recovery latency: p95 = 450ms, p99 = 680ms
- ZKP proof generation: 45ms (Nano33 BLE)
- ZKP proof verification: 12ms (Pi4)

### Safety Validation
- Cryptographic oracle: 0/10K forgery attempts [SAF-001]
- Audit trail coverage: 100% [SAF-002]
- Thermal stress tests passed [SAF-003]

### Breaking Changes
- ROS message format updated: `JointTrajectoryProof` now includes nonce

### Contributors
- Luke Pepin (lead)
- Configuration Manager
- Safety Lead
```

---

## 8. Certification Milestone Timeline

| Date | Milestone | Deliverable | Approver |
|------|-----------|-------------|----------|
| 2026-02-15 | H1 ZKP implementation | zkp_prover.ino + zkp_verifier.py | Cryptography Lead |
| 2026-02-28 | H1 network isolation tests | tc-002_latency_histogram.csv | Integration Lead |
| 2026-03-15 | Physical robot validation | tc-007_niryo_execution_log.txt | Hardware Lead |
| 2026-03-31 | v0.2.0-beta release | Release notes + changelog | CM |
| 2026-04-15 | Final DO-178C audit | Compliance report | Safety Lead |
| 2026-04-30 | Thesis defense | Defense slides + data | Thesis Advisor |

---

## 9. References

### DO-178C / DO-254 Standards
- [1] RTCA DO-178C: "Software Considerations in Airborne Systems and Equipment Certification"
- [2] RTCA DO-254: "Design Assurance Guidance for Airborne Hardware"
- [3] IEC 61508: "Functional safety of electrical/electronic/programmable electronic safety-related systems"

### Cryptography Standards
- [4] NIST SP 800-207: "Zero Trust Architecture"
- [5] FIPS 186-4: "Digital Signature Standard"
- [6] Schnorr (1989): "Efficient identification and signatures for smart cards"

### Repository Documentation
- [docs/REQUIREMENTS.md](../docs/REQUIREMENTS.md) — System requirements
- [docs/zkp_deployment_guide.md](../docs/zkp_deployment_guide.md) — ZKP implementation
- [CHANGELOG.md](../CHANGELOG.md) — Release history
- [tests/traceability_matrix.csv](../tests/traceability_matrix.csv) — TC mapping

---

**Prepared by:** Configuration Manager  
**Date:** 2026-02-02  
**Next Review:** 2026-03-01 (or upon major code change)

