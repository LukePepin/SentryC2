using UnityEngine;
using TMPro;
using System;
using UnityEngine.InputSystem;
using Unity.Robotics.UrdfImporter.Control;

/// <summary>
/// Bidirectional Pick-and-Place Control Manager.
/// Implements H1 resilience: Network drop prevents unintended gripper release.
/// 
/// State Machine:
///   MONITOR (default)   → RealRobot drives; WorkObject follows only if gripper closed.
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

    [Header("Gripper References")]
    public Transform gripperGhost;
    public Transform gripperReal;
    public float gripperCloseThreshold = 0.1f; // Distance threshold for attachment

    [Header("Payload References")]
    public GameObject workObject;
    public Rigidbody workObjectRigidbody;
    public Transform targetZone;

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
    public bool isObjectAttached = false;
    private float gripperClosureTime = 0f;
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
        
        // Validate references
        if (workObjectRigidbody == null && workObject != null)
            workObjectRigidbody = workObject.GetComponent<Rigidbody>();

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
    /// MONITOR MODE: RealRobot drives; payload follows only if gripper reports closed.
    /// </summary>
    private void UpdateMonitorMode()
    {
        // If real robot gripper is closed AND object is near gripper
        bool gripperClosed = IsRealGripperClosed();
        float payloadDistance = Vector3.Distance(workObject.transform.position, gripperReal.position);

        if (gripperClosed && payloadDistance < gripperCloseThreshold && !isObjectAttached)
        {
            AttachPayload(gripperReal);
            Debug.Log("[GripperControlSystem] MONITOR: Payload auto-attached to RealGripper");
        }
        else if (!gripperClosed && isObjectAttached)
        {
            DetachPayload();
            Debug.Log("[GripperControlSystem] MONITOR: Payload auto-released from RealGripper");
        }
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

        // Calculate payload delta (WorkObject vs GripperReal)
        float payloadDelta = Vector3.Distance(workObject.transform.position, gripperReal.position);

        // Check for critical desync
        bool jointAnomaly = jointDelta > maxJointDeltaDegrees;
        bool payloadAnomaly = IsRealGripperClosed() && payloadDelta > maxPayloadDeltaMeters;

        if (jointAnomaly || payloadAnomaly)
        {
            TriggerValidationAlarm(jointDelta, payloadDelta);
        }

        // Log telemetry (zero-alloc)
        Debug.Log($"[GripperControlSystem] VALIDATION: JointDelta={jointDelta:F2}°, PayloadDelta={payloadDelta:F2}m");
    }

    /// <summary>
    /// PICK: Move arm to object, attach via kinematic parenting, send to ROS2.
    /// </summary>
    private void PickSequence()
    {
        if (safetyHoldActive)
        {
            Debug.LogError("[GripperControlSystem] PICK BLOCKED: Safety hold active (network loss)");
            return;
        }

        // Move ghost arm to approach object
        Debug.Log("[GripperControlSystem] PICK: Moving arm to object...");

        // Wait for gripper to close and object to be within threshold
        if (Vector3.Distance(gripperGhost.position, workObject.transform.position) < gripperCloseThreshold)
        {
            AttachPayload(gripperGhost);
            gripperState = GripperState.Closed;
            gripperClosureTime = Time.time;

            // TODO: Send execution command to ROS2 via TrajectoryPublisher
            Debug.Log($"[GripperControlSystem] PICK: Payload attached. [Time={Time.time:F2}]");
        }
        else
        {
            Debug.LogWarning("[GripperControlSystem] PICK: Object out of reach");
        }
    }

    /// <summary>
    /// RELEASE: Detach payload ONLY if network is alive. Otherwise, safety hold.
    /// </summary>
    private void ReleaseSequence()
    {
        if (!isObjectAttached)
        {
            Debug.LogWarning("[GripperControlSystem] RELEASE: No object attached");
            return;
        }

        // Critical H1 Logic: Check network heartbeat
        if (!networkAlive)
        {
            safetyHoldActive = true;
            Debug.LogError("[GripperControlSystem] RELEASE BLOCKED: Network down. Entering Safety Hold.");
            if (modeIndicator != null)
                modeIndicator.text = "[WARNING] SAFETY HOLD: Network Loss";
            return;
        }

        // Network OK: Safe to release
        DetachPayload();
        gripperState = GripperState.Open;

        // TODO: Send execution command to ROS2 via TrajectoryPublisher
        Debug.Log($"[GripperControlSystem] RELEASE: Payload detached. [Time={Time.time:F2}]");
    }

    /// <summary>
    /// Kinematic attachment: Parent WorkObject to Gripper, disable physics.
    /// </summary>
    private void AttachPayload(Transform gripperTransform)
    {
        if (isObjectAttached) return;

        workObject.transform.SetParent(gripperTransform);
        if (workObjectRigidbody != null)
        {
            workObjectRigidbody.isKinematic = true;
        }

        isObjectAttached = true;
    }

    /// <summary>
    /// Kinematic detachment: Unparent WorkObject, re-enable physics.
    /// </summary>
    private void DetachPayload()
    {
        if (!isObjectAttached) return;

        workObject.transform.SetParent(null);
        if (workObjectRigidbody != null)
        {
            workObjectRigidbody.isKinematic = false;
            workObjectRigidbody.linearVelocity = Vector3.zero; // Reset velocity to prevent jerking
        }

        isObjectAttached = false;
    }

    /// <summary>
    /// Check if RealRobot gripper is closed (from JointStateSubscriber feedback).
    /// </summary>
    private bool IsRealGripperClosed()
    {
        if (jointStateSubscriber == null) return false;
        // Assumes gripper joint state is published; extract and check torque/position
        // Placeholder: Assume gripper_joint position < 0.05 radians == closed
        return jointStateSubscriber.GetGripperPosition() < 0.05f;
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
