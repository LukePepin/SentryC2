# URDF Import Instructions for Niryo One Robot

## Current Status
- Unity Version: 6000.3.3f1 (Unity 6)
- URDF Importer: Latest from GitHub
- Physics Solver: ✅ Set to Temporal Gauss Seidel (Type 1)
- URDF File Location: `Assets/URDF/niryo_one/niryo_one.urdf`
- File Ownership: ✅ Fixed for host user (UID 1000)

## ⚠️ IMPORTANT: Container/Host Environment
This project is accessed from a Docker container while Unity runs on the host.
File ownership has been corrected to UID 1000 (host user) to prevent permission conflicts.

## Import Steps

### 1. **In Unity Editor:**
   - Open the scene where you want the robot
   - Make sure only ONE scene is open in the Hierarchy

### 2. **Import the URDF:**
   
   **Method A - Right-click Import (Recommended):**
   1. In Project window, navigate to `Assets/URDF/niryo_one/`
   2. Find `niryo_one.urdf` file
   3. **Right-click** on it
   4. Select **"Import Robot from Selected URDF file"**
   
   **Method B - Menu Import:**
   1. Select `niryo_one.urdf` in Project window
   2. Go to top menu: **Assets → Import Robot from URDF**

### 3. **Import Settings:**
   When the import window appears, use these settings:
   - **Axis Type:** Y Axis ✅
   - **Mesh Decomposer:** VHACD ✅
   - **Overwrite Existing Prefabs:** Check if reimporting
   - Click **"Import URDF"**

### 4. **Post-Import Configuration:**
   After import completes successfully:
   
   1. Select `niryo_one` GameObject in Hierarchy
   2. In Inspector, find **Controller (Script)** component
   3. Set these values:
      - Stiffness: `10000`
      - Damping: `100`
      - Force Limit: `1000`
      - Speed: `30`
      - Acceleration: `10`
   
   4. Expand the robot hierarchy: `niryo_one → world → base_link`
   5. Select `base_link`
   6. Toggle **"Immovable"** checkbox ON

### 5. **Test the Import:**
   - Press Play button
   - Robot should stay stable on the ground
   - No errors in Console
   - Use arrow keys to control joints:
     - Left/Right: Select joint
     - Up/Down: Move selected joint

## Troubleshooting

### Import Hangs or "Moving file failed" Error

**If you see:** `Moving file failed, moving Temp/assetCreatPath to Assets/URDF/...`

**Root Cause:** File ownership mismatch between container (root) and host user.

**Solutions:**
```bash
# Run in terminal from workspace root:
cd /workspace/Sentry_Simulation

# 1. Fix file ownership (CRITICAL for container/host setup)
# Replace 1000:1000 with your host user UID:GID if different
chown -R 1000:1000 Assets/ Packages/ ProjectSettings/ UserSettings/ Library/ Logs/ Temp/

# 2. Remove stuck temp file
rm -f Temp/assetCreatePath

# 3. Clean up partial imports
rm -rf Assets/URDF/niryo_one/niryo_one_urdf/meshes/stl/*.asset
rm -rf Assets/URDF/niryo_one/niryo_one_urdf/meshes/stl/*.prefab
rm -rf Assets/URDF/niryo_one/niryo_one_urdf/meshes/collada/*.asset

# 4. Fix permissions
cd Assets/URDF
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;

# 5. Clear Materials folder
rm -rf niryo_one/Materials/*
```

Then **restart Unity** and try importing again.

### Container/Host File Ownership Issues

**Symptoms:**
- "Permission denied" errors
- "Moving file failed" errors
- Asset import hangs indefinitely
- Unity can't save scenes or prefabs

**Solution:**
When working in a container while Unity runs on host, all Unity project files must be owned by the host user:

```bash
# From inside the container, run:
cd /workspace/Sentry_Simulation
chown -R 1000:1000 Assets/ Packages/ Library/ Logs/ ProjectSettings/ UserSettings/ Temp/

# To find your host UID:
stat -c "UID: %u GID: %g" /workspace
```

**Prevention:**
After creating/modifying files from the container, always run the chown command above.

### Robot Falls Through Floor or Joints Are Wobbly

**Check:**
1. Physics Settings (Edit → Project Settings → Physics)
   - Solver Type MUST be: **Temporal Gauss Seidel** (not Default PGS)
2. Controller values on niryo_one GameObject
   - Stiffness: 10000
   - Damping: 100
3. base_link must have "Immovable" checked

### Package Not Found Errors

**Update packages:**
```bash
# Edit Packages/manifest.json and ensure:
"com.unity.robotics.urdf-importer": "https://github.com/Unity-Technologies/URDF-Importer.git?path=/com.unity.robotics.urdf-importer"
```

Then in Unity: Window → Package Manager → Click "Refresh"

## Unity 6 Known Issues

Unity 6 introduced breaking changes to ArticulationBody system:
- Some older URDF Importers may not work correctly
- Latest version from GitHub main branch recommended
- Physics solver MUST be set to Temporal Gauss Seidel

## Resources

- [URDF Importer Documentation](https://github.com/Unity-Technologies/URDF-Importer)
- [Unity Articulation Body Manual](https://docs.unity3d.com/Manual/class-ArticulationBody.html)
- [Pick and Place Tutorial](https://github.com/Unity-Technologies/Unity-Robotics-Hub/tree/master/tutorials/pick_and_place)
