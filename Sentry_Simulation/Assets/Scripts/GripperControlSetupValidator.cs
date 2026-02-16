using UnityEngine;
using TMPro;

/// <summary>
/// VALIDATOR: Checks for missing/invalid references in Gripper Control setup.
/// Run this in the Inspector or via PlayMode to detect configuration errors.
/// </summary>
[ExecuteInEditMode]
public class GripperControlSetupValidator : MonoBehaviour
{
    public enum ValidationResult { Valid, Warning, Error }

    [Header("=== AUTO-VALIDATOR ===")]
    [Tooltip("Automatically validate on play")]
    public bool validateOnPlay = true;

    [Tooltip("Log level: 0=Error, 1=Warning, 2=Info")]
    public int logLevel = 2;

    private GripperControlSystem gripperControl;
    private ControlModeManager controlManager;

    void OnEnable()
    {
        // Validator disabled - gripper logic removed
        // if (!Application.isPlaying && !validateOnPlay)
        //     return;
        //
        // ValidateSetup();
    }

    /// <summary>
    /// Main validation routine
    /// </summary>
    public void ValidateSetup()
    {
        Log("====== GRIPPER CONTROL SETUP VALIDATION ======", 2);

        gripperControl = GetComponent<GripperControlSystem>();
        controlManager = GetComponent<ControlModeManager>();

        ValidationResult result = ValidationResult.Valid;

        // Check for critical components
        if (gripperControl == null)
        {
            LogError("GripperControlSystem component NOT FOUND on this GameObject");
            result = ValidationResult.Error;
        }

        if (controlManager == null)
        {
            LogError("ControlModeManager component NOT FOUND on this GameObject");
            result = ValidationResult.Error;
        }

        // If we have both components, validate their references
        if (gripperControl != null && controlManager != null)
        {
            result = ValidateGripperControlReferences();
            if (result == ValidationResult.Valid)
                result = ValidateControlManagerReferences();
        }

        // Summary
        Log("", 2);
        switch (result)
        {
            case ValidationResult.Valid:
                Log("✅ ALL CHECKS PASSED - Ready for testing!", 2);
                break;
            case ValidationResult.Warning:
                Log("⚠️  WARNINGS DETECTED - Check log above", 1);
                break;
            case ValidationResult.Error:
                Log("❌ CRITICAL ERRORS - Fix before testing", 0);
                break;
        }
        Log("", 2);
    }

    ValidationResult ValidateGripperControlReferences()
    {
        Log("\n--- GripperControlSystem References ---", 2);
        ValidationResult result = ValidationResult.Valid;

        if (gripperControl.ghostRobot == null)
        {
            LogError("  ghostRobot is NULL - Assign RobotGhost GameObject");
            result = ValidationResult.Error;
        }
        else
        {
            Log($"  ✓ ghostRobot: {gripperControl.ghostRobot.name}", 2);
        }

        if (gripperControl.realRobot == null)
        {
            LogError("  realRobot is NULL - Assign RobotReal GameObject");
            result = ValidationResult.Error;
        }
        else
        {
            Log($"  ✓ realRobot: {gripperControl.realRobot.name}", 2);
        }

        // Validate ArticulationBody chains
        if (gripperControl.ghostRobot != null)
        {
            ArticulationBody[] ghostJoints = gripperControl.ghostRobot.GetComponentsInChildren<ArticulationBody>();
            if (ghostJoints.Length < 6)
            {
                LogWarning($"  ghostRobot has only {ghostJoints.Length} joints (expected 6)");
            }
            else
            {
                Log($"  ✓ ghostRobot: {ghostJoints.Length} ArticulationBody joints", 2);
            }
        }

        if (gripperControl.realRobot != null)
        {
            ArticulationBody[] realJoints = gripperControl.realRobot.GetComponentsInChildren<ArticulationBody>();
            if (realJoints.Length < 6)
            {
                LogWarning($"  realRobot has only {realJoints.Length} joints (expected 6)");
            }
            else
            {
                Log($"  ✓ realRobot: {realJoints.Length} ArticulationBody joints", 2);
            }
        }

        return result;
    }

    ValidationResult ValidateControlManagerReferences()
    {
        Log("\n--- ControlModeManager References ---", 2);
        ValidationResult result = ValidationResult.Valid;

        if (controlManager.ghostRobot == null)
        {
            LogError("  ghostRobot is NULL");
            result = ValidationResult.Error;
        }
        else
        {
            Log($"  ✓ ghostRobot: {controlManager.ghostRobot.name}", 2);
        }

        if (controlManager.realRobot == null)
        {
            LogError("  realRobot is NULL");
            result = ValidationResult.Error;
        }
        else
        {
            Log($"  ✓ realRobot: {controlManager.realRobot.name}", 2);
        }

        return result;
    }

    void Log(string msg, int level)
    {
        if (level <= logLevel)
            Debug.Log($"[VALIDATOR] {msg}");
    }

    void LogWarning(string msg)
    {
        Debug.LogWarning($"[VALIDATOR] ⚠️  {msg}");
    }

    void LogError(string msg)
    {
        Debug.LogError($"[VALIDATOR] ❌ {msg}");
    }
}
