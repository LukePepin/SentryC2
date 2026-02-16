#!/bin/bash
# ============================================================================
# Docker Reproducibility Verification Script
# Purpose: Verify bitwise-identical builds for DO-178C certification
# ============================================================================

set -e

WORKSPACE="/workspace"
BUILD_DIR="${WORKSPACE}/builds"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BUILD_DIR}/reproducibility_${TIMESTAMP}.log"

echo "================================================================================="
echo "SentryC2 Docker Reproducibility Verification"
echo "================================================================================="
echo "Date: $(date)"
echo "Log: ${LOG_FILE}"
echo ""

# Create builds directory
mkdir -p "${BUILD_DIR}"

# ============================================================================
# Function: Build Docker image and capture metadata
# ============================================================================
build_image() {
    local build_num=$1
    local image_name="sentry-c2:repro-${build_num}"
    
    echo "[Build ${build_num}] Starting Docker build..."
    echo "Image: ${image_name}"
    
    cd "${WORKSPACE}"
    
    # Build image with consistent settings
    docker build \
        --tag "${image_name}" \
        --file Dockerfile \
        --build-arg ROS_DISTRO=humble \
        --no-cache \
        . 2>&1 | tee -a "${LOG_FILE}"
    
    # Extract image SHA256
    local image_id=$(docker image inspect "${image_name}" --format='{{.ID}}')
    local image_sha=$(echo "${image_id}" | sed 's/sha256://')
    
    echo "[Build ${build_num}] Image SHA256: ${image_sha}"
    echo "${image_sha}" > "${BUILD_DIR}/build_${build_num}.sha256"
    
    return 0
}

# ============================================================================
# Function: Verify image reproducibility
# ============================================================================
verify_reproducibility() {
    echo ""
    echo "================================================================================="
    echo "Reproducibility Verification"
    echo "================================================================================="
    
    if [ ! -f "${BUILD_DIR}/build_1.sha256" ] || [ ! -f "${BUILD_DIR}/build_2.sha256" ]; then
        echo "ERROR: Missing build SHA256 files"
        return 1
    fi
    
    local sha1=$(cat "${BUILD_DIR}/build_1.sha256")
    local sha2=$(cat "${BUILD_DIR}/build_2.sha256")
    
    echo "Build 1 SHA256: ${sha1}"
    echo "Build 2 SHA256: ${sha2}"
    
    if [ "${sha1}" == "${sha2}" ]; then
        echo ""
        echo "✅ SUCCESS: Docker images are bitwise identical!"
        echo "✅ Reproducible build verified for DO-178C certification"
        return 0
    else
        echo ""
        echo "❌ FAILURE: Docker images differ!"
        echo "❌ This may indicate non-deterministic build steps"
        echo ""
        echo "Possible causes:"
        echo "  1. Timestamp in package metadata (.git, timestamps)"
        echo "  2. Network-dependent package installation (use --require-hashes)"
        echo "  3. Docker layer cache inconsistency (use --no-cache)"
        echo "  4. Random seed in build process"
        
        # Run diagnostic
        echo ""
        echo "Diagnostic: Comparing image metadata..."
        docker image inspect sentry-c2:repro-1 --format='{{json .}}' | python3 -m json.tool > "${BUILD_DIR}/image_1_metadata.json"
        docker image inspect sentry-c2:repro-2 --format='{{json .}}' | python3 -m json.tool > "${BUILD_DIR}/image_2_metadata.json"
        
        diff -u "${BUILD_DIR}/image_1_metadata.json" "${BUILD_DIR}/image_2_metadata.json" || true
        
        return 1
    fi
}

# ============================================================================
# Function: Measure build performance
# ============================================================================
measure_build_time() {
    local build_num=$1
    local image_name="sentry-c2:perf-${build_num}"
    
    echo ""
    echo "[Performance] Build ${build_num} timing..."
    
    cd "${WORKSPACE}"
    
    # Measure build time
    local start_time=$(date +%s)
    
    docker build \
        --tag "${image_name}" \
        --file Dockerfile \
        --build-arg ROS_DISTRO=humble \
        --no-cache \
        . > /dev/null 2>&1
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    local image_size=$(docker image inspect "${image_name}" --format='{{.Size}}')
    local image_size_mb=$((image_size / 1048576))
    
    echo "Build time: ${duration}s"
    echo "Image size: ${image_size_mb}MB"
    echo "${duration}" >> "${BUILD_DIR}/build_times.txt"
    
    return 0
}

# ============================================================================
# Main Execution
# ============================================================================

echo "[Step 1/4] Building Docker image (attempt 1)..."
build_image 1

echo ""
echo "[Step 2/4] Building Docker image (attempt 2)..."
build_image 2

echo ""
echo "[Step 3/4] Verifying reproducibility..."
verify_reproducibility
REPRO_RESULT=$?

echo ""
echo "[Step 4/4] Measuring build performance..."
measure_build_time "perf-1"
measure_build_time "perf-2"

# ============================================================================
# Generate Report
# ============================================================================

echo ""
echo "================================================================================="
echo "Reproducibility Report"
echo "================================================================================="
echo "Generated: $(date)" > "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
echo "" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
echo "Build 1 SHA256: $(cat ${BUILD_DIR}/build_1.sha256)" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
echo "Build 2 SHA256: $(cat ${BUILD_DIR}/build_2.sha256)" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
echo "" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"

if [ $REPRO_RESULT -eq 0 ]; then
    echo "Status: ✅ PASS (Reproducible builds verified)" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
    echo "Certification: Ready for DO-178C audit" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
else
    echo "Status: ❌ FAIL (Builds differ)" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
    echo "Action: Investigate non-deterministic steps and retry" >> "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"
fi

cat "${BUILD_DIR}/REPRODUCIBILITY_REPORT.txt"

# ============================================================================
# Cleanup
# ============================================================================
echo ""
echo "Cleaning up temporary images..."
docker image rm sentry-c2:repro-1 sentry-c2:repro-2 sentry-c2:perf-perf-1 sentry-c2:perf-perf-2 2>/dev/null || true

echo ""
echo "================================================================================="
echo "✅ Verification complete. See ${BUILD_DIR} for logs."
echo "================================================================================="

exit $REPRO_RESULT
