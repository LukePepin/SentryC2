#!/bin/bash
# H2 Security Tax Benchmark Launch Script
# Validates cryptographic performance on target hardware

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[LAUNCH] Starting H2 Crypto Benchmark from: $SCRIPT_DIR"
echo ""

# Step 1: Install dependencies
echo "[STEP 1] Installing cryptographic dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "[STEP 1] ✅ Dependencies installed"
echo ""

# Step 2: Run benchmark
# Use -u (unbuffered) and explicit path to prevent VS Code REPL interception
echo "[STEP 2] Executing H2 Security Tax Benchmark..."
/usr/bin/python3 -u "$SCRIPT_DIR/crypto_benchmark.py"
RESULT=$?
echo ""

if [ $RESULT -eq 0 ]; then
    echo "[LAUNCH] ✅ Benchmark completed successfully"
    exit 0
else
    echo "[LAUNCH] ❌ Benchmark failed with exit code $RESULT"
    exit 1
fi
