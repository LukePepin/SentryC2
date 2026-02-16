# Test Data Directory (Local Only)

**EXCLUDED FROM GITHUB**

This directory stores experimental test results and telemetry data:
- H3 Boot Storm validation CSV files (`h3_test_n*_*.csv`)
- Baseline performance metrics
- Raw sensor data from chaos engineering tests

## Post-Test Protocol
**CRITICAL:** After completing test campaigns, **email all CSV results** to the full data repository on your PC for long-term archival and analysis.

## Directory Structure
```
data/
├── h3_test_n1_YYYYMMDD_HHMMSS.csv      # Baseline (n=1)
├── h3_test_n3_YYYYMMDD_HHMMSS.csv      # Linear scaling (n=3)
├── h3_test_n5_YYYYMMDD_HHMMSS.csv      # Linear scaling (n=5)
├── h3_test_n10_YYYYMMDD_HHMMSS.csv     # Boot Storm (n=10)
└── h3_test_n20_YYYYMMDD_HHMMSS.csv     # Boot Storm (n=20)
```

## Data Format
See `tests/livelock_sim.py` for CSV schema:
- `node_id`, `request_sent_ts`, `response_received_ts`, `latency_ms`, `status`, `zkp_hash`
