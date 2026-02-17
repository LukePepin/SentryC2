#!/usr/bin/env python3
"""
test_livelock_sim.py — Unit tests for H1 Kill-Switch DIL Simulator
===================================================================
Validates livelock_sim.py logic WITHOUT requiring sudo or tc.
Uses dry-run mode + loopback echo server for deterministic testing.

Run: pytest test_livelock_sim.py -v
"""

import csv
import socket
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure the tests directory is importable
sys.path.insert(0, str(Path(__file__).parent))

from livelock_sim import (
    CLOUD_TIMEOUT_THRESHOLD_S,
    EDGE_RECOVERY_THRESHOLD_S,
    HEARTBEAT_PORT,
    EventType,
    FaultScenario,
    HeartbeatEchoServer,
    LivelockSimulator,
    LogRow,
    TrafficController,
)


# ---------------------------------------------------------------------------
# §0  FIXTURES
# ---------------------------------------------------------------------------
@pytest.fixture
def echo_server():
    """Spin up a UDP echo server on a random high port."""
    port = 19090  # Avoid collision with production port
    srv = HeartbeatEchoServer(host="127.0.0.1", port=port)
    srv.start()
    yield port
    srv.stop()
    time.sleep(0.1)  # Let socket release


@pytest.fixture
def tmp_output(tmp_path):
    """Provide a clean temp directory for CSV output."""
    return tmp_path


# ---------------------------------------------------------------------------
# §1  TrafficController — dry-run mode (no sudo required)
# ---------------------------------------------------------------------------
class TestTrafficController:
    """Verify tc wrapper logic without actually calling tc."""

    def test_inject_dry_run_prints_command(self, capsys):
        tc = TrafficController(interface="lo", dry_run=True)
        tc.inject(loss_pct=20, delay_ms=50, jitter_ms=10)
        captured = capsys.readouterr()
        assert "tc qdisc add" in captured.out
        assert "loss 20%" in captured.out
        assert "delay 50ms" in captured.out
        assert tc.is_active()

    def test_clear_dry_run(self, capsys):
        tc = TrafficController(interface="lo", dry_run=True)
        tc.inject(loss_pct=100, delay_ms=0)
        tc.clear()
        assert not tc.is_active()

    def test_inject_zero_loss_no_loss_arg(self, capsys):
        tc = TrafficController(interface="lo", dry_run=True)
        tc.inject(loss_pct=0, delay_ms=100)
        captured = capsys.readouterr()
        assert "loss" not in captured.out
        assert "delay 100ms" in captured.out


# ---------------------------------------------------------------------------
# §2  HeartbeatEchoServer — basic echo contract
# ---------------------------------------------------------------------------
class TestEchoServer:
    """Verify the built-in UDP echo server returns payload intact."""

    def test_echo_returns_same_payload(self, echo_server):
        port = echo_server
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        try:
            sock.sendto(b"HB", ("127.0.0.1", port))
            data, _ = sock.recvfrom(64)
            assert data == b"HB"
        finally:
            sock.close()

    def test_echo_handles_large_payload(self, echo_server):
        port = echo_server
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        payload = b"X" * 64
        try:
            sock.sendto(payload, ("127.0.0.1", port))
            data, _ = sock.recvfrom(128)
            assert data == payload
        finally:
            sock.close()


# ---------------------------------------------------------------------------
# §3  LivelockSimulator — end-to-end with dry-run tc
# ---------------------------------------------------------------------------
class TestSimulatorE2E:
    """Integration test: run a short simulation and validate CSV output."""

    def test_short_run_produces_csv(self, echo_server, tmp_output):
        """A 2s baseline-only run must produce a valid CSV with HEARTBEAT rows."""
        port = echo_server
        scenarios = [
            FaultScenario(name="baseline", loss_pct=0, delay_ms=0,
                          duration_s=2.0),
        ]
        sim = LivelockSimulator(
            target_host="127.0.0.1",
            target_port=port,
            interface="lo",
            scenarios=scenarios,
            output_dir=str(tmp_output),
            dry_run=True,
        )
        csv_path = sim.run()

        assert csv_path.exists()
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Must have the exact legacy columns
        assert reader.fieldnames == [
            "timestamp_ms", "event_type", "latency_ms",
            "rtt_confidence", "notes"
        ]
        # Must have at least some heartbeats (~2s / 50ms = ~40 rows)
        heartbeats = [r for r in rows if r["event_type"] == "HEARTBEAT"]
        assert len(heartbeats) >= 10, \
            f"Expected ≥10 heartbeats in 2s, got {len(heartbeats)}"

    def test_first_row_is_baseline(self, echo_server, tmp_output):
        """First HEARTBEAT row must say 'First message (baseline)'."""
        port = echo_server
        scenarios = [
            FaultScenario(name="baseline", loss_pct=0, delay_ms=0,
                          duration_s=1.0),
        ]
        sim = LivelockSimulator(
            target_host="127.0.0.1",
            target_port=port,
            interface="lo",
            scenarios=scenarios,
            output_dir=str(tmp_output),
            dry_run=True,
        )
        csv_path = sim.run()

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            first = next(reader)

        assert first["event_type"] == "HEARTBEAT"
        assert "baseline" in first["notes"].lower()

    def test_fault_inject_and_clear_logged(self, echo_server, tmp_output):
        """FAULT_INJECT + FAULT_CLEAR events must bracket a fault scenario."""
        port = echo_server
        scenarios = [
            FaultScenario(name="baseline", loss_pct=0, delay_ms=0,
                          duration_s=1.0),
            FaultScenario(name="degraded", loss_pct=20, delay_ms=50,
                          duration_s=1.0),
            FaultScenario(name="recovery", loss_pct=0, delay_ms=0,
                          duration_s=1.0),
        ]
        sim = LivelockSimulator(
            target_host="127.0.0.1",
            target_port=port,
            interface="lo",
            scenarios=scenarios,
            output_dir=str(tmp_output),
            dry_run=True,
        )
        csv_path = sim.run()

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            events = [r["event_type"] for r in reader]

        assert "FAULT_INJECT" in events, "Missing FAULT_INJECT event"
        assert "FAULT_CLEAR" in events, "Missing FAULT_CLEAR event"

        # FAULT_INJECT must appear before FAULT_CLEAR
        inject_idx = events.index("FAULT_INJECT")
        clear_idx = events.index("FAULT_CLEAR")
        assert inject_idx < clear_idx, \
            "FAULT_INJECT must precede FAULT_CLEAR"


# ---------------------------------------------------------------------------
# §4  LogRow — schema correctness
# ---------------------------------------------------------------------------
class TestLogRow:
    """Verify the data class matches legacy CSV expectations."""

    def test_fields_present(self):
        row = LogRow(
            timestamp_ms=100.0,
            event_type="HEARTBEAT",
            latency_ms=25.2,
            rtt_confidence=0.30,
            notes="Normal cycle: 50ms",
        )
        assert row.timestamp_ms == 100.0
        assert row.event_type == "HEARTBEAT"
        assert row.rtt_confidence == 0.30

    def test_all_event_types_valid(self):
        """Every EventType value must be a valid string for CSV output."""
        expected = {"HEARTBEAT", "PACKET_LOSS", "CLOUD_TIMEOUT",
                    "EDGE_RECOVERY", "FAULT_INJECT", "FAULT_CLEAR"}
        actual = {e.value for e in EventType}
        assert actual == expected


# ---------------------------------------------------------------------------
# §5  Threshold Logic — unit-level
# ---------------------------------------------------------------------------
class TestThresholds:
    """Verify H1 threshold constants match thesis requirements."""

    def test_cloud_timeout_is_30s(self):
        assert CLOUD_TIMEOUT_THRESHOLD_S == 30.0

    def test_edge_recovery_is_500ms(self):
        assert EDGE_RECOVERY_THRESHOLD_S == 0.500
