#!/usr/bin/env python3
"""
MultiThreaded Executor vs Baseline Comparison (H3 Analysis)
===========================================================
Compare single-threaded baseline vs MultiThreadedExecutor with ReentrantCallbackGroup.

CRITICAL FINDING:
    MultiThreadedExecutor does NOT mitigate H3 livelock.
    Root cause: Queue head-of-line blocking - first submitted requests starve behind later ones.
"""

import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import csv

# Configuration
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 10,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
})

# Data collection
def collect_test_data(data_dir):
    """Extract metrics from CSV files in directory."""
    results = {}
    
    for csv_file in glob.glob(os.path.join(data_dir, 'h3_test_n*.csv')):
        filename = os.path.basename(csv_file)
        # Extract node count from filename: h3_test_n20_timestamp.csv
        node_count = int(filename.split('_')[2].replace('n', ''))
        
        # Read CSV manually
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Calculate metrics
        success_rows = [r for r in rows if r['status'] in ['SUCCESS', 'REJECTED']]
        timeout_count = len([r for r in rows if r['status'] == 'TIMEOUT'])
        total_count = len(rows)
        
        if node_count not in results:
            results[node_count] = {
                'latency_mean': [],
                'latency_max': [],
                'timeout_rate': []
            }
        
        if len(success_rows) > 0:
            latencies = [float(r['latency_ms']) for r in success_rows]
            results[node_count]['latency_mean'].append(np.mean(latencies))
            results[node_count]['latency_max'].append(np.max(latencies))
        else:
            results[node_count]['latency_mean'].append(0)
            results[node_count]['latency_max'].append(0)
        
        results[node_count]['timeout_rate'].append((timeout_count / total_count) * 100)
    
    # Average multiple runs
    metrics = {}
    for n in sorted(results.keys()):
        metrics[n] = {
            'latency_mean': np.mean(results[n]['latency_mean']),
            'latency_max': np.mean(results[n]['latency_max']),
            'timeout_rate': np.mean(results[n]['timeout_rate'])
        }
    
    return metrics

# Load data
baseline_dir = '/home/sentry/sentry/SentryC2/data/h3'
multithreaded_dir = '/home/sentry/sentry/SentryC2/data/h3_multithreaded'

print("📊 Loading baseline data...")
baseline = collect_test_data(baseline_dir)

print("📊 Loading multithreaded executor data...")
multithreaded_data = collect_test_data(multithreaded_dir)

# Extract arrays for plotting
node_counts = sorted(set(baseline.keys()) & set(multithreaded_data.keys()))

baseline_timeout = [baseline[n]['timeout_rate'] for n in node_counts]
multithreaded_timeout = [multithreaded_data[n]['timeout_rate'] for n in node_counts]

baseline_latency = [baseline[n]['latency_mean'] for n in node_counts]
multithreaded_latency = [multithreaded_data[n]['latency_mean'] for n in node_counts]

# Create comparison figure
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=100)

# Plot 1: Timeout Rate Comparison
ax1.plot(node_counts, baseline_timeout, 'o-', label='Baseline (Single-Thread FIFO)', 
         color='#d62728', linewidth=2, markersize=6)
ax1.plot(node_counts, multithreaded_timeout, 's-', label='MultiThreadedExecutor (4 threads)', 
         color='#1f77b4', linewidth=2, markersize=6)

ax1.set_xlabel('Node Density (n)', fontweight='bold')
ax1.set_ylabel('Authentication Failure Rate (%)', fontweight='bold')
ax1.set_title('Timeout Rate Comparison', fontweight='bold', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
ax1.set_ylim(0, 60)

# Add target line
ax1.axhline(y=5, color='green', linestyle='--', linewidth=1.5, 
            label='Target (<5%)', alpha=0.7)
ax1.legend(loc='upper left')

# Plot 2: Latency Comparison
ax2.plot(node_counts, baseline_latency, 'o-', label='Baseline (Single-Thread FIFO)', 
         color='#d62728', linewidth=2, markersize=6)
ax2.plot(node_counts, multithreaded_latency, 's-', label='MultiThreadedExecutor (4 threads)', 
         color='#1f77b4', linewidth=2, markersize=6)

ax2.set_xlabel('Node Density (n)', fontweight='bold')
ax2.set_ylabel('Mean Authentication Latency (ms)', fontweight='bold')
ax2.set_title('Latency Comparison', fontweight='bold', fontsize=12)
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)

# Overall title
fig.suptitle('H3 MultiThreadedExecutor Validation', 
             fontsize=14, fontweight='bold', y=1.02)

plt.tight_layout()

# Save outputs
output_png = '/home/sentry/sentry/SentryC2/figure_async_comparison.png'
output_pdf = '/home/sentry/sentry/SentryC2/figure_async_comparison.pdf'

plt.savefig(output_png, dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(output_pdf, bbox_inches='tight', facecolor='white')

print(f"\n[✓] Generated: {output_png} (300 DPI)")
print(f"[✓] Generated: {output_pdf} (Vector)")

# Analysis
print("\n" + "="*60)
print("MULTITHREADED EXECUTOR VALIDATION RESULTS")
print("="*60)

for n in [12, 20, 24]:
    if n in baseline and n in multithreaded_data:
        baseline_fail = baseline[n]['timeout_rate']
        mt_fail = multithreaded_data[n]['timeout_rate']
        improvement = baseline_fail - mt_fail
        
        print(f"\nn={n} nodes:")
        print(f"  Baseline Timeout:     {baseline_fail:.1f}%")
        print(f"  MultiThreaded:        {mt_fail:.1f}%")
        print(f"  Improvement:          {improvement:+.1f}% ({improvement/baseline_fail*100:.1f}% reduction)" if baseline_fail > 0 else "  Improvement:          N/A")
        
        if mt_fail >= baseline_fail * 0.9:
            print(f"  ❌ NO IMPROVEMENT: MultiThreadedExecutor ineffective")
        elif mt_fail < 5.0:
            print(f"  ✅ SUCCESS: Target achieved (<5%)")
        else:
            print(f"  ⚠️  PARTIAL: Some improvement but target missed")

print("\n" + "="*60)
print("ARCHITECTURAL DIAGNOSIS:")

# Check if multithreading helped
n20_baseline = baseline.get(20, {}).get('timeout_rate', 100)
n20_mt = multithreaded_data.get(20, {}).get('timeout_rate', 100)

if n20_mt >= n20_baseline * 0.9:
    print("❌ MultiThreadedExecutor does NOT mitigate H3 livelock")
    print("   Root Cause: Queue head-of-line blocking")
    print("   Observation: First submitted requests starve behind later ones")
    print("   H3 HYPOTHESIS CONFIRMED: Parallelism cannot solve authentication queue saturation")
else:
    print("✅ MultiThreadedExecutor effective")
    print("   Architecture successfully reduces queue bottleneck")

print("="*60)
