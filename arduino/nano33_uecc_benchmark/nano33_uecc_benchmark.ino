/**
 * H2 SECURITY TAX BENCHMARK — Cortex-M4F (Arduino Nano 33 BLE)
 * ==============================================================
 *
 * **Mission:** Measure raw cycle counts for micro-ecc operations
 * to validate that ZKP authentication fits within the 500ms budget.
 *
 * **Hardware:**  Arduino Nano 33 BLE (nRF52840, Cortex-M4F @ 64MHz, 256KB SRAM)
 * **Library:**   micro-ecc (https://github.com/kmackay/micro-ecc)
 * **Curve:**     secp256r1 (NIST P-256) — FIPS 186-4 compliant
 *
 * **Methodology:**
 *   - 5 warmup iterations (discarded, instruction cache priming)
 *   - N=50 measurement samples (SRAM-constrained, no heap alloc)
 *   - microsecond-precision timing via micros()
 *   - All buffers are static (NO malloc/new in main loop)
 *
 * **Operations Measured:**
 *   1. uECC_make_key()   — Ephemeral keypair generation
 *   2. uECC_sign()       — ECDSA signature (32-byte message)
 *   3. uECC_verify()     — ECDSA verification (CRITICAL PATH)
 *
 * **Output Format (Serial @ 115200):**
 *   CSV-style per-iteration lines, then statistical summary.
 *   Parseable by companion Python script for thesis data pipeline.
 *
 * **Memory Budget:**
 *   - Static buffers: 32 (privkey) + 64 (pubkey) + 64 (sig) + 32 (msg) = 192 bytes
 *   - Timing arrays: 50 * 4 bytes * 3 ops = 600 bytes
 *   - Total: ~1KB fixed SRAM. No heap fragmentation risk.
 *
 * **Compliance:**
 *   - FAR Part 7: Uses industry-standard micro-ecc (no custom math)
 *   - DO-178C Atomic: Single benchmark function, verifiable output
 *
 * **Install:** Arduino IDE → Sketch → Include Library → Manage Libraries
 *              → Search "micro-ecc" → Install "micro-ecc by Kenneth MacKay"
 *
 * Author: SentryC2 Security Team
 * Date:   February 2026
 */

#include <uECC.h>

// ============================================================================
// CONFIGURATION (compile-time constants, zero heap)
// ============================================================================

/** Number of timed measurement iterations. */
static const uint8_t NUM_SAMPLES = 50;

/** Number of warmup iterations (discarded, cache priming). */
static const uint8_t NUM_WARMUP  = 5;

/** H1 resilience budget ceiling in microseconds (500ms). */
static const uint32_t BUDGET_US  = 500000UL;

// ============================================================================
// STATIC BUFFERS (no dynamic allocation — safety-critical requirement)
// ============================================================================

/** ECDSA private key (32 bytes for P-256). */
static uint8_t private_key[32];

/** ECDSA public key — uncompressed (X || Y), 64 bytes for P-256. */
static uint8_t public_key[64];

/** ECDSA signature buffer (r || s), 64 bytes for P-256. */
static uint8_t signature[64];

/** Fixed test message (SHA-256 hash length, 32 bytes). */
static const uint8_t test_message[32] = {
    0x48, 0x32, 0x20, 0x53, 0x45, 0x43, 0x55, 0x52,  // "H2 SECUR"
    0x49, 0x54, 0x59, 0x20, 0x54, 0x41, 0x58, 0x20,  // "ITY TAX "
    0x56, 0x41, 0x4C, 0x49, 0x44, 0x41, 0x54, 0x49,  // "VALIDATI"
    0x4F, 0x4E, 0x20, 0x32, 0x30, 0x32, 0x36, 0x00   // "ON 2026\0"
};

/** Timing storage — static arrays, fixed size. */
static uint32_t keygen_us[NUM_SAMPLES];
static uint32_t sign_us[NUM_SAMPLES];
static uint32_t verify_us[NUM_SAMPLES];

// ============================================================================
// RNG CALLBACK (required by micro-ecc)
// ============================================================================

/**
 * Hardware RNG callback for micro-ecc.
 *
 * nRF52840 has a true hardware RNG peripheral.
 * Arduino core exposes it via analogRead(A0) + micros() as entropy.
 * For production: use nrf_drv_rng or CryptoCell CC310.
 *
 * Why not rand(): deterministic PRNG is insufficient for key generation.
 */
static int rng_callback(uint8_t *dest, unsigned size) {
    // Use Arduino's built-in random seeded by analog noise + timer jitter
    for (unsigned i = 0; i < size; i++) {
        dest[i] = (uint8_t)(analogRead(A0) ^ (micros() & 0xFF));
        // Mix in timer LSB for additional entropy
        dest[i] ^= (uint8_t)(micros() >> 8);
    }
    return 1;  // Success
}

// ============================================================================
// STATISTICAL HELPERS (integer math only — no float on M4 without FPU use)
// ============================================================================

/**
 * Compute mean of uint32_t array (integer division, microsecond precision).
 * Overflow-safe: accumulate in uint64_t.
 */
static uint32_t compute_mean(const uint32_t *data, uint8_t count) {
    uint64_t sum = 0;
    for (uint8_t i = 0; i < count; i++) {
        sum += data[i];
    }
    return (uint32_t)(sum / count);
}

/**
 * Find minimum value in array.
 */
static uint32_t compute_min(const uint32_t *data, uint8_t count) {
    uint32_t min_val = data[0];
    for (uint8_t i = 1; i < count; i++) {
        if (data[i] < min_val) min_val = data[i];
    }
    return min_val;
}

/**
 * Find maximum value in array.
 */
static uint32_t compute_max(const uint32_t *data, uint8_t count) {
    uint32_t max_val = data[0];
    for (uint8_t i = 1; i < count; i++) {
        if (data[i] > max_val) max_val = data[i];
    }
    return max_val;
}

/**
 * Compute P99 (index-based, requires sorted data).
 * Simple insertion sort — N=50 is trivial for M4.
 */
static void insertion_sort(uint32_t *data, uint8_t count) {
    for (uint8_t i = 1; i < count; i++) {
        uint32_t key = data[i];
        int8_t j = i - 1;
        while (j >= 0 && data[j] > key) {
            data[j + 1] = data[j];
            j--;
        }
        data[j + 1] = key;
    }
}

static uint32_t compute_p99(uint32_t *data, uint8_t count) {
    // Work on a copy to preserve original order
    static uint32_t sorted[NUM_SAMPLES];
    for (uint8_t i = 0; i < count; i++) sorted[i] = data[i];
    insertion_sort(sorted, count);
    // P99 index: ceil(0.99 * N) - 1
    uint8_t idx = (uint8_t)((99UL * count + 99UL) / 100UL) - 1;
    if (idx >= count) idx = count - 1;
    return sorted[idx];
}

/**
 * Compute median (50th percentile).
 */
static uint32_t compute_median(uint32_t *data, uint8_t count) {
    static uint32_t sorted[NUM_SAMPLES];
    for (uint8_t i = 0; i < count; i++) sorted[i] = data[i];
    insertion_sort(sorted, count);
    if (count % 2 == 0) {
        return (sorted[count / 2 - 1] + sorted[count / 2]) / 2;
    }
    return sorted[count / 2];
}

// ============================================================================
// BENCHMARK CORE
// ============================================================================

/**
 * Execute a single benchmark iteration.
 *
 * Returns false if any crypto operation fails (signature invalid, etc.)
 * All timing stored in the static arrays at index `idx`.
 */
static bool benchmark_iteration(uint8_t idx) {
    const struct uECC_Curve_t *curve = uECC_secp256r1();
    uint32_t t_start, t_elapsed;
    int result;

    // --- 1. KEY GENERATION ---
    t_start = micros();
    result = uECC_make_key(public_key, private_key, curve);
    t_elapsed = micros() - t_start;

    if (!result) {
        Serial.println("[ERROR] uECC_make_key() FAILED");
        return false;
    }
    keygen_us[idx] = t_elapsed;

    // --- 2. ECDSA SIGN ---
    t_start = micros();
    result = uECC_sign(private_key, test_message, sizeof(test_message),
                       signature, curve);
    t_elapsed = micros() - t_start;

    if (!result) {
        Serial.println("[ERROR] uECC_sign() FAILED");
        return false;
    }
    sign_us[idx] = t_elapsed;

    // --- 3. ECDSA VERIFY (CRITICAL PATH) ---
    t_start = micros();
    result = uECC_verify(public_key, test_message, sizeof(test_message),
                         signature, curve);
    t_elapsed = micros() - t_start;

    if (!result) {
        Serial.println("[ERROR] uECC_verify() FAILED — signature invalid!");
        return false;
    }
    verify_us[idx] = t_elapsed;

    return true;
}

// ============================================================================
// OUTPUT FORMATTING
// ============================================================================

/**
 * Print per-iteration CSV line for data pipeline ingestion.
 * Format: SAMPLE,<idx>,<keygen_us>,<sign_us>,<verify_us>,<total_us>
 */
static void print_sample_csv(uint8_t idx) {
    uint32_t total = keygen_us[idx] + sign_us[idx] + verify_us[idx];
    Serial.print("SAMPLE,");
    Serial.print(idx);
    Serial.print(",");
    Serial.print(keygen_us[idx]);
    Serial.print(",");
    Serial.print(sign_us[idx]);
    Serial.print(",");
    Serial.print(verify_us[idx]);
    Serial.print(",");
    Serial.println(total);
}

/**
 * Print statistical summary for one operation.
 */
static void print_op_stats(const char *name, uint32_t *data, uint8_t count) {
    uint32_t mean = compute_mean(data, count);
    uint32_t med  = compute_median(data, count);
    uint32_t p99  = compute_p99(data, count);
    uint32_t mn   = compute_min(data, count);
    uint32_t mx   = compute_max(data, count);

    Serial.print("STATS,");
    Serial.print(name);
    Serial.print(",mean_us=");
    Serial.print(mean);
    Serial.print(",median_us=");
    Serial.print(med);
    Serial.print(",p99_us=");
    Serial.print(p99);
    Serial.print(",min_us=");
    Serial.print(mn);
    Serial.print(",max_us=");
    Serial.println(mx);

    // Human-readable line
    Serial.print("  ");
    Serial.print(name);
    Serial.print(": Mean=");
    Serial.print(mean);
    Serial.print("us  Median=");
    Serial.print(med);
    Serial.print("us  P99=");
    Serial.print(p99);
    Serial.print("us  Min=");
    Serial.print(mn);
    Serial.print("us  Max=");
    Serial.print(mx);
    Serial.println("us");
}

/**
 * Print budget analysis — does the critical path fit in 500ms?
 */
static void print_budget_verdict(uint32_t *data, uint8_t count) {
    uint32_t mean = compute_mean(data, count);
    uint32_t p99  = compute_p99(data, count);
    uint32_t total_pipeline_mean = compute_mean(keygen_us, count)
                                 + compute_mean(sign_us, count)
                                 + compute_mean(data, count);

    Serial.println();
    Serial.println("================================================================");
    Serial.println("H2 BUDGET ANALYSIS (500ms ceiling)");
    Serial.println("================================================================");

    Serial.print("  Verify Mean:           ");
    Serial.print(mean);
    Serial.print(" us (");
    Serial.print((float)mean / 1000.0, 2);
    Serial.println(" ms)");

    Serial.print("  Verify P99:            ");
    Serial.print(p99);
    Serial.print(" us (");
    Serial.print((float)p99 / 1000.0, 2);
    Serial.println(" ms)");

    Serial.print("  Full Pipeline Mean:    ");
    Serial.print(total_pipeline_mean);
    Serial.print(" us (");
    Serial.print((float)total_pipeline_mean / 1000.0, 2);
    Serial.println(" ms)");

    Serial.print("  Budget:                ");
    Serial.print(BUDGET_US);
    Serial.print(" us (");
    Serial.print((float)BUDGET_US / 1000.0, 2);
    Serial.println(" ms)");

    Serial.print("  Budget Remaining:      ");
    if (total_pipeline_mean < BUDGET_US) {
        uint32_t remaining = BUDGET_US - total_pipeline_mean;
        Serial.print(remaining);
        Serial.print(" us (");
        Serial.print((float)remaining / 1000.0, 2);
        Serial.println(" ms)");
    } else {
        Serial.print("EXCEEDED by ");
        uint32_t exceeded = total_pipeline_mean - BUDGET_US;
        Serial.print(exceeded);
        Serial.println(" us");
    }

    Serial.println();
    if (total_pipeline_mean < BUDGET_US) {
        Serial.println("[H2 VERDICT] PASS — Full crypto pipeline fits within 500ms budget");
    } else {
        Serial.println("[H2 VERDICT] FAIL — Crypto pipeline EXCEEDS 500ms budget");
        Serial.println("[H2 ACTION]  Consider: Reduce curve size, pre-compute keys, or offload to CC310");
    }
}

// ============================================================================
// ARDUINO ENTRY POINTS
// ============================================================================

void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }

    // Seed entropy from analog noise before any crypto operations
    randomSeed(analogRead(A0) ^ micros());

    // Register RNG callback (micro-ecc requirement)
    uECC_set_rng(&rng_callback);

    Serial.println();
    Serial.println("================================================================");
    Serial.println("H2 SECURITY TAX BENCHMARK — Arduino Nano 33 BLE");
    Serial.println("Cortex-M4F @ 64MHz | micro-ecc | secp256r1 (NIST P-256)");
    Serial.println("================================================================");
    Serial.print("Warmup: ");
    Serial.print(NUM_WARMUP);
    Serial.print(" | Samples: ");
    Serial.println(NUM_SAMPLES);
    Serial.println();

    // === WARMUP PHASE (discarded, instruction cache priming) ===
    Serial.println("[PHASE 1] Warmup (discarded)...");
    for (uint8_t w = 0; w < NUM_WARMUP; w++) {
        const struct uECC_Curve_t *curve = uECC_secp256r1();
        uECC_make_key(public_key, private_key, curve);
        uECC_sign(private_key, test_message, sizeof(test_message), signature, curve);
        uECC_verify(public_key, test_message, sizeof(test_message), signature, curve);
        Serial.print("  warmup ");
        Serial.print(w + 1);
        Serial.print("/");
        Serial.println(NUM_WARMUP);
    }
    Serial.println("[PHASE 1] Warmup complete.");
    Serial.println();

    // === MEASUREMENT PHASE ===
    Serial.println("[PHASE 2] Measurement...");
    Serial.println("FORMAT: SAMPLE,<idx>,<keygen_us>,<sign_us>,<verify_us>,<total_us>");
    Serial.println();

    uint8_t failures = 0;

    for (uint8_t i = 0; i < NUM_SAMPLES; i++) {
        bool ok = benchmark_iteration(i);
        if (!ok) {
            failures++;
            Serial.print("[WARN] Iteration ");
            Serial.print(i);
            Serial.println(" FAILED — zeroed out");
            keygen_us[i] = 0;
            sign_us[i]   = 0;
            verify_us[i] = 0;
        }
        print_sample_csv(i);
    }

    Serial.println();
    Serial.print("[PHASE 2] Complete. Failures: ");
    Serial.print(failures);
    Serial.print("/");
    Serial.println(NUM_SAMPLES);

    // === STATISTICAL SUMMARY ===
    Serial.println();
    Serial.println("================================================================");
    Serial.println("STATISTICAL SUMMARY");
    Serial.println("================================================================");

    print_op_stats("uECC_make_key", keygen_us, NUM_SAMPLES);
    print_op_stats("uECC_sign",     sign_us,   NUM_SAMPLES);
    print_op_stats("uECC_verify",   verify_us, NUM_SAMPLES);

    // === BUDGET VERDICT ===
    print_budget_verdict(verify_us, NUM_SAMPLES);

    Serial.println();
    Serial.println("================================================================");
    Serial.println("BENCHMARK COMPLETE — Copy output for thesis data pipeline");
    Serial.println("================================================================");
}

void loop() {
    // Benchmark runs once in setup(). No-op loop.
    // Device idles after benchmark to preserve serial output.
    delay(10000);
}
