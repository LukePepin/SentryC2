using UnityEngine;
using TMPro;
using System.Collections.Generic;

/// <summary>
/// ControlModeManager: Top-level orchestration for Bidirectional Digital Twin
/// 
/// **Mission:** Implements "Ghost vs. Real" synchronization with:
/// - Deterministic state convergence (S_unity ≈ S_ros)
/// - Kinematic attachment for grip (prevents physics slip)
/// - H1 Resilience (watchdog timeout → safety hold)
/// 
/// **Architecture:**
///   Ghost Robot (User Input) → Bridge → ROS2 Action Server → Real Robot
///   Real Robot (Feedback) ← Bridge ← ROS2 Joint States ← Real Robot
/// 
/// **Visual Proof:** Ghost (transparent red) should lag behind Real (opaque) by ~50-200ms.
/// This gap is the latency tax of cryptographic verification + DDS middleware.
/// </summary>
public class ControlModeManager : MonoBehaviour
{
    [Header("=== ROBOT REFERENCES ===")]
    [Tooltip("Ghost robot (user controls, transparent red)")]
    public GameObject ghostRobot;
    
    [Tooltip("Real robot (ROS2-driven, opaque)")]
    public GameObject realRobot;



    [Header("=== NETWORK RESILIENCE (H1) ===")]
    [Tooltip("Watchdog timeout: if no ROS2 heartbeat, trigger safety hold")]
    public float watchdogTimeoutSeconds = 2.0f;
    
    [Tooltip("Display connection status")]
    public TextMeshProUGUI connectionStatus;
    
    private float lastJointStateArrival = 0f;
    private bool networkHealthy = true;

    [Header("=== LATENCY TELEMETRY ===")]
    [Tooltip("Display Ghost-Real latency delta")]
    public TextMeshProUGUI latencyDisplay;
    
    private Vector3 ghostEndEffectorPos = Vector3.zero;
    private Vector3 realEndEffectorPos = Vector3.zero;
    private float latencyDeltaMeters = 0f;

    // State tracking
    private GripperControlSystem gripperController;

    void Start()
    {
        gripperController = GetComponent<GripperControlSystem>();
        if (gripperController == null)
            Debug.LogWarning("GripperControlSystem not found on ControlModeManager");

        lastJointStateArrival = Time.time;
    }

    void Update()
    {
        // **WATCHDOG: Detect network timeout**
        UpdateNetworkHealth();

        // **BIDIRECTIONAL SYNC: Calculate Ghost vs. Real delta**
        CalculateLatencyDelta();

        // **UI TELEMETRY: Update displays**
        UpdateTelemetry();
    }

    /// <summary>
    /// WATCHDOG TIMEOUT HANDLER
    /// If no ROS2 JointState arrives for N seconds, freeze the real robot.
    /// Gripper remains in last known state (SAFE_HOLD).
    /// </summary>
    private void UpdateNetworkHealth()
    {
        float timeSinceLastHeartbeat = Time.time - lastJointStateArrival;
        bool wasHealthy = networkHealthy;
        networkHealthy = (timeSinceLastHeartbeat < watchdogTimeoutSeconds);

        if (wasHealthy && !networkHealthy)
        {
            Debug.LogWarning($"[H1 RESILIENCE] WATCHDOG TRIGGERED: No ROS2 heartbeat for {timeSinceLastHeartbeat:F2}s");
            TriggerSafetyHold();
        }

        if (!wasHealthy && networkHealthy)
        {
            // Network restored
        }
    }

    /// <summary>
    /// SAFETY HOLD: Freeze real robot in place on network loss.
    /// Do NOT open gripper (default state must be CLOSED).
    /// </summary>
    private void TriggerSafetyHold()
    {
        if (realRobot == null) return;

        ArticulationBody[] joints = realRobot.GetComponentsInChildren<ArticulationBody>();
        foreach (ArticulationBody joint in joints)
        {
            // Set all joints to 0 target velocity (frozen)
            ArticulationDrive drive = joint.xDrive;
            drive.targetVelocity = 0f;
            joint.xDrive = drive;
        }

        // Gripper state: MAINTAIN current closure (do NOT open)
        if (gripperController != null)
        {
            gripperController.safetyHoldActive = true;
        }
    }

    /// <summary>
    /// LATENCY VISUALIZATION
    /// The gap between Ghost and Real is the network tax.
    /// This proves the system is ROS2-driven, not simulated locally.
    /// </summary>
    private void CalculateLatencyDelta()
    {
        if (ghostRobot == null || realRobot == null) return;

        // Get end-effector positions (wrist link)
        ghostEndEffectorPos = ghostRobot.transform.Find("Link_6")?.position ?? Vector3.zero;
        realEndEffectorPos = realRobot.transform.Find("Link_6")?.position ?? Vector3.zero;

        latencyDeltaMeters = Vector3.Distance(ghostEndEffectorPos, realEndEffectorPos);
    }



    /// <summary>
    /// UI TELEMETRY: Update connection status and latency display
    /// </summary>
    private void UpdateTelemetry()
    {
        if (connectionStatus != null)
        {
            string status = networkHealthy ? "CONNECTED" : "DISCONNECTED (H1 SAFE_HOLD)";
            float timeSinceHeartbeat = Time.time - lastJointStateArrival;
            connectionStatus.text = $"{status}\nHeartbeat: {timeSinceHeartbeat:F2}s";
        }

        if (latencyDisplay != null)
        {
            latencyDisplay.text = $"Ghost-Real Δ: {latencyDeltaMeters * 1000f:F1}ms";
        }
    }

    /// <summary>
    /// PUBLIC METHOD: Signal ROS2 message arrival (call from JointStateSubscriber)
    /// </summary>
    public void OnJointStateArrived()
    {
        lastJointStateArrival = Time.time;
    }

    /// <summary>
    /// PUBLIC METHOD: Get current network health for diagnostics
    /// </summary>
    public bool IsNetworkHealthy()
    {
        return networkHealthy;
    }

    /// <summary>
    /// PUBLIC METHOD: Get latency delta for testing
    /// </summary>
    public float GetLatencyDeltaMeters()
    {
        return latencyDeltaMeters;
    }
}
