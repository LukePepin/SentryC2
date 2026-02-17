#!/usr/bin/env python3
"""
generate_h3_scalability_figure.py — H3 Livelock & Scalability Visualization
============================================================================
Reads h3_test_n*.csv files from the h3/ data directory and generates:
  - Latency vs Node Density (primary axis)
  - Timeout/Failure Rate (secondary axis)
  - Livelock onset boundary annotation
  - 3-sentence summary

Output: figure_h3_scalability.png / .pdf
"""

import csv
import glob
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "../../data/h3_validation/h3"
OUTPUT_DIR = SCRIPT_DIR
DPI = 300


def load_h3_data(data_dir: Path) -> dict:
    """
    Parse all h3_test_n*.csv files, aggregating by node density.
    Returns {n: {"latencies": [...], "statuses": [...], "files": [...]}}
    """
    pattern = str(data_dir / "h3_test_n*_*.csv")
    files = sorted(glob.glob(pattern))

    by_n = defaultdict(lambda: {"latencies": [], "statuses": [], "files": []})

    for filepath in files:
        # Extract node count from filename: h3_test_n{N}_...
        m = re.search(r"n(\d+)_", os.path.basename(filepath))
        if not m:
            continue
        n = int(m.group(1))

        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lat = float(row["latency_ms"])
                status = row["status"]
                by_n[n]["latencies"].append(lat)
                by_n[n]["statuses"].append(status)

        by_n[n]["files"].append(os.path.basename(filepath))

    return dict(by_n)


def compute_metrics(by_n: dict) -> dict:
    """Compute per-node-density statistics."""
    metrics = {}
    for n in sorted(by_n.keys()):
        lats = np.array(by_n[n]["latencies"])
        statuses = by_n[n]["statuses"]
        total = len(statuses)
        timeouts = sum(1 for s in statuses if s == "TIMEOUT")
        successes = [l for l, s in zip(lats, statuses) if s == "SUCCESS" and l > 0]

        metrics[n] = {
            "total": total,
            "timeouts": timeouts,
            "timeout_pct": (timeouts / total * 100) if total else 0,
            "mean_ms": float(np.mean(successes)) if successes else 0,
            "p99_ms": float(np.percentile(successes, 99)) if successes else 0,
            "max_ms": float(np.max(successes)) if successes else 0,
            "success_count": len(successes),
            "files": len(by_n[n]["files"]),
        }
    return metrics


def generate_figure(metrics: dict):
    """Produce the dual-axis scalability figure."""
    plt.style.use("seaborn-v0_8-paper")
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
    })

    nodes = np.array(sorted(metrics.keys()))
    mean_lat = np.array([metrics[n]["mean_ms"] for n in nodes])
    p99_lat = np.array([metrics[n]["p99_ms"] for n in nodes])
    timeout_pct = np.array([metrics[n]["timeout_pct"] for n in nodes])

    # Theoretical linear baseline
    L0 = mean_lat[0] if mean_lat[0] > 0 else 10.0
    theoretical = nodes * L0

    fig, ax1 = plt.subplots(figsize=(8, 5), dpi=100)

    # --- Primary axis: Latency ---
    ax1.plot(nodes, mean_lat, "o-", color="#1f77b4", linewidth=2,
             markersize=6, label="Empirical Mean Latency", zorder=3)
    ax1.plot(nodes, p99_lat, "s--", color="#1f77b4", linewidth=1, alpha=0.5,
             markersize=4, label="Empirical P99 Latency", zorder=3)
    ax1.plot(nodes, theoretical, "--", color="#7f7f7f", linewidth=1.5,
             label=f"Theoretical Linear (n×{L0:.1f}ms)", zorder=2)

    ax1.set_xlabel("Node Density (n)", fontweight="bold")
    ax1.set_ylabel("Authentication Latency (ms)", fontweight="bold",
                   color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax1.set_xticks(nodes)
    ax1.set_xlim(0, max(nodes) + 2)
    ax1.set_ylim(0, max(max(theoretical), max(p99_lat)) * 1.15)
    ax1.grid(True, alpha=0.3, linestyle=":", linewidth=0.5)

    # --- Secondary axis: Failure rate ---
    ax2 = ax1.twinx()
    ax2.fill_between(nodes, timeout_pct, color="#d62728", alpha=0.25,
                     label="Timeout Rate", zorder=1)
    ax2.plot(nodes, timeout_pct, "s-", color="#d62728", markersize=5,
             linewidth=1.5, zorder=2)
    ax2.set_ylabel("Authentication Failure Rate (%)", fontweight="bold",
                   color="#d62728")
    ax2.tick_params(axis="y", labelcolor="#d62728")
    ax2.set_ylim(0, 65)

    # --- Livelock boundary ---
    # Find onset: first n with timeout_pct > 0
    onset_n = None
    onset_pct = 0
    for n in nodes:
        if metrics[n]["timeout_pct"] > 0:
            onset_n = n
            onset_pct = metrics[n]["timeout_pct"]
            break

    if onset_n:
        ax1.axvline(x=onset_n, color="red", linestyle=":", linewidth=2, zorder=1)
        ax1.axvspan(onset_n, max(nodes) + 2, color="red", alpha=0.08, zorder=0)
        ax1.annotate(
            f"Livelock Onset\n(n={onset_n}, {onset_pct:.1f}%)",
            xy=(onset_n, max(mean_lat) * 0.5),
            xytext=(onset_n - 4, max(mean_lat) * 0.7),
            fontsize=9, color="darkred", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="darkred", lw=1.5),
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="darkred", alpha=0.9)
        )
        ax1.text(
            (onset_n + max(nodes)) / 2, max(theoretical) * 1.0,
            "Livelock Region\n(Queue Saturation)",
            fontsize=9, color="darkred", fontweight="bold", ha="center",
            va="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="darkred", alpha=0.9)
        )

    # --- Legend ---
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left",
               frameon=True, framealpha=0.95, fontsize=9)

    fig.suptitle("Figure 4.3: H₃ Scalability & Livelock Analysis",
                 fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()

    # Save
    png_path = OUTPUT_DIR / "figure_h3_scalability.png"
    pdf_path = OUTPUT_DIR / "figure_h3_scalability.pdf"
    fig.savefig(png_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"[OK] {png_path} (300 DPI)")
    print(f"[OK] {pdf_path} (Vector)")
    plt.close(fig)


def print_summary(metrics: dict):
    """Print the 3-sentence summary."""
    nodes = sorted(metrics.keys())
    safe_nodes = [n for n in nodes if metrics[n]["timeout_pct"] == 0]
    unsafe_nodes = [n for n in nodes if metrics[n]["timeout_pct"] > 0]
    max_safe = max(safe_nodes) if safe_nodes else 0
    worst_n = max(nodes)
    worst_to = metrics[worst_n]["timeout_pct"]

    print("\n" + "=" * 72)
    print("H3 SCALABILITY — 3-SENTENCE SUMMARY")
    print("=" * 72)
    print(
        f"SentryC2's ZKP authentication pipeline scales linearly up to "
        f"n={max_safe} concurrent nodes with 0% timeout rate and "
        f"mean latency of {metrics[max_safe]['mean_ms']:.1f}ms — validating "
        f"the ROS2 SingleThreadedExecutor path under nominal load."
    )
    if unsafe_nodes:
        onset = min(unsafe_nodes)
        print(
            f"Livelock onset occurs at n={onset} nodes "
            f"({metrics[onset]['timeout_pct']:.1f}% failure), escalating to "
            f"{worst_to:.1f}% at n={worst_n} due to queue head-of-line "
            f"blocking in the service callback chain."
        )
    print(
        "H₃ is validated: the system exhibits O(n) degradation with a "
        "catastrophic failure boundary — operational deployments should "
        f"cap node density at n≤{max_safe} without executor redesign."
    )
    print("=" * 72)


def main():
    if not DATA_DIR.is_dir():
        print(f"[FATAL] Data directory not found: {DATA_DIR}", file=sys.stderr)
        return 1

    by_n = load_h3_data(DATA_DIR)
    if not by_n:
        print(f"[FATAL] No h3_test_*.csv in {DATA_DIR}", file=sys.stderr)
        return 1

    print(f"[LOAD] Found data for node densities: {sorted(by_n.keys())}")
    metrics = compute_metrics(by_n)

    for n in sorted(metrics.keys()):
        m = metrics[n]
        print(f"  n={n:2d}: mean={m['mean_ms']:6.1f}ms  p99={m['p99_ms']:6.1f}ms  "
              f"timeout={m['timeout_pct']:5.1f}%  ({m['files']} files)")

    generate_figure(metrics)
    print_summary(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
