#!/bin/bash
# Unity launcher with correct library paths for URDF importer

export LD_LIBRARY_PATH=/usr/lib:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

echo "Starting Unity with library paths:"
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo ""

# Find Unity editor
UNITY_EDITOR=$(which unity-editor 2>/dev/null)

if [ -z "$UNITY_EDITOR" ]; then
    # Try common Unity Hub installation path
    UNITY_EDITOR="$HOME/Unity/Hub/Editor/*/Editor/Unity"
    UNITY_EDITOR=$(ls -1 $UNITY_EDITOR 2>/dev/null | head -1)
fi

if [ -z "$UNITY_EDITOR" ]; then
    echo "Error: Unity editor not found!"
    echo "Please edit this script and set UNITY_EDITOR path manually"
    exit 1
fi

echo "Launching Unity: $UNITY_EDITOR"
"$UNITY_EDITOR" -projectPath "/workspace/Sentry_Simulation" "$@"
