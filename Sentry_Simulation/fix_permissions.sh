#!/bin/bash
# Fix file ownership for Unity project in container/host environment
# Run this script from inside the container whenever you modify Unity files

set -e

PROJECT_DIR="/workspace/Sentry_Simulation"
HOST_UID=1000
HOST_GID=1000

echo "Fixing file ownership for Unity project..."
echo "Target: UID=$HOST_UID GID=$HOST_GID"

cd "$PROJECT_DIR"

# Fix Unity project directories
echo "Fixing Assets/..."
chown -R $HOST_UID:$HOST_GID Assets/ 2>/dev/null || true

echo "Fixing Packages/..."
chown -R $HOST_UID:$HOST_GID Packages/ 2>/dev/null || true

echo "Fixing ProjectSettings/..."
chown -R $HOST_UID:$HOST_GID ProjectSettings/ 2>/dev/null || true

echo "Fixing UserSettings/..."
chown -R $HOST_UID:$HOST_GID UserSettings/ 2>/dev/null || true

echo "Fixing Library/..."
chown -R $HOST_UID:$HOST_GID Library/ 2>/dev/null || true

echo "Fixing Logs/..."
chown -R $HOST_UID:$HOST_GID Logs/ 2>/dev/null || true

echo "Fixing Temp/..."
chown -R $HOST_UID:$HOST_GID Temp/ 2>/dev/null || true

echo "✓ File ownership fixed!"
echo ""
echo "Summary:"
ls -ld Assets Packages ProjectSettings Library 2>/dev/null | awk '{print $3":"$4" "$9}'
