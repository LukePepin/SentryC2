# Fixing Niryo One Robot Materials in Unity 6

## Why Is the Robot Pink?

Pink/magenta color in Unity means **missing or broken material references**. The URDF Importer created materials, but Unity 6's URP (Universal Render Pipeline) requires specific material setup.

## Quick Fix: Create URP Materials

### Option 1: Convert to URP Materials (Recommended)

1. **Select all imported robot parts:**
   - In Hierarchy: Expand `niryo_one → world → base_link` and all child links
   - Or in Project: Navigate to `Assets/URDF/niryo_one/Materials/`

2. **Convert materials to URP:**
   - Top menu: **Edit → Rendering → Materials → Convert Selected Built-in Materials to URP**
   - Or: **Edit → Rendering → Materials → Convert All Built-in Materials to URP**

3. **Verify the change:**
   - Select `Default.mat` in `Assets/URDF/niryo_one/Materials/`
   - In Inspector, Shader should now be: **Universal Render Pipeline/Lit**

### Option 2: Create Custom Materials Manually

If conversion doesn't work, create materials from scratch:

1. **Create new material:**
   - In Project window: `Assets/URDF/niryo_one/Materials/`
   - Right-click → **Create → Material**
   - Name it `NiryoMaterial`

2. **Configure for URP:**
   - Select the material
   - In Inspector:
     - **Shader:** Universal Render Pipeline/Lit
     - **Surface Type:** Opaque
     - **Base Map:** Choose a color (e.g., dark gray RGB: 0.3, 0.3, 0.3)
     - **Metallic:** 0.5
     - **Smoothness:** 0.5

3. **Apply to robot:**
   - In Hierarchy, select `niryo_one`
   - In Inspector, find each link's Mesh Renderer components
   - Drag your new `NiryoMaterial` to the Material slot

### Option 3: Use Simple Colors

For quick testing without worrying about appearance:

1. **Create colored materials:**
   ```
   Assets/URDF/niryo_one/Materials/
   - RobotGray.mat  → URP/Lit, Color: (0.3, 0.3, 0.3)
   - RobotBlack.mat → URP/Lit, Color: (0.1, 0.1, 0.1)
   - RobotWhite.mat → URP/Lit, Color: (0.8, 0.8, 0.8)
   ```

2. **Apply to different parts:**
   - Base: Gray
   - Joints: Black
   - Links: White or Gray

## Fix the Default Material

The existing `Default.mat` likely uses the wrong shader:

1. **Select** `Assets/URDF/niryo_one/Materials/Default.mat`
2. **In Inspector:**
   - Current Shader: Probably "Standard" or "Built-in"
   - Change to: **Universal Render Pipeline/Lit**
3. **Set Base Color:** Dark gray (0.3, 0.3, 0.3, 1.0)

## Expected Result

After fixing materials, the robot should appear with proper gray/black coloring instead of bright pink.

## Advanced: Extract Textures from DAE Files

If you want the original textures:

1. **The DAE files are here:** `Assets/URDF/niryo_one/niryo_one_urdf/meshes/collada/`
2. **Unity 6 may not extract embedded textures automatically**
3. **Manual extraction:**
   - Open DAE files in a 3D tool (Blender)
   - Export textures separately
   - Import to Unity
   - Assign to materials

For most robotics simulations, **simple colored materials are sufficient** and perform better.

## Troubleshooting

**Materials still pink after conversion:**
- Check Console for errors
- Ensure URP is actually active: Edit → Project Settings → Graphics → Scriptable Render Pipeline Settings should point to a URP Asset

**Can't find "Convert to URP" option:**
- Your project uses URP (check manifest.json has `com.unity.render-pipelines.universal`)
- The conversion option is under Edit → Rendering → Materials

**Robot has no mesh at all:**
- URDF import may have failed
- Check Console for import errors
- Try reimporting with VHACD decomposer
