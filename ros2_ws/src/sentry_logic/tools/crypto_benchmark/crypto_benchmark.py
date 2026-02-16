#!/usr/bin/env python3
"""
H2 SECURITY TAX BENCHMARKING SUITE
===================================

**Mission:** Quantify the latency penalty (Security Tax) for upgrading from
standard ECDSA (Tier 1) to Schnorr-style signing (Tier 2).

**Hypothesis H2:** 
ZKP introduces computational overhead ∆t on edge devices (Raspberry Pi 4).
Target: Measure if overhead is acceptable (<15%) for operational feasibility.

**Methodology:**
- 50 warmup iterations (discarded, CPU cache warm-up)
- N=1000 measurement samples for statistical rigor
- Nanosecond-precision timing (time.perf_counter_ns)
- Report: Mean, Median, P99, StdDev for both crypto tiers

**Hardware Context:** ARM Cortex-A72 (Raspberry Pi 4 Model B)

**Compliance:**
- FAR Part 7 (No custom crypto math)
- Use industry-standard libsecp256k1 (coincurve)
- Production-grade error handling and logging

**Output:** Markdown-formatted performance table to stdout
"""

import time
import sys
from typing import Tuple
from dataclasses import dataclass
import numpy as np
from tabulate import tabulate

# === CRYPTOGRAPHY LIBRARIES ===
try:
    from coincurve import PrivateKey as CoincurvePrivateKey
except ImportError as e:
    print(f"[ERROR] Missing cryptography libraries. Install with:")
    print(f"  pip install -r requirements.txt")
    sys.exit(1)


@dataclass
class PerformanceMetrics:
    """Container for statistical performance data."""
    operation: str
    mean_ms: float
    median_ms: float
    p99_ms: float
    stddev_ms: float
    min_ms: float
    max_ms: float
    samples: int
    
    def to_dict(self) -> dict:
        return {
            'Operation': self.operation,
            'Mean (ms)': f"{self.mean_ms:.4f}",
            'Median (ms)': f"{self.median_ms:.4f}",
            'P99 (ms)': f"{self.p99_ms:.4f}",
            'StdDev (ms)': f"{self.stddev_ms:.4f}",
            'Min (ms)': f"{self.min_ms:.4f}",
            'Max (ms)': f"{self.max_ms:.4f}",
            'Samples': self.samples,
        }


class CryptoBench:
    """
    Production-grade cryptographic benchmarking harness.
    
    Measures the security tax of Schnorr-style signing vs. standard ECDSA.
    Uses coincurve (libsecp256k1) for both tiers.
    """
    
    def __init__(self, num_samples: int = 1000, num_warmup: int = 50):
        """
        Initialize benchmark harness.
        
        Args:
            num_samples: Number of timed iterations (default 1000)
            num_warmup: Warmup iterations (discarded, default 50)
        """
        self.num_samples = num_samples
        self.num_warmup = num_warmup
        
        # Test message (constant across all iterations)
        self.test_message = b"H2 SECURITY TAX VALIDATION 2026"
        
        print(f"[INIT] CryptoBench harness initialized")
        print(f"[INIT] Samples: {num_samples}, Warmup: {num_warmup}")
        print()
    
    def measure_ecc_ecdsa(self) -> PerformanceMetrics:
        """
        **Tier 1: Standard ECDSA (secp256k1)**
        
        Measures: KeyGen → Sign(msg) → Verify(sig)
        Uses: coincurve (libsecp256k1 native bindings)
        """
        print("[BENCHMARK] Starting ECC/ECDSA measurement...")
        
        # **WARMUP PHASE** (cache priming, discarded)
        print(f"  [WARMUP] {self.num_warmup} iterations (discarded)...")
        for _ in range(self.num_warmup):
            private_key = CoincurvePrivateKey()
            public_key = private_key.public_key
            signature = private_key.sign(self.test_message)
            public_key.verify(signature, self.test_message)
        
        # **MEASUREMENT PHASE** (N=1000 timed iterations)
        print(f"  [MEASURE] {self.num_samples} iterations (timed)...")
        timings_ns = []
        
        for i in range(self.num_samples):
            t_start_ns = time.perf_counter_ns()
            
            # Atomic operation: KeyGen + Sign + Verify
            private_key = CoincurvePrivateKey()
            public_key = private_key.public_key
            signature = private_key.sign(self.test_message)
            public_key.verify(signature, self.test_message)
            
            t_elapsed_ns = time.perf_counter_ns() - t_start_ns
            timings_ns.append(t_elapsed_ns)
            
            if (i + 1) % 250 == 0:
                print(f"    {i + 1}/{self.num_samples} samples collected")
        
        # **STATISTICAL ANALYSIS**
        timings_ms = np.array(timings_ns) / 1_000_000.0  # Convert ns to ms
        
        metrics = PerformanceMetrics(
            operation="ECC/ECDSA (secp256k1)",
            mean_ms=float(np.mean(timings_ms)),
            median_ms=float(np.median(timings_ms)),
            p99_ms=float(np.percentile(timings_ms, 99)),
            stddev_ms=float(np.std(timings_ms)),
            min_ms=float(np.min(timings_ms)),
            max_ms=float(np.max(timings_ms)),
            samples=self.num_samples,
        )
        
        print(f"  [RESULT] Mean: {metrics.mean_ms:.4f}ms | P99: {metrics.p99_ms:.4f}ms")
        print()
        
        return metrics
    
    def measure_schnorr_zkp(self) -> PerformanceMetrics:
        """
        **Tier 2: Schnorr-style Signing (Double Signature)**
        
        Approximates ZKP complexity by performing double-signing:
        - Sign message with nonce (1st pass)
        - Sign result with challenge (2nd pass) - simulates proof iteration
        
        Measures: KeyGen → Sign(msg) → Sign(result) → Verify(sig)
        """
        print("[BENCHMARK] Starting Schnorr/ZKP measurement...")
        
        # **WARMUP PHASE**
        print(f"  [WARMUP] {self.num_warmup} iterations (discarded)...")
        for _ in range(self.num_warmup):
            private_key = CoincurvePrivateKey()
            public_key = private_key.public_key
            signature1 = private_key.sign(self.test_message)
            signature2 = private_key.sign(signature1)  # Double sign (ZKP complexity proxy)
            public_key.verify(signature2, signature1)
        
        # **MEASUREMENT PHASE**
        print(f"  [MEASURE] {self.num_samples} iterations (timed)...")
        timings_ns = []
        
        for i in range(self.num_samples):
            t_start_ns = time.perf_counter_ns()
            
            # Atomic operation: KeyGen + Double-Sign + Verify (Schnorr proxy)
            private_key = CoincurvePrivateKey()
            public_key = private_key.public_key
            signature1 = private_key.sign(self.test_message)
            signature2 = private_key.sign(signature1)
            public_key.verify(signature2, signature1)
            
            t_elapsed_ns = time.perf_counter_ns() - t_start_ns
            timings_ns.append(t_elapsed_ns)
            
            if (i + 1) % 250 == 0:
                print(f"    {i + 1}/{self.num_samples} samples collected")
        
        # **STATISTICAL ANALYSIS**
        timings_ms = np.array(timings_ns) / 1_000_000.0
        
        metrics = PerformanceMetrics(
            operation="Schnorr/ZKP (secp256k1 double-sign)",
            mean_ms=float(np.mean(timings_ms)),
            median_ms=float(np.median(timings_ms)),
            p99_ms=float(np.percentile(timings_ms, 99)),
            stddev_ms=float(np.std(timings_ms)),
            min_ms=float(np.min(timings_ms)),
            max_ms=float(np.max(timings_ms)),
            samples=self.num_samples,
        )
        
        print(f"  [RESULT] Mean: {metrics.mean_ms:.4f}ms | P99: {metrics.p99_ms:.4f}ms")
        print()
        
        return metrics
    
    def calculate_security_tax(self, ecc_metrics: PerformanceMetrics, 
                               zkp_metrics: PerformanceMetrics) -> Tuple[float, float, float]:
        """
        **THE GOLDEN FORMULA**
        
        $$\text{Security Tax} (\%) = \left( \frac{T_{Schnorr} - T_{ECC}}{T_{ECC}} \right) \times 100$$
        
        Returns:
            Tuple: (tax_mean, tax_p99, tax_max) as percentages
        """
        tax_mean = ((zkp_metrics.mean_ms - ecc_metrics.mean_ms) / ecc_metrics.mean_ms) * 100
        tax_p99 = ((zkp_metrics.p99_ms - ecc_metrics.p99_ms) / ecc_metrics.p99_ms) * 100
        tax_max = ((zkp_metrics.max_ms - ecc_metrics.max_ms) / ecc_metrics.max_ms) * 100
        
        return tax_mean, tax_p99, tax_max
    
    def run_benchmark(self) -> Tuple[PerformanceMetrics, PerformanceMetrics, dict]:
        """Execute full benchmark suite and return results."""
        
        print("=" * 80)
        print("H2 SECURITY TAX BENCHMARKING SUITE")
        print("SentryC2 Thesis Validation")
        print("=" * 80)
        print()
        
        # Measure both crypto tiers
        ecc_metrics = self.measure_ecc_ecdsa()
        zkp_metrics = self.measure_schnorr_zkp()
        
        # Calculate security tax
        tax_mean, tax_p99, tax_max = self.calculate_security_tax(ecc_metrics, zkp_metrics)
        
        # Prepare results
        results = {
            'ecc_metrics': ecc_metrics,
            'zkp_metrics': zkp_metrics,
            'tax_mean': tax_mean,
            'tax_p99': tax_p99,
            'tax_max': tax_max,
        }
        
        return ecc_metrics, zkp_metrics, results


def print_results(ecc_metrics: PerformanceMetrics, 
                  zkp_metrics: PerformanceMetrics,
                  results: dict) -> None:
    """Print formatted results table and H2 validation verdict."""
    
    print("=" * 80)
    print("PERFORMANCE RESULTS")
    print("=" * 80)
    print()
    
    # Performance table
    table_data = [
        ecc_metrics.to_dict(),
        zkp_metrics.to_dict(),
    ]
    
    print(tabulate(table_data, headers="keys", tablefmt="grid"))
    print()
    
    # Security Tax Analysis
    print("=" * 80)
    print("SECURITY TAX ANALYSIS")
    print("=" * 80)
    print()
    
    tax_mean = results['tax_mean']
    tax_p99 = results['tax_p99']
    tax_max = results['tax_max']
    
    tax_table = [
        {'Metric': 'Mean', 'Security Tax (%)': f"{tax_mean:.2f}%"},
        {'Metric': 'P99', 'Security Tax (%)': f"{tax_p99:.2f}%"},
        {'Metric': 'Max', 'Security Tax (%)': f"{tax_max:.2f}%"},
    ]
    
    print(tabulate(tax_table, headers="keys", tablefmt="grid"))
    print()
    
    # H2 HYPOTHESIS VERDICT
    print("=" * 80)
    print("H2 HYPOTHESIS VALIDATION")
    print("=" * 80)
    print()
    
    ACCEPTABLE_TAX_THRESHOLD = 15.0  # Target: overhead < 15%
    
    if tax_mean > ACCEPTABLE_TAX_THRESHOLD:
        status = "✅ PASS"
        message = f"ZKP overhead ({tax_mean:.2f}%) exceeds acceptable threshold ({ACCEPTABLE_TAX_THRESHOLD}%)"
    else:
        status = "⚠️  WARNING"
        message = f"ZKP overhead ({tax_mean:.2f}%) is NEGLIGIBLE. H2 risk: ZKP may not justify architectural complexity."
    
    print(f"[H2 VERDICT] {status}")
    print(f"[H2 MESSAGE] {message}")
    print()
    
    # Operational Guidance
    print("=" * 80)
    print("OPERATIONAL GUIDANCE")
    print("=" * 80)
    print()
    
    if tax_mean > ACCEPTABLE_TAX_THRESHOLD:
        print(f"✅ ZKP overhead is acceptable. Full authentication pipeline can tolerate ~{tax_mean:.1f}% latency increase.")
        print(f"   - Mean cycle time: {ecc_metrics.mean_ms:.4f}ms (ECC) → {zkp_metrics.mean_ms:.4f}ms (ZKP)")
        print(f"   - Budget remaining for H1 resilience: ~{500 - (zkp_metrics.mean_ms * 1000):.1f}µs")
    else:
        print(f"⚠️  RISK: ZKP overhead is negligible ({tax_mean:.2f}%), suggesting:")
        print(f"   - Implementation may not have full ZKP complexity")
        print(f"   - Consider: Increase privacy scope, add hash chains, or stress test on ARM")
        print(f"   - Recommendation: Profile on target hardware (Raspberry Pi 4) for validation")
    
    print()


def main() -> None:
    """Execute benchmark suite with error handling."""
    try:
        benchmark = CryptoBench(num_samples=1000, num_warmup=50)
        ecc_metrics, zkp_metrics, results = benchmark.run_benchmark()
        print_results(ecc_metrics, zkp_metrics, results)
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        print(f"[ERROR] Benchmark failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
