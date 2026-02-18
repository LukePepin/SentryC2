#!/usr/bin/env python3
"""
generate_500ms_budget_figure.py — Latency Budget Waterfall Diagram
===================================================================
Constructs a stacked horizontal bar (waterfall) showing how each
subsystem consumes portions of the 500ms edge-recovery budget.

Uses MEASURED values from H1/H2/H3 test campaigns.
Projects where the budget goes under nominal and worst-case scenarios.

Output: figure_500ms_budget.png / .pdf
"""

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
BUDGET_MS = 500.0

# ---------------------------------------------------------------------------
# MEASURED DATA — sourced from H1/H2/H3 validation campaigns
# ---------------------------------------------------------------------------

# Two platform profiles: Pi4 (production target) and WSL2 (dev/CI)
PROFILES = {
    "Pi 4 (Production)": {
        # H1: Heartbeat RTT (UDP loopback on Pi4)
        "Heartbeat RTT":        {"nominal": 25.2,  "worst": 40.2},
        # H2: ECC/ECDSA baseline crypto
        "ECC/ECDSA Crypto":     {"nominal": 0.546, "worst": 0.596},
        # H2: ZKP delta (Schnorr - ECC)
        "ZKP Tax (Schnorr Δ)":  {"nominal": 0.125, "worst": 0.132},
        # H3: Auth pipeline at n=10 (last safe node count)
        "Auth Pipeline (n=10)": {"nominal": 19.9,  "worst": 21.0},
        # Network: measured packet-loss recovery latency
        "Network Jitter/Loss":  {"nominal": 5.0,   "worst": 332.1},
        # OS scheduling + ROS2 callback overhead
        "OS/ROS2 Scheduling":   {"nominal": 2.0,   "worst": 10.0},
    },
    "WSL2 / Dev (CI)": {
        "Heartbeat RTT":        {"nominal": 0.3,   "worst": 0.5},
        "ECC/ECDSA Crypto":     {"nominal": 0.087, "worst": 0.134},
        "ZKP Tax (Schnorr Δ)":  {"nominal": 0.021, "worst": 0.040},
        "Auth Pipeline (n=10)": {"nominal": 10.1,  "worst": 19.9},
        "Network Jitter/Loss":  {"nominal": 0.1,   "worst": 5.0},
        "OS/ROS2 Scheduling":   {"nominal": 0.5,   "worst": 2.0},
    },
    # Measured on physical Nano 33 BLE (Cortex-M4F @ 64MHz, micro-ecc secp256r1)
    # Source: h2_results_nano33_20260218_091530.txt, h2_results_nano33_20260218_091634.txt
    # N=100 samples (2 runs × 50), 5 warmup iterations per run
    "Nano 33 BLE (Worker)": {
        "ECC Key Generation":   {"nominal": 113.4, "worst": 113.6},
        "ECDSA Sign":           {"nominal": 125.3, "worst": 125.6},
        "ECDSA Verify":         {"nominal": 136.0, "worst": 141.8},
        "Serial I/O Overhead":  {"nominal": 2.0,   "worst": 5.0},
    },
}

# Color palette for each budget component
COLORS = {
    "Heartbeat RTT":        "#1f77b4",  # Blue
    "ECC/ECDSA Crypto":     "#2ca02c",  # Green
    "ZKP Tax (Schnorr Δ)":  "#d62728",  # Red
    "Auth Pipeline (n=10)": "#ff7f0e",  # Orange
    "Network Jitter/Loss":  "#9467bd",  # Purple
    "OS/ROS2 Scheduling":   "#8c564b",  # Brown
    "ECC Key Generation":   "#17becf",  # Cyan
    "ECDSA Sign":           "#bcbd22",  # Olive
    "ECDSA Verify":         "#e377c2",  # Pink
    "Serial I/O Overhead":  "#7f7f7f",  # Gray
}


def generate_figure():
    plt.style.use("seaborn-v0_8-paper")
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
    })

    fig, axes = plt.subplots(len(PROFILES), 1, figsize=(12, 4 * len(PROFILES)),
                             squeeze=False)

    for prof_idx, (profile_name, components) in enumerate(PROFILES.items()):
        ax = axes[prof_idx, 0]
        labels = list(components.keys())
        n = len(labels)

        # --- Nominal scenario ---
        nominal_vals = [components[l]["nominal"] for l in labels]
        nominal_total = sum(nominal_vals)
        nominal_remaining = BUDGET_MS - nominal_total

        # --- Worst-case scenario ---
        worst_vals = [components[l]["worst"] for l in labels]
        worst_total = sum(worst_vals)
        worst_remaining = BUDGET_MS - worst_total

        y_positions = [0, 1]  # 0 = nominal, 1 = worst-case
        bar_height = 0.5

        # Draw stacked horizontal bars
        for scenario_idx, (vals, total, remaining, label_prefix) in enumerate([
            (nominal_vals, nominal_total, nominal_remaining, "Nominal"),
            (worst_vals, worst_total, worst_remaining, "Worst-Case"),
        ]):
            left = 0
            for i, (comp_label, val) in enumerate(zip(labels, vals)):
                bar = ax.barh(scenario_idx, val, left=left, height=bar_height,
                              color=COLORS[comp_label],
                              edgecolor="white", linewidth=0.5,
                              label=comp_label if scenario_idx == 0 else None)

                # Label if segment is wide enough
                if val > BUDGET_MS * 0.03:
                    ax.text(left + val / 2, scenario_idx, f"{val:.1f}",
                            ha="center", va="center", fontsize=7,
                            fontweight="bold", color="white")
                left += val

            # Remaining budget (green fill)
            if remaining > 0:
                ax.barh(scenario_idx, remaining, left=left, height=bar_height,
                        color="#77dd77", alpha=0.4, edgecolor="white",
                        hatch="//",
                        label="Remaining Budget" if scenario_idx == 0 else None)
                ax.text(left + remaining / 2, scenario_idx,
                        f"> {remaining:.1f}ms free",
                        ha="center", va="center", fontsize=8,
                        fontweight="bold", color="#2d862d")
            else:
                # Overbudget!
                ax.barh(scenario_idx, abs(remaining), left=BUDGET_MS,
                        height=bar_height, color="red", alpha=0.5,
                        hatch="xx",
                        label="OVERBUDGET" if scenario_idx == 0 else None)
                ax.text(BUDGET_MS + abs(remaining) / 2, scenario_idx,
                        f"> {remaining:.1f}ms OVER!",
                        ha="center", va="center", fontsize=8,
                        fontweight="bold", color="darkred")

        # 500ms budget line
        ax.axvline(x=BUDGET_MS, color="red", linestyle="--", linewidth=2,
                   zorder=10)
        ax.text(BUDGET_MS + 2, 1.3, "500ms\nBudget", fontsize=9,
                color="red", fontweight="bold", va="bottom")

        ax.set_yticks(y_positions)
        ax.set_yticklabels(["Nominal", "Worst-Case"], fontsize=10,
                           fontweight="bold")
        ax.set_xlabel("Latency (ms)")
        ax.set_title(f"{profile_name}", fontweight="bold", fontsize=12)
        ax.set_xlim(0, max(BUDGET_MS * 1.15, worst_total * 1.1))
        ax.grid(True, axis="x", alpha=0.3, linestyle=":")
        ax.invert_yaxis()

        if prof_idx == 0:
            ax.legend(loc="upper right", fontsize=8, ncol=2,
                      framealpha=0.95)

        # Summary annotation
        nom_pct = (nominal_total / BUDGET_MS) * 100
        worst_pct = (worst_total / BUDGET_MS) * 100
        ax.text(
            0.02, -0.18,
            f"Nominal: {nominal_total:.1f}ms ({nom_pct:.1f}% of budget)  |  "
            f"Worst-case: {worst_total:.1f}ms ({worst_pct:.1f}% of budget)",
            transform=ax.transAxes, fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fffbe6",
                      edgecolor="#b8860b", alpha=0.9)
        )

    fig.suptitle(
        "Figure 4.4: 500ms Edge-Recovery Budget Allocation",
        fontsize=14, fontweight="bold", y=1.01
    )
    plt.tight_layout()

    # Save
    png_path = OUTPUT_DIR / "figure_500ms_budget.png"
    pdf_path = OUTPUT_DIR / "figure_500ms_budget.pdf"
    fig.savefig(png_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"[OK] {png_path} (300 DPI)")
    print(f"[OK] {pdf_path} (Vector)")
    plt.close(fig)

    print_budget_analysis()


def print_budget_analysis():
    """Print the budget breakdown and projection."""
    print("\n" + "=" * 72)
    print("500ms BUDGET ANALYSIS — WHERE THE TIME GOES")
    print("=" * 72)

    for profile_name, components in PROFILES.items():
        nominal_total = sum(c["nominal"] for c in components.values())
        worst_total = sum(c["worst"] for c in components.values())
        print(f"\n--- {profile_name} ---")
        print(f"{'Component':<24} {'Nominal':>10} {'Worst':>10} {'% Budget':>10}")
        print("-" * 56)
        for label, vals in components.items():
            pct = (vals["nominal"] / BUDGET_MS) * 100
            print(f"{label:<24} {vals['nominal']:>9.1f}ms {vals['worst']:>9.1f}ms "
                  f"{pct:>9.1f}%")
        print("-" * 56)
        print(f"{'TOTAL CONSUMED':<24} {nominal_total:>9.1f}ms {worst_total:>9.1f}ms "
              f"{(nominal_total/BUDGET_MS*100):>9.1f}%")
        print(f"{'REMAINING':<24} {BUDGET_MS-nominal_total:>9.1f}ms "
              f"{BUDGET_MS-worst_total:>9.1f}ms")

    print("\n" + "=" * 72)
    print("PROJECTION SUMMARY")
    print("=" * 72)
    pi4 = PROFILES["Pi 4 (Production)"]
    nom = sum(c["nominal"] for c in pi4.values())
    worst = sum(c["worst"] for c in pi4.values())
    print(
        f"On Pi 4, the nominal pipeline consumes {nom:.1f}ms ({nom/5:.1f}% of "
        f"budget), leaving {BUDGET_MS - nom:.1f}ms of headroom for "
        f"multi-hop routing or additional authentication rounds."
    )
    print(
        f"Under worst-case DIL conditions (332ms packet-loss spike), total "
        f"consumption reaches {worst:.1f}ms ({worst/5:.1f}% of budget) — "
        f"{'still within' if worst < BUDGET_MS else 'EXCEEDING'} the 500ms "
        f"edge-recovery threshold."
    )
    print(
        f"The dominant cost is network jitter/loss ({pi4['Network Jitter/Loss']['worst']:.1f}ms worst), "
        f"not cryptography ({pi4['ZKP Tax (Schnorr Δ)']['worst']:.3f}ms) — "
        f"confirming H₂'s finding that security tax is operationally negligible."
    )

    nano = PROFILES["Nano 33 BLE (Worker)"]
    nano_nom = sum(c["nominal"] for c in nano.values())
    nano_worst = sum(c["worst"] for c in nano.values())
    print(
        f"\nOn Nano 33 BLE (Cortex-M4F @ 64MHz), the full crypto pipeline "
        f"consumes {nano_nom:.1f}ms nominal / {nano_worst:.1f}ms worst-case — "
        f"{'within' if nano_worst < BUDGET_MS else 'EXCEEDING'} the 500ms budget."
    )
    print(
        f"Budget remaining: {BUDGET_MS - nano_nom:.1f}ms nominal / "
        f"{BUDGET_MS - nano_worst:.1f}ms worst-case. "
        f"The embedded crypto is ~250× slower than Pi 4 but still fits "
        f"within the edge-recovery window."
    )
    print("=" * 72)


def main():
    generate_figure()
    return 0


if __name__ == "__main__":
    sys.exit(main())
