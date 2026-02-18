#!/usr/bin/env python3
"""
generate_nano33_benchmark_figure.py — Nano 33 BLE Crypto Benchmark Graph
=========================================================================
Parses H2 benchmark results captured from the Arduino Nano 33 BLE and
generates publication-quality figures for the thesis.

Reads all h2_results_nano33_*.txt files in this directory, aggregates the
per-sample data from both runs, and produces:
  - Stacked bar chart: mean keygen/sign/verify vs 500ms budget
  - Box plot: per-operation latency distributions across both runs
  - Per-sample time series (both runs overlaid)

Output: figure_nano33_benchmark.png / .pdf
"""

import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR
DPI = 300
BUDGET_US = 500_000  # 500ms in microseconds
BUDGET_MS = 500.0


def parse_results_file(filepath: Path) -> dict:
    """Parse a single h2_results_nano33_*.txt file.

    Returns dict with keys:
        samples: list of (idx, keygen_us, sign_us, verify_us, total_us)
        stats: dict of operation -> {mean, median, p99, min, max} in us
        capture_time: str
    """
    samples = []
    stats = {}
    capture_time = ""

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            # Capture timestamp
            if line.startswith("# Captured:"):
                capture_time = line.split(":", 1)[1].strip()

            # SAMPLE lines: SAMPLE,idx,keygen,sign,verify,total
            m = re.match(r"SAMPLE,(\d+),(\d+),(\d+),(\d+),(\d+)", line)
            if m:
                samples.append(tuple(int(x) for x in m.groups()))

            # STATS lines
            m = re.match(
                r"STATS,([\w_]+),mean_us=(\d+),median_us=(\d+),"
                r"p99_us=(\d+),min_us=(\d+),max_us=(\d+)",
                line,
            )
            if m:
                op = m.group(1)
                stats[op] = {
                    "mean": int(m.group(2)),
                    "median": int(m.group(3)),
                    "p99": int(m.group(4)),
                    "min": int(m.group(5)),
                    "max": int(m.group(6)),
                }

    return {"samples": samples, "stats": stats, "capture_time": capture_time}


def generate_figure(results_files: list[Path]):
    """Generate the benchmark figure from one or more result files."""

    # --- Parse all files ---
    all_runs = []
    for f in sorted(results_files):
        parsed = parse_results_file(f)
        parsed["filename"] = f.name
        all_runs.append(parsed)
        print(f"[PARSED] {f.name}: {len(parsed['samples'])} samples, "
              f"{len(parsed['stats'])} stat groups")

    if not all_runs:
        print("[ERROR] No result files found.")
        return 1

    # --- Aggregate per-sample data across runs ---
    all_keygen = []
    all_sign = []
    all_verify = []
    all_total = []

    for run in all_runs:
        for s in run["samples"]:
            # s = (idx, keygen_us, sign_us, verify_us, total_us)
            all_keygen.append(s[1])
            all_sign.append(s[2])
            all_verify.append(s[3])
            all_total.append(s[4])

    all_keygen = np.array(all_keygen, dtype=np.float64)
    all_sign = np.array(all_sign, dtype=np.float64)
    all_verify = np.array(all_verify, dtype=np.float64)
    all_total = np.array(all_total, dtype=np.float64)

    n_total = len(all_keygen)
    n_runs = len(all_runs)

    # Convert to ms for display
    keygen_ms = all_keygen / 1000.0
    sign_ms = all_sign / 1000.0
    verify_ms = all_verify / 1000.0
    total_ms = all_total / 1000.0

    # --- SETUP ---
    plt.style.use("seaborn-v0_8-paper")
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
    })

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.3)

    # =====================================================================
    # PANEL A: Stacked bar — Mean pipeline breakdown vs 500ms budget
    # =====================================================================
    ax1 = fig.add_subplot(gs[0, 0])

    mean_keygen = np.mean(keygen_ms)
    mean_sign = np.mean(sign_ms)
    mean_verify = np.mean(verify_ms)
    mean_total = mean_keygen + mean_sign + mean_verify
    remaining = BUDGET_MS - mean_total

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    labels_ops = ["Key Generation", "ECDSA Sign", "ECDSA Verify"]
    vals = [mean_keygen, mean_sign, mean_verify]

    left = 0
    for i, (v, c, lab) in enumerate(zip(vals, colors, labels_ops)):
        ax1.barh(0, v, left=left, height=0.5, color=c, edgecolor="white",
                 linewidth=0.5, label=lab)
        ax1.text(left + v / 2, 0, f"{v:.1f}ms", ha="center", va="center",
                 fontsize=8, fontweight="bold", color="white")
        left += v

    # Remaining budget
    ax1.barh(0, remaining, left=left, height=0.5, color="#77dd77", alpha=0.4,
             edgecolor="white", hatch="//", label="Remaining Budget")
    ax1.text(left + remaining / 2, 0, f"{remaining:.1f}ms\nfree",
             ha="center", va="center", fontsize=8, fontweight="bold",
             color="#2d862d")

    ax1.axvline(x=BUDGET_MS, color="red", linestyle="--", linewidth=2, zorder=10)
    ax1.text(BUDGET_MS + 3, 0.3, "500ms\nBudget", fontsize=9, color="red",
             fontweight="bold")

    ax1.set_xlim(0, BUDGET_MS)
    ax1.set_yticks([0])
    ax1.set_yticklabels(["Full Pipeline"], fontsize=10, fontweight="bold")
    ax1.set_xlabel("Latency (ms)")
    ax1.set_title("(a) Mean Pipeline vs 500ms Budget", fontweight="bold")
    ax1.legend(loc="upper right", fontsize=7, ncol=2)
    ax1.grid(True, axis="x", alpha=0.3, linestyle=":")

    pct_used = (mean_total / BUDGET_MS) * 100
    ax1.text(0.02, -0.15,
             f"Total: {mean_total:.1f}ms ({pct_used:.1f}% of budget)  |  "
             f"{n_runs} runs, {n_total} samples",
             transform=ax1.transAxes, fontsize=8,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#fffbe6",
                       edgecolor="#b8860b", alpha=0.9))

    # =====================================================================
    # PANEL B: Box plot — per-operation latency distributions
    # =====================================================================
    ax2 = fig.add_subplot(gs[0, 1])

    bp_data = [keygen_ms, sign_ms, verify_ms, total_ms]
    bp_labels = ["Key Gen", "Sign", "Verify", "Total"]
    bp_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    bp = ax2.boxplot(bp_data, tick_labels=bp_labels, patch_artist=True,
                     widths=0.5, showmeans=True,
                     meanprops=dict(marker="D", markerfacecolor="black",
                                    markersize=5))

    for patch, color in zip(bp["boxes"], bp_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax2.axhline(y=BUDGET_MS, color="red", linestyle="--", linewidth=1.5,
                label="500ms Budget")
    ax2.set_ylim(0, BUDGET_MS)
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("(b) Latency Distribution (N={})".format(n_total),
                  fontweight="bold")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, axis="y", alpha=0.3, linestyle=":")

    # =====================================================================
    # PANEL C: Time series — per-sample totals, both runs overlaid
    # =====================================================================
    ax3 = fig.add_subplot(gs[1, 0])

    run_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for run_idx, run in enumerate(all_runs):
        indices = [s[0] for s in run["samples"]]
        totals = [s[4] / 1000.0 for s in run["samples"]]
        ax3.plot(indices, totals, marker=".", markersize=3, linewidth=0.8,
                 color=run_colors[run_idx % len(run_colors)],
                 label=f"Run {run_idx + 1}", alpha=0.8)

    ax3.axhline(y=BUDGET_MS, color="red", linestyle="--", linewidth=1.5,
                label="500ms Budget")
    ax3.set_ylim(0, BUDGET_MS)
    ax3.set_xlabel("Sample Index")
    ax3.set_ylabel("Total Pipeline (ms)")
    ax3.set_title("(c) Per-Sample Pipeline Latency", fontweight="bold")
    ax3.legend(loc="upper right", fontsize=8)
    ax3.grid(True, alpha=0.3, linestyle=":")

    # =====================================================================
    # PANEL D: Stacked area — per-sample operation breakdown (Run 1)
    # =====================================================================
    ax4 = fig.add_subplot(gs[1, 1])

    # Use first run for the stacked view
    run0 = all_runs[0]
    idxs = [s[0] for s in run0["samples"]]
    kg = np.array([s[1] / 1000.0 for s in run0["samples"]])
    sg = np.array([s[2] / 1000.0 for s in run0["samples"]])
    vf = np.array([s[3] / 1000.0 for s in run0["samples"]])

    ax4.fill_between(idxs, 0, kg, alpha=0.7, color="#1f77b4",
                     label="Key Gen")
    ax4.fill_between(idxs, kg, kg + sg, alpha=0.7, color="#ff7f0e",
                     label="Sign")
    ax4.fill_between(idxs, kg + sg, kg + sg + vf, alpha=0.7,
                     color="#2ca02c", label="Verify")

    ax4.axhline(y=BUDGET_MS, color="red", linestyle="--", linewidth=1.5,
                label="500ms Budget")
    ax4.set_ylim(0, BUDGET_MS)
    ax4.set_xlabel("Sample Index")
    ax4.set_ylabel("Cumulative Latency (ms)")
    ax4.set_title("(d) Operation Breakdown (Run 1)", fontweight="bold")
    ax4.legend(loc="upper right", fontsize=8)
    ax4.grid(True, alpha=0.3, linestyle=":")

    # --- SUPTITLE ---
    fig.suptitle(
        "Figure H2-B: Nano 33 BLE (Cortex-M4F) ECDSA Benchmark\n"
        "secp256r1 (NIST P-256) — micro-ecc @ 64MHz",
        fontsize=13, fontweight="bold", y=1.02,
    )

    plt.tight_layout()

    # --- SAVE ---
    png_path = OUTPUT_DIR / "figure_nano33_benchmark.png"
    pdf_path = OUTPUT_DIR / "figure_nano33_benchmark.pdf"
    fig.savefig(png_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"[OK] {png_path}")
    print(f"[OK] {pdf_path}")
    plt.close(fig)

    # --- PRINT SUMMARY ---
    print("\n" + "=" * 68)
    print("NANO 33 BLE BENCHMARK SUMMARY (aggregated across {} runs)".format(n_runs))
    print("=" * 68)
    print(f"{'Operation':<20} {'Mean':>10} {'Median':>10} {'P99':>10} "
          f"{'Min':>10} {'Max':>10}")
    print("-" * 72)
    for name, data in [("Key Generation", keygen_ms), ("ECDSA Sign", sign_ms),
                        ("ECDSA Verify", verify_ms), ("Full Pipeline", total_ms)]:
        print(f"{name:<20} {np.mean(data):>9.2f}ms {np.median(data):>9.2f}ms "
              f"{np.percentile(data, 99):>9.2f}ms {np.min(data):>9.2f}ms "
              f"{np.max(data):>9.2f}ms")
    print("-" * 72)
    print(f"Budget Utilization: {mean_total:.1f}ms / {BUDGET_MS:.0f}ms "
          f"({pct_used:.1f}%) — PASS" if mean_total < BUDGET_MS
          else f"Budget EXCEEDED: {mean_total:.1f}ms / {BUDGET_MS:.0f}ms")
    print("=" * 68)

    return 0


def main():
    results_files = sorted(SCRIPT_DIR.glob("h2_results_nano33_*.txt"))
    if not results_files:
        print("[ERROR] No h2_results_nano33_*.txt files found in", SCRIPT_DIR)
        return 1
    print(f"[INFO] Found {len(results_files)} result file(s)")
    return generate_figure(results_files)


if __name__ == "__main__":
    sys.exit(main())
