#!/usr/bin/env python3
"""
H2 Nano 33 BLE Serial Capture
==============================

Captures benchmark output from the Arduino Nano 33 BLE over USB serial
and saves it as a timestamped results file for the thesis data pipeline.

Usage:
    python3 capture_nano33_benchmark.py [--port /dev/ttyACM0] [--baud 115200]

The script waits for "BENCHMARK COMPLETE" marker, then saves output.
"""

import serial
import sys
import os
import argparse
import platform
from datetime import datetime


def find_serial_port() -> str:
    """Auto-detect the Nano 33 BLE serial port."""
    candidates = [
        "/dev/ttyACM0",    # Linux (most common for Nano 33 BLE)
        "/dev/ttyACM1",
        "/dev/ttyUSB0",
        "COM3",            # Windows fallback
        "COM4",
    ]
    for port in candidates:
        try:
            s = serial.Serial(port, 115200, timeout=1)
            s.close()
            return port
        except (serial.SerialException, OSError):
            continue
    return "/dev/ttyACM0"  # Default, let it fail with clear error


def main():
    parser = argparse.ArgumentParser(description="Capture Nano 33 BLE benchmark output")
    parser.add_argument("--port", type=str, default=None, help="Serial port (auto-detect if omitted)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=int, default=300, help="Max wait time in seconds (default: 300)")
    args = parser.parse_args()

    port = args.port or find_serial_port()

    print(f"[CAPTURE] Connecting to {port} @ {args.baud} baud...")
    print(f"[CAPTURE] Timeout: {args.timeout}s")
    print(f"[CAPTURE] Press RESET on the Nano 33 BLE to start benchmark")
    print()

    try:
        ser = serial.Serial(port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"[ERROR] Cannot open {port}: {e}")
        print(f"[HINT]  Check: ls /dev/ttyACM* or specify --port")
        sys.exit(1)

    lines = []
    start_time = datetime.now()
    complete = False

    try:
        while (datetime.now() - start_time).total_seconds() < args.timeout:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").rstrip()
            lines.append(line)
            print(line)  # Mirror to console

            if "BENCHMARK COMPLETE" in line:
                complete = True
                # Read a few more lines to get closing banner
                for _ in range(5):
                    raw = ser.readline()
                    if raw:
                        line = raw.decode("utf-8", errors="replace").rstrip()
                        lines.append(line)
                        print(line)
                break

    except KeyboardInterrupt:
        print("\n[CAPTURE] Interrupted by user")
    finally:
        ser.close()

    if not complete:
        print("\n[WARN] Did not receive BENCHMARK COMPLETE marker")
        print("[WARN] Saving partial output anyway")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hostname = platform.node().replace(" ", "_")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = f"h2_results_nano33_{timestamp}.txt"
    filepath = os.path.join(script_dir, filename)

    with open(filepath, "w") as f:
        f.write(f"# H2 Security Tax Benchmark — Arduino Nano 33 BLE\n")
        f.write(f"# Captured: {datetime.now().isoformat()}\n")
        f.write(f"# Host: {hostname}\n")
        f.write(f"# Serial Port: {port}\n")
        f.write(f"# Python: {sys.version}\n")
        f.write(f"# Platform: {platform.platform()}\n")
        f.write(f"\n")
        for line in lines:
            f.write(line + "\n")

    print(f"\n[OUTPUT] Results saved to: {filepath}")
    print(f"[OUTPUT] Total lines captured: {len(lines)}")


if __name__ == "__main__":
    main()
