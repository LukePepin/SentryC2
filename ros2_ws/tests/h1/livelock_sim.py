#!/usr/bin/env python3
"""
livelock_sim.py — H1 "Kill Switch" DIL Network Simulator
=========================================================
Task 3.1: Validates Thesis Hypothesis H₁ (Resilience) by injecting
network faults via Linux `tc` (Traffic Control) and measuring heartbeat
recovery latency.

Requires: sudo privileges (tc netem), Linux host, Python ≥ 3.8
Target:   Supervisor Node (Raspberry Pi 4) or localhost loopback

Output CSV schema (legacy-compatible):
    timestamp_ms, event_type, latency_ms, rtt_confidence, notes

ARCHITECTURAL INTENT:
    - Prove edge autonomy survives 100% packet loss for ≤30s.
    - Measure sub-500ms recovery after fault clearance.
    - Detect livelock if heartbeat gap exceeds 30s (CLOUD_TIMEOUT).
"""

import argparse
import csv
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# §0  CONSTANTS — Tunable thresholds derived from H1 requirements
# ---------------------------------------------------------------------------
HEARTBEAT_INTERVAL_S: float = 0.050       # 50ms nominal send rate
HEARTBEAT_PORT: int = 9090                 # UDP echo port
SOCKET_TIMEOUT_S: float = 0.200           # 200ms recv timeout per ping
CLOUD_TIMEOUT_THRESHOLD_S: float = 30.0   # Gap > 30s ⇒ cloud-severed
EDGE_RECOVERY_THRESHOLD_S: float = 0.500  # Gap < 500ms ⇒ fast recovery
RTT_CONFIDENCE_NOMINAL: float = 0.30      # Static confidence for loopback
DEFAULT_INTERFACE: str = "lo"              # Loopback for safe local testing
DEFAULT_DURATION_S: float = 60.0          # Total test duration


class EventType(Enum):
    """Mirrors the legacy CSV event_type column."""
    HEARTBEAT = "HEARTBEAT"
    PACKET_LOSS = "PACKET_LOSS"
    CLOUD_TIMEOUT = "CLOUD_TIMEOUT"
    EDGE_RECOVERY = "EDGE_RECOVERY"
    FAULT_INJECT = "FAULT_INJECT"
    FAULT_CLEAR = "FAULT_CLEAR"


@dataclass
class LogRow:
    """Single CSV row — matches legacy h1_test_*.csv schema."""
    timestamp_ms: float
    event_type: str
    latency_ms: float
    rtt_confidence: float
    notes: str


# ---------------------------------------------------------------------------
# §1  FAULT SCENARIO DEFINITIONS
# ---------------------------------------------------------------------------
@dataclass
class FaultScenario:
    """Describes one tc-netem fault injection phase."""
    name: str
    loss_pct: int           # 0–100
    delay_ms: int           # Added latency (ms)
    duration_s: float       # How long the fault persists
    jitter_ms: int = 0      # Optional jitter


# Default DIL scenario ladder: normal → degraded → denied → recovery
DEFAULT_SCENARIOS: List[FaultScenario] = [
    FaultScenario(name="baseline",      loss_pct=0,   delay_ms=0,   duration_s=5.0),
    FaultScenario(name="degraded_20",   loss_pct=20,  delay_ms=50,  duration_s=10.0, jitter_ms=25),
    FaultScenario(name="denied_100",    loss_pct=100, delay_ms=0,   duration_s=15.0),
    FaultScenario(name="recovery",      loss_pct=0,   delay_ms=0,   duration_s=10.0),
]


# ---------------------------------------------------------------------------
# §2  TRAFFIC CONTROL (tc) WRAPPER — requires sudo
# ---------------------------------------------------------------------------
class TrafficController:
    """
    Wraps Linux `tc qdisc` calls for netem fault injection.
    All mutations are idempotent: clear-before-set prevents stale rules.
    """

    def __init__(self, interface: str = DEFAULT_INTERFACE, dry_run: bool = False):
        self._iface = interface
        self._dry_run = dry_run
        self._active = False

    def inject(self, loss_pct: int, delay_ms: int, jitter_ms: int = 0) -> None:
        """Apply netem rule. Clears any prior rule first."""
        self.clear()
        parts = ["sudo", "tc", "qdisc", "add", "dev", self._iface,
                 "root", "netem"]
        if loss_pct > 0:
            parts += ["loss", f"{loss_pct}%"]
        if delay_ms > 0:
            parts += ["delay", f"{delay_ms}ms"]
            if jitter_ms > 0:
                parts += [f"{jitter_ms}ms"]
        self._run(parts)
        self._active = True

    def clear(self) -> None:
        """Remove any existing netem qdisc — safe to call repeatedly."""
        self._run(["sudo", "tc", "qdisc", "del", "dev", self._iface,
                   "root"], allow_fail=True)
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def _run(self, cmd: List[str], allow_fail: bool = False) -> None:
        if self._dry_run:
            print(f"[DRY-RUN] {' '.join(cmd)}")
            return
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=5)
        except subprocess.CalledProcessError:
            if not allow_fail:
                raise
        except FileNotFoundError:
            # tc not available (e.g. Windows dev box) — degrade gracefully
            if not allow_fail:
                print("[WARN] `tc` not found. Running in dry-run mode.",
                      file=sys.stderr)


# ---------------------------------------------------------------------------
# §3  UDP HEARTBEAT ENGINE
# ---------------------------------------------------------------------------
class HeartbeatEchoServer(threading.Thread):
    """
    Minimal UDP echo server — runs in a background thread so the
    simulator can talk to itself on loopback for CI/local validation.
    Kill via stop().
    """

    def __init__(self, host: str = "127.0.0.1", port: int = HEARTBEAT_PORT):
        super().__init__(daemon=True)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.settimeout(0.5)
        self._sock.bind((host, port))
        self._running = True

    def run(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(64)
                self._sock.sendto(data, addr)
            except socket.timeout:
                continue
            except OSError:
                # Socket closed during recvfrom (expected on stop())
                break

    def stop(self) -> None:
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# §4  CORE SIMULATOR — orchestrates scenarios and records metrics
# ---------------------------------------------------------------------------
class LivelockSimulator:
    """
    Drives the heartbeat/fault-injection loop and writes the CSV log.

    State machine:
        IDLE → BASELINE → FAULT_n → RECOVERY → DONE
    """

    def __init__(
        self,
        target_host: str = "127.0.0.1",
        target_port: int = HEARTBEAT_PORT,
        interface: str = DEFAULT_INTERFACE,
        scenarios: Optional[List[FaultScenario]] = None,
        output_dir: str = ".",
        dry_run: bool = False,
    ):
        self._host = target_host
        self._port = target_port
        self._tc = TrafficController(interface=interface, dry_run=dry_run)
        self._scenarios = scenarios or DEFAULT_SCENARIOS
        self._output_dir = Path(output_dir)
        self._log: List[LogRow] = []
        self._t0: float = 0.0              # epoch reference (ms)
        self._last_success_ts: float = 0.0  # last successful heartbeat (ms)
        self._sock: Optional[socket.socket] = None
        self._running = True

    # -- public API --

    def run(self) -> Path:
        """Execute all scenarios sequentially, return path to output CSV."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(SOCKET_TIMEOUT_S)
        self._t0 = time.monotonic() * 1000.0

        try:
            for scenario in self._scenarios:
                if not self._running:
                    break
                self._execute_scenario(scenario)
        finally:
            self._cleanup()

        return self._write_csv()

    def abort(self) -> None:
        """Signal graceful shutdown (e.g. from SIGINT handler)."""
        self._running = False

    # -- private implementation --

    def _now_ms(self) -> float:
        """Elapsed milliseconds since test start."""
        return time.monotonic() * 1000.0 - self._t0

    def _execute_scenario(self, scenario: FaultScenario) -> None:
        """Run one fault scenario for its configured duration."""
        is_fault = scenario.loss_pct > 0 or scenario.delay_ms > 0

        # Apply / clear tc rules
        if is_fault:
            self._tc.inject(scenario.loss_pct, scenario.delay_ms,
                            scenario.jitter_ms)
            self._record(EventType.FAULT_INJECT, 0.0,
                         f"tc netem loss={scenario.loss_pct}% "
                         f"delay={scenario.delay_ms}ms "
                         f"jitter={scenario.jitter_ms}ms "
                         f"[{scenario.name}]")
        else:
            if self._tc.is_active():
                self._tc.clear()
                self._record(EventType.FAULT_CLEAR, 0.0,
                             f"Cleared [{scenario.name}]")

        phase_end = self._now_ms() + scenario.duration_s * 1000.0
        first_in_phase = True

        while self._running and self._now_ms() < phase_end:
            rtt_ms = self._send_heartbeat()

            ts_now = self._now_ms()
            gap_from_last = (ts_now - self._last_success_ts) if self._last_success_ts else 0.0

            if rtt_ms is not None:
                # Successful pong received
                cycle_ms = gap_from_last if self._last_success_ts else 0.0

                if first_in_phase and not is_fault and self._last_success_ts > 0:
                    # Check edge recovery condition
                    if gap_from_last < EDGE_RECOVERY_THRESHOLD_S * 1000.0:
                        self._record(EventType.EDGE_RECOVERY, rtt_ms,
                                     f"Recovered in {gap_from_last:.0f}ms "
                                     f"(threshold {EDGE_RECOVERY_THRESHOLD_S*1000:.0f}ms)")
                    first_in_phase = False

                # Classify: normal heartbeat vs degraded (PACKET_LOSS-style delay)
                expected_ms = HEARTBEAT_INTERVAL_S * 1000.0 * 2  # 100ms tolerance
                if cycle_ms > expected_ms and self._last_success_ts > 0:
                    self._record(EventType.PACKET_LOSS, rtt_ms,
                                 f"Delayed arrival: {cycle_ms:.0f}ms "
                                 f"(expected {expected_ms:.0f}ms)")
                else:
                    note = "First message (baseline)" if self._last_success_ts == 0.0 \
                        else f"Normal cycle: {cycle_ms:.0f}ms"
                    self._record(EventType.HEARTBEAT, rtt_ms, note)

                self._last_success_ts = ts_now
                first_in_phase = False
            else:
                # Timeout — check for cloud-severed condition
                if self._last_success_ts > 0:
                    gap_s = gap_from_last / 1000.0
                    if gap_s >= CLOUD_TIMEOUT_THRESHOLD_S:
                        self._record(EventType.CLOUD_TIMEOUT, 0.0,
                                     f"No heartbeat for {gap_s:.1f}s "
                                     f"(threshold {CLOUD_TIMEOUT_THRESHOLD_S:.0f}s)")

            # Pace to ~50ms cycle
            elapsed_this_iter = self._now_ms() - ts_now
            sleep_s = max(0, HEARTBEAT_INTERVAL_S - elapsed_this_iter / 1000.0)
            time.sleep(sleep_s)

    def _send_heartbeat(self) -> Optional[float]:
        """
        Send a single UDP ping and measure RTT.
        Returns RTT in ms, or None on timeout/error.
        """
        payload = b"HB"
        try:
            t_send = time.monotonic()
            self._sock.sendto(payload, (self._host, self._port))
            data, _ = self._sock.recvfrom(64)
            t_recv = time.monotonic()
            if data == payload:
                return (t_recv - t_send) * 1000.0
        except (socket.timeout, OSError):
            pass
        return None

    def _record(self, event: EventType, latency_ms: float, notes: str) -> None:
        """Append a row to the in-memory log."""
        self._log.append(LogRow(
            timestamp_ms=round(self._now_ms(), 1),
            event_type=event.value,
            latency_ms=round(latency_ms, 1),
            rtt_confidence=RTT_CONFIDENCE_NOMINAL if latency_ms > 0 else 0.00,
            notes=notes,
        ))

    def _write_csv(self) -> Path:
        """Flush log to disk in legacy-compatible CSV format."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = socket.gethostname()
        filename = f"h1_test_{hostname}_{ts_tag}.csv"
        path = self._output_dir / filename

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_ms", "event_type", "latency_ms",
                             "rtt_confidence", "notes"])
            for row in self._log:
                writer.writerow([
                    f"{row.timestamp_ms:.1f}",
                    row.event_type,
                    f"{row.latency_ms:.1f}",
                    f"{row.rtt_confidence:.2f}",
                    row.notes,
                ])

        print(f"[CSV] Wrote {len(self._log)} rows → {path}")
        return path

    def _cleanup(self) -> None:
        """Deterministic teardown: clear tc rules, close socket."""
        self._tc.clear()
        if self._sock:
            self._sock.close()
            self._sock = None


# ---------------------------------------------------------------------------
# §5  SIGNAL HANDLING — clean exit on Ctrl+C
# ---------------------------------------------------------------------------
_simulator_instance: Optional[LivelockSimulator] = None


def _signal_handler(signum, frame):
    """Ensures tc rules are purged even on forced exit."""
    print(f"\n[SIG] Caught signal {signum} — cleaning up tc rules...")
    if _simulator_instance:
        _simulator_instance.abort()


# ---------------------------------------------------------------------------
# §6  CLI ENTRY POINT
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="H1 Kill-Switch DIL Simulator — injects packet loss via "
                    "tc netem and measures heartbeat resilience.",
        epilog="Requires sudo for tc commands. Use --dry-run on non-Linux hosts."
    )
    p.add_argument("--host", default="127.0.0.1",
                   help="Target heartbeat host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=HEARTBEAT_PORT,
                   help=f"Target UDP port (default: {HEARTBEAT_PORT})")
    p.add_argument("--interface", default=DEFAULT_INTERFACE,
                   help=f"Network interface for tc (default: {DEFAULT_INTERFACE})")
    p.add_argument("--output-dir", default=".",
                   help="Directory for output CSV (default: cwd)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print tc commands instead of executing them")
    p.add_argument("--no-echo-server", action="store_true",
                   help="Skip built-in echo server (use external target)")
    p.add_argument("--baseline-s", type=float, default=5.0,
                   help="Baseline phase duration (default: 5s)")
    p.add_argument("--degraded-s", type=float, default=10.0,
                   help="Degraded (20%% loss) phase duration (default: 10s)")
    p.add_argument("--denied-s", type=float, default=15.0,
                   help="Denied (100%% loss) phase duration (default: 15s)")
    p.add_argument("--recovery-s", type=float, default=10.0,
                   help="Recovery phase duration (default: 10s)")
    return p.parse_args()


def main() -> int:
    global _simulator_instance

    # Guard: tc requires root on Linux
    if os.name == "posix" and os.geteuid() != 0:
        if "--dry-run" not in sys.argv:
            print("[FATAL] This script requires sudo for tc commands.",
                  file=sys.stderr)
            print("        Run: sudo python3 livelock_sim.py", file=sys.stderr)
            print("        Or:  python3 livelock_sim.py --dry-run",
                  file=sys.stderr)
            return 1

    args = parse_args()

    # Build scenario list from CLI durations
    scenarios = [
        FaultScenario(name="baseline",    loss_pct=0,   delay_ms=0,
                      duration_s=args.baseline_s),
        FaultScenario(name="degraded_20", loss_pct=20,  delay_ms=50,
                      duration_s=args.degraded_s, jitter_ms=25),
        FaultScenario(name="denied_100",  loss_pct=100, delay_ms=0,
                      duration_s=args.denied_s),
        FaultScenario(name="recovery",    loss_pct=0,   delay_ms=0,
                      duration_s=args.recovery_s),
    ]

    # Start built-in echo server unless user brings their own
    echo_server: Optional[HeartbeatEchoServer] = None
    if not args.no_echo_server:
        echo_server = HeartbeatEchoServer(host=args.host, port=args.port)
        echo_server.start()
        print(f"[ECHO] UDP echo server listening on {args.host}:{args.port}")

    sim = LivelockSimulator(
        target_host=args.host,
        target_port=args.port,
        interface=args.interface,
        scenarios=scenarios,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    _simulator_instance = sim

    # Register signal handlers for clean tc teardown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"[SIM] Starting H1 livelock simulation on {args.interface}")
    print(f"[SIM] Phases: baseline={args.baseline_s}s, "
          f"degraded={args.degraded_s}s, "
          f"denied={args.denied_s}s, "
          f"recovery={args.recovery_s}s")
    print(f"[SIM] Thresholds: CLOUD_TIMEOUT={CLOUD_TIMEOUT_THRESHOLD_S}s, "
          f"EDGE_RECOVERY={EDGE_RECOVERY_THRESHOLD_S*1000:.0f}ms")

    try:
        csv_path = sim.run()
        print(f"[DONE] Results: {csv_path}")
        return 0
    except KeyboardInterrupt:
        print("\n[ABORT] KeyboardInterrupt — cleaning up...")
        sim.abort()
        sim._cleanup()
        return 130
    finally:
        if echo_server:
            echo_server.stop()


if __name__ == "__main__":
    sys.exit(main())
