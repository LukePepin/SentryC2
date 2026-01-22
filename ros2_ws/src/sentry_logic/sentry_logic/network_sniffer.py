#!/usr/bin/env python3
"""
SentryC2 Network Sniffer
Captures TCP traffic between Docker container and Niryo Ned2 robot
Measures latency and logs baseline metrics for resilience testing
"""
from scapy.all import sniff, IP, TCP
import time
import pandas as pd

# CONFIG
ROBOT_IP = "192.168.0.244"
LOG_FILE = "baseline_metrics_h0.csv"

def packet_callback(packet):
    if IP in packet and TCP in packet:
        # Filter for traffic to/from Robot
        if packet[IP].src == ROBOT_IP or packet[IP].dst == ROBOT_IP:
            timestamp = time.time()
            # Direction: CMD (Out) or TEL (In)
            direction = "OUTbound_CMD" if packet[IP].dst == ROBOT_IP else "INbound_TEL"
            length = len(packet)
            
            # Log to CSV (Append mode)
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp},{direction},{length}\n")

def main():
    print(f"SentryC2: Sniffing traffic on {ROBOT_IP}...")
    print(f"Logging to: {LOG_FILE}")
    print("Note: This requires root/sudo privileges")
    
    # Create CSV header if file doesn't exist
    try:
        with open(LOG_FILE, "x") as f:
            f.write("timestamp,direction,packet_length\n")
    except FileExistsError:
        pass
    
    print(f"Starting packet capture on all interfaces...")
    print(f"Filter: host {ROBOT_IP} and tcp port 9090")
    
    # Sniff TCP port 9090 (PyNiryo2 uses rosbridge port)
    sniff(filter=f"host {ROBOT_IP} and tcp port 9090", prn=packet_callback, store=0)

if __name__ == '__main__':
    main()
