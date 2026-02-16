# Development & Versioning Guidelines
## SentryC2 Semantic Versioning Policy

**Version:** 0.1-alpha  
**Date:** 2026-02-02  
**Prepared by:** Configuration Manager  

---

## 1. Semantic Versioning Scheme

SentryC2 follows **Semantic Versioning 2.0.0** aligned with thesis milestones:

```
vX.Y.Z[-prerelease]

v0.1-alpha       → H0 Baseline (Environment setup & simulation)
v0.2.0-beta      → H1 Hypothesis (Kill switch elimination via ZKP)
v0.2.1-beta.1    → H1 Bug fixes (optional intermediate releases)
v1.0.0           → H2 Production (Thesis defense + certification complete)
```

### 1.1 Version Numbering Rules

| Component | Increment | Trigger | Example |
|-----------|-----------|---------|---------|
| **X (Major)** | 1.0.0 → 2.0.0 | Breaking API change, incompatible hardware | v1.0.0 (thesis release) |
| **Y (Minor)** | 0.1.0 → 0.2.0 | New feature (ZKP auth), new test suite | v0.2.0 (H1 hypothesis) |
| **Z (Patch)** | 0.2.0 → 0.2.1 | Bug fix, performance improvement, no new features | v0.2.1 (H1 bug fix) |
| **Prerelease** | v0.2.0-beta.1 → v0.2.0-beta.2 | Testing before stable release | v0.2.0-beta |

### 1.2 Reset Policy

- **Major version bumps:** Y and Z reset to 0
  - v0.2.3 → v1.0.0 (not v1.2.3)
- **Minor version bumps:** Z resets to 0
  - v0.2.5 → v0.3.0 (not v0.3.5)

---

## 2. Git Tag & Release Workflow

### 2.1 Creating a Release Tag

```bash
# 1. Update version in CHANGELOG.md
#    Move [Unreleased] section → [vX.Y.Z] with date

# 2. Commit version update
git add CHANGELOG.md
git commit -m "Release v0.2.0-beta: H1 ZKP implementation

Highlights:
- Schnorr NIZK proof authentication [REQ-003]
- Sub-500ms recovery validation [REQ-002]
- Physical Niryo Ned2 integration [REQ-007]"

# 3. Tag commit (MUST be on main branch)
git tag -a v0.2.0-beta -m "H1 Hypothesis: Kill switch elimination

Release notes: https://github.com/lpep64/SentryC2/releases/tag/v0.2.0-beta"

# 4. Push to GitHub
git push origin main --tags
```

### 2.2 Tag Annotation Requirements

**Required fields in tag annotation:**
```
v0.2.0-beta: H1 Hypothesis Validation

Release: 2026-03-31
Thesis Milestone: H1 (Kill Switch Elimination)

Verified Components:
✅ Schnorr NIZK proof generation (Nano33 BLE)
✅ Sub-500ms recovery latency (1000 trials)
✅ Physical robot control (Niryo Ned2 via TCP bridge)
✅ Audit trail logging (100% coverage)

Test Results:
- Recovery p95: 498ms (target <500ms) ✓
- ZKP oracle: 0/10K forgeries ✓
- Thermal shutdown: 80°C trigger ✓

Breaking Changes:
- ROS message JointTrajectoryProof now requires nonce field

Contributors:
- Luke Pepin (lead)
- Configuration Manager (CM)
```

### 2.3 Viewing Existing Tags

```bash
# List all tags
git tag -l

# Show details of specific tag
git show v0.2.0-beta

# Filter tags by milestone
git tag -l "v0.2*"  # All H1 releases
```

---

## 3. Thesis Milestone Mapping

### 3.1 H0: Baseline Environment (January 2026)

**Release:** v0.1-alpha  
**Dates:** Jan 12 - Jan 31, 2026  
**Focus:** Reproducible development environment

**Deliverables:**
- Docker containerization (Ubuntu 22.04 + ROS2 Humble)
- ROS-TCP-Endpoint bridge (Unity ↔ ROS2)
- Niryo URDF + physics simulation
- Baseline metrics collection

**Git Command:**
```bash
git tag -a v0.1-alpha -m "H0: Baseline environment setup

- Docker reproducibility: SHA256 build verification
- Niryo Ned2 URDF import
- ROS-TCP-Endpoint integration
- Baseline metrics: docs/data/baseline_metrics_h0.csv"
```

---

### 3.2 H1: Kill Switch Elimination (February-March 2026)

**Release:** v0.2.0-beta  
**Dates:** Feb 1 - Mar 31, 2026  
**Focus:** Zero-Knowledge Proof authentication & sub-500ms recovery

**Deliverables:**
- Schnorr NIZK proof implementation (Nano33 BLE + Pi4)
- Sub-500ms recovery validation (TC-002)
- Physical robot control (Niryo Ned2 via TCP bridge)
- Network isolation experiments
- Thermal management (Pi4 CPU throttling)

**Git Command:**
```bash
git tag -a v0.2.0-beta -m "H1: Kill switch elimination via ZKP auth

Key Features:
- Schnorr NIZK proof authentication [REQ-003]
- Sub-500ms recovery latency [REQ-002] (p95: 498ms)
- Physical Niryo control [REQ-007]
- Thermal management [SAF-003]
- Audit trail logging [SAF-002]

Test Coverage:
- TC-001: Edge-first mesh ✓
- TC-002: Recovery latency ✓
- TC-003: ZKP oracle (0/10K forgeries) ✓
- TC-007: Physical robot execution ✓
- TC-010: Thermal shutdown ✓

Breaking Changes:
- ROS JointTrajectoryProof includes nonce field
- Audit log format: JSON (was: plaintext)

Verified on: Ubuntu 22.04 LTS (Docker)
Contributors: Luke Pepin, Configuration Manager"
```

---

### 3.3 H2: Production Release & Thesis (April 2026)

**Release:** v1.0.0  
**Dates:** Apr 1 - Apr 30, 2026  
**Focus:** DO-178C certification, federal disclosure, thesis defense

**Deliverables:**
- Complete DO-178C audit trail (PSAC + SVP)
- Federal IP clearance (Bayh-Dole verification)
- Thesis manuscript + defense slides
- Production-ready Docker image
- Cryptographic validation report

**Git Command:**
```bash
git tag -a v1.0.0 -m "H2: Production release & thesis certification

DO-178C Compliance:
✅ PSAC (Plan for Software Aspects of Certification)
✅ SVP (Software Verification Plan)
✅ Requirements traceability (100%)
✅ Test results archive
✅ Code review records
✅ Change management log (CHANGELOG.md)

Bayh-Dole Compliance:
✅ IP office clearance letter
✅ Patent disclosure filed
✅ License audit complete (no GPL/AGPL)
✅ Secrets prevention verified
✅ Export control determination: Academic research exemption

Performance Baseline (H2):
- Recovery latency p95: 498ms
- ZKP proof generation: 45ms (Nano33)
- ZKP proof verification: 12ms (Pi4)
- Thermal shutdown latency: <1s

Contributors:
- Luke Pepin
- Thesis Advisor
- Configuration Manager
- Safety Lead
- Integration Test Lead"
```

---

## 4. CHANGELOG.md Maintenance

### 4.1 Entry Format

Every PR to `main` MUST update CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- Feature X [REQ-001] via commit abc1234
- Feature Y [REQ-002] via commit def5678

### Changed
- Updated ROS message format [BREAKING] via commit ghi9012

### Fixed
- Bug Z [TC-003 failure] via commit jkl3456

### Security
- Hardened .gitignore to prevent secret leakage [SAF-002]

### Verified
- ✅ Ubuntu 22.04 LTS (Docker)
- ✅ ROS2 Humble rmw_cyclonedds_cpp
```

### 4.2 Section Definitions

| Section | Purpose | Example |
|---------|---------|---------|
| **Added** | New features, test cases, documentation | "Added Schnorr NIZK verification [REQ-003]" |
| **Changed** | Modifications to existing functionality | "Refactored ZKP prover for 20% latency improvement" |
| **Fixed** | Bug fixes, resolved failures | "Fixed race condition in joint state update" |
| **Removed** | Deprecated features (warn before removal) | "Removed legacy ROS1 bridge (deprecated v0.1-alpha)" |
| **Security** | Security fixes, compliance improvements | "Added pre-commit hooks to block secrets" |
| **Verified** | Platforms/environments tested | "✅ Tested on Ubuntu 22.04 + Docker" |

### 4.3 Traceability Tags

Always include requirement/test case references:

```markdown
# Good ✓
- Added Schnorr NIZK proof [REQ-003, TC-003] via a1b2c3d
- Fixed thermal shutdown logic [SAF-003, TC-010] via d4e5f6g

# Bad ✗
- Added cryptography stuff
- Fixed some bugs
```

---

## 5. Branch Management

### 5.1 Branch Structure

```
main
  │
  ├─ feature/zkp-prover
  ├─ feature/kill-switch-test
  ├─ feature/thermal-mgmt
  │
  └─ hotfix/rc-fix (emergency patches)
```

### 5.2 Branch Naming Convention

| Type | Pattern | Example | Lifetime |
|------|---------|---------|----------|
| Feature | `feature/<requirement>` | `feature/zkp-prover` | Until merged |
| Hotfix | `hotfix/<issue>` | `hotfix/rc-race-condition` | Until v1.0.0 released |
| Release prep | `release/v0.2.0-beta` | Release candidate testing | 1-2 weeks |
| Experimental | `exp/<concept>` | `exp/dual-proof-scheme` | Until abandoned |

### 5.3 Merge Requirements

**All PRs to `main` MUST:**
1. ✅ Pass GitHub Actions CI (linting, tests, docker build)
2. ✅ Require 2+ code review approvals
3. ✅ Update CHANGELOG.md with [Unreleased] entries
4. ✅ No secrets in commits (TruffleHog scan passes)
5. ✅ Squash-merge for clean history (or rebase-merge)

---

## 6. Release Candidate (RC) Process

### 6.1 RC Timeline (Example: v0.2.0-beta)

| Day | Activity | Output |
|-----|----------|--------|
| -7d | Release planning | `release/v0.2.0-beta` branch created |
| -5d | Feature freeze | No new features (only bug fixes) |
| -3d | RC1 build | Tag: `v0.2.0-beta.rc1` |
| -2d | Regression testing | Test results logged |
| -1d | RC2 build (if needed) | Tag: `v0.2.0-beta.rc2` |
| 0d | Final release | Tag: `v0.2.0-beta` pushed to main |

### 6.2 RC Testing Checklist

- [ ] All unit tests pass (pytest)
- [ ] All integration tests pass (ROS2 composition)
- [ ] All system tests pass (network isolation, HIL)
- [ ] Docker reproducibility verified
- [ ] Performance baseline collected (vs. previous version)
- [ ] No regressions (> 95% pass rate on historical tests)
- [ ] Security scan passed (no new vulnerabilities)

---

## 7. Commit Message Convention

### 7.1 Format

```
<type>: <subject> [<requirement>]

<body>

<footer>

---

Examples:

[REQ-003] feat: Implement Schnorr NIZK proof verification

Add SchnorrVerifier class for non-interactive proof validation.
Supports nonce binding to prevent replay attacks.

Closes: #42
Test: TC-003 oracle testing passed (0/10K forgeries)

---

[SAF-002] fix: Fix race condition in audit log writes

Use mutex to serialize audit log writes to prevent concurrent
corruption during high-frequency commands.

Fixes: #38
Verified: Ubuntu 22.04, 1000+ concurrent writes
```

### 7.2 Type Codes

| Type | Meaning | Example |
|------|---------|---------|
| `feat` | New feature | Schnorr proof, thermal manager |
| `fix` | Bug fix | Race condition, memory leak |
| `docs` | Documentation | README update, PSAC revision |
| `test` | Test additions | New test case, improved coverage |
| `refactor` | Code restructuring | No behavior change |
| `perf` | Performance improvement | 30% latency reduction |
| `chore` | Maintenance (deps, build) | Update ROS packages |
| `ci` | CI/CD pipeline | GitHub Actions workflow |

---

## 8. Version Deprecation & EOL

### 8.1 Support Lifecycle

| Version | Release | EOL Date | Support |
|---------|---------|----------|---------|
| v0.1-alpha | Jan 2026 | Feb 2026 | Bug fixes only |
| v0.2.0-beta | Mar 2026 | May 2026 | Full support + bug fixes |
| v1.0.0 | Apr 2026 | Ongoing | Long-term support (LTS) |

### 8.2 Deprecation Warnings

Before removing features:
1. Deprecate in version N (announce in CHANGELOG)
2. Support in versions N+1, N+2
3. Remove in version N+3

**Example:**
```markdown
## v0.3.0

### Deprecated
- ROS1 legacy bridge (use `ros1_bridge` package instead)
  - Will be removed in v1.0.0
```

---

## 9. Release Announcement Template

Post on GitHub Discussions / email thesis advisors:

```markdown
# SentryC2 v0.2.0-beta Release: H1 Hypothesis Validation

**Release Date:** 2026-03-31  
**Thesis Milestone:** H1 (Kill Switch Elimination)

## Summary
Validated sub-500ms recovery during network blackouts via Schnorr 
zero-knowledge proof authentication. All safety-critical tests passed.

## Key Features
- ✅ Schnorr NIZK proof authentication (Nano33 BLE)
- ✅ Sub-500ms recovery latency (p95: 498ms)
- ✅ Physical Niryo Ned2 robot integration
- ✅ Thermal management (Pi4 CPU throttling)
- ✅ Audit trail logging (100% coverage)

## Performance
- Proof generation: 45ms (Nano33 BLE)
- Proof verification: 12ms (Pi4)
- Recovery latency p95: 498ms (target: <500ms) ✓

## Breaking Changes
- `JointTrajectoryProof` ROS message now includes `nonce` field
- Audit log format changed to JSON

## Installation
```bash
docker pull ghcr.io/lpep64/sentryc2:v0.2.0-beta
docker-compose up -d
```

## Contributors
- Luke Pepin (lead)
- Configuration Manager (CM)
- Safety Lead

## Links
- [Changelog](../CHANGELOG.md)
- [Requirements](../docs/REQUIREMENTS.md)
- [PSAC](../docs/PSAC.md)
- [SVP](../docs/SVP.md)
```

---

## 10. Reference

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Git Tagging Best Practices](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [CHANGELOG.md](../CHANGELOG.md) (this repository)

---

**Prepared by:** Configuration Manager  
**Date:** 2026-02-02  
**Next Review:** Upon first major release (v0.2.0-beta)

