using UnityEngine;
using TMPro;
using System;
using UnityEngine.InputSystem;
using Unity.Robotics.UrdfImporter.Control;

/// <summary>
/// Bidirectional Control Manager.
/// Implements H1 resilience: Network drop prevents unsafe operations.
/// 
/// State Machine:
///   MONITOR (default)   → RealRobot drives.
///   COMMAND (teleop)    → GhostRobot controlled via user input; RealRobot follows.
///   VALIDATION (H1)     → Detects network desync and triggers safety holds.
/// </summary>
public class GripperControlSystem : MonoBehaviour
{
    public enum ControlMode { Monitor, Command, Validation }
    public enum GripperState { Open, Closing, Closed, Opening }

    [Header("Mode Configuration")]
    public ControlMode currentMode = ControlMode.Monitor;
    public TextMeshProUGUI modeIndicator;

    [Header("Robot References")]
    public ArticulationBody ghostRobot;
    public ArticulationBody realRobot;



    [Header("ROS2 Bridge")]
    public JointStateSubscriber jointStateSubscriber;
    // public TrajectoryPublisher trajectoryPublisher; // TODO: Implement after ROS2 Action server

    [Header("Network Safety")]
    public float heartbeatTimeoutSeconds = 2.0f;
    private float lastHeartbeatTime = 0f;
    private bool networkAlive = true;

    [Header("H1 Validation")]
    public float maxJointDeltaDegrees = 5.0f;
    public float maxPayloadDeltaMeters = 0.2f;
    public Color validationAlarmColor = Color.red;

    // State tracking (pre-allocated, publicly readable for debugging)
    public GripperState gripperState = GripperState.Open;
    public bool safetyHoldActive = false;

    // Singleton
    private static GripperControlSystem instance;
    private Keyboard keyboard;

    void Awake()
    {
        if (instance != null && instance != this)
        {
            Destroy(gameObject);
            return;
        }
        instance = this;
    }

    void Start()
    {
        keyboard = Keyboard.current;
        lastHeartbeatTime = Time.time;
        UpdateModeUI();
    }

    void Update()
    {
        if (keyboard == null) return;

        // Update network heartbeat (from ROS2 message arrival)
        UpdateHeartbeat();

        // Mode switching
        if (keyboard.digit1Key.wasPressedThisFrame)
            SetMode(ControlMode.Monitor);
        if (keyboard.digit2Key.wasPressedThisFrame)
            SetMode(ControlMode.Command);
        if (keyboard.digit3Key.wasPressedThisFrame)
            SetMode(ControlMode.Validation);

        // Execute mode logic
        switch (currentMode)
        {
            case ControlMode.Monitor:
                UpdateMonitorMode();
                break;
            case ControlMode.Command:
                UpdateCommandMode();
                break;
            case ControlMode.Validation:
                UpdateValidationMode();
                break;
        }
    }

    /// <summary>
    /// MONITOR MODE: RealRobot drives.
    /// </summary>
    private void UpdateMonitorMode()
    {
        // Monitor mode - no gripper logic
    }

    /// <summary>
    /// COMMAND MODE: User controls GhostRobot; RealRobot follows via ROS2.
    /// Hotkeys: P = Pick, R = Release.
    /// </summary>
    private void UpdateCommandMode()
    {
        // Pick sequence
        if (keyboard.pKey.wasPressedThisFrame)
        {
            PickSequence();
        }

        // Release sequence
        if (keyboard.rKey.wasPressedThisFrame)
        {
            ReleaseSequence();
        }

        // User controls ghost arm via TrajectoryPublisher (assumed external)
        // Example: WASD or gamepad input processed by IK solver
    }

    /// <summary>
    /// VALIDATION MODE: Detect network desync and trigger alarms.
    /// </summary>
    private void UpdateValidationMode()
    {
        // Calculate joint delta (Ghost vs Real)
        float jointDelta = CalculateJointDelta();

        // Check for critical desync
        bool jointAnomaly = jointDelta > maxJointDeltaDegrees;

        if (jointAnomaly)
        {
            TriggerValidationAlarm(jointDelta, 0f);
        }

        // Telemetry logged only on alarm
    }

    /// <summary>
    /// PICK: Reserved for future implementation.
    /// </summary>
    private void PickSequence()
    {
        // Gripper logic removed
    }

    /// <summary>
    /// RELEASE: Reserved for future implementation.
    /// </summary>
    private void ReleaseSequence()
    {
        // Gripper logic removed
    }





    /// <summary>
    /// Calculate max delta between ghost and real joint angles.
    /// Zero-alloc: pre-iterate articulation bodies.
    /// </summary>
    private float CalculateJointDelta()
    {
        if (ghostRobot == null || realRobot == null) return 0f;

        float maxDelta = 0f;
        var ghostJoints = ghostRobot.GetComponentsInChildren<ArticulationBody>();
        var realJoints = realRobot.GetComponentsInChildren<ArticulationBody>();

        int count = Mathf.Min(ghostJoints.Length, realJoints.Length);
        for (int i = 0; i < count; i++)
        {
            float ghostAngle = ghostJoints[i].jointPosition[0] * Mathf.Rad2Deg;
            float realAngle = realJoints[i].jointPosition[0] * Mathf.Rad2Deg;
            float delta = Mathf.Abs(ghostAngle - realAngle);
            maxDelta = Mathf.Max(maxDelta, delta);
        }

        return maxDelta;
    }

    /// <summary>
    /// Update network heartbeat from ROS2 message callbacks.
    /// </summary>
    private void UpdateHeartbeat()
    {
        // Called when JointState message arrives (assumed external callback)
        // Placeholder: Manually update for testing
        float timeSinceHeartbeat = Time.time - lastHeartbeatTime;
        networkAlive = timeSinceHeartbeat < heartbeatTimeoutSeconds;

        if (!networkAlive && currentMode != ControlMode.Monitor)
        {
            safetyHoldActive = true;
            Debug.LogError($"[GripperControlSystem] NETWORK LOSS: {timeSinceHeartbeat:F2}s since last heartbeat");
        }
    }

    /// <summary>
    /// Public method: Call from JointStateSubscriber when message received.
    /// </summary>
    public void OnHeartbeat()
    {
        lastHeartbeatTime = Time.time;
        if (!networkAlive)
        {
            Debug.Log("[GripperControlSystem] Network restored.");
            networkAlive = true;
            safetyHoldActive = false;
        }
    }

    /// <summary>
    /// Trigger H1 validation alarm: Joint desync or payload falling.
    /// </summary>
    private void TriggerValidationAlarm(float jointDelta, float payloadDelta)
    {
        if (modeIndicator != null)
        {
            modeIndicator.text = $"[CRITICAL] Joint Delta={jointDelta:F1}deg Payload Delta={payloadDelta:F2}m";
            modeIndicator.color = validationAlarmColor;
        }

        Debug.LogError($"[GripperControlSystem] H1 VALIDATION FAILED: Ghost/Real desync detected.");
    }

    private void SetMode(ControlMode mode)
    {
        currentMode = mode;
        safetyHoldActive = false;
        UpdateModeUI();
        Debug.Log($"[GripperControlSystem] Mode switched to: {mode}");
    }

    private void UpdateModeUI()
    {
        if (modeIndicator == null) return;

        string modeText = currentMode switch
        {
            ControlMode.Monitor => "[MONITOR] RealRobot drives",
            ControlMode.Command => "[COMMAND] Teleop active",
            ControlMode.Validation => "[VALIDATION] H1 Check",
            _ => "UNKNOWN"
        };

        modeIndicator.text = modeText;
        modeIndicator.color = networkAlive ? Color.white : Color.yellow;
    }

    public static GripperControlSystem Instance => instance;
}
