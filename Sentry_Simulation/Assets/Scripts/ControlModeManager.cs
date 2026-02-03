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
    
    [Tooltip("Gripper attachment point on real robot")]
    public Transform gripperAttachmentPoint;

    [Header("=== PAYLOAD & DYNAMICS ===")]
    [Tooltip("Object to be picked and placed")]
    public GameObject workObject;
    
    [Tooltip("Attachment threshold: distance between gripper and object")]
    public float attachmentThreshold = 0.05f;
    
    [Tooltip("Detachment threshold: gripper must open beyond this")]
    public float detachmentThreshold = 0.2f;

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
    private bool isPayloadAttached = false;
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

        // **KINEMATIC ATTACHMENT: Conditional parenting**
        UpdatePayloadAttachment();

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
            Debug.Log("[H1 RESILIENCE] Network recovered. Resuming normal operation.");
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

        Debug.Log("[SAFETY] Real robot frozen. Gripper in SAFE_HOLD.");
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
    /// KINEMATIC ATTACHMENT: Prevent Physics Slip
    /// 
    /// Theory: Physics-based grasping (friction) is unreliable in simulation.
    /// Solution: Use Kinematic Attachment (Parenting) to lock object to gripper.
    /// 
    /// Logic:
    ///   1. If gripper closed AND distance(gripper, object) < threshold:
    ///      → SetParent(workObject, gripperAttachmentPoint)
    ///      → workObject.GetComponent<Rigidbody>().isKinematic = true
    ///   2. If gripper opened AND distance > detachment_threshold:
    ///      → SetParent(workObject, null)
    ///      → workObject.GetComponent<Rigidbody>().isKinematic = false
    /// </summary>
    private void UpdatePayloadAttachment()
    {
        if (workObject == null || gripperAttachmentPoint == null) return;

        float distanceToGripper = Vector3.Distance(
            workObject.transform.position,
            gripperAttachmentPoint.position
        );

        Rigidbody rb = workObject.GetComponent<Rigidbody>();
        if (rb == null) return;

        // **ATTACH: Gripper closed and object near**
        if (!isPayloadAttached &&
            gripperController.gripperState == GripperControlSystem.GripperState.Closed &&
            distanceToGripper < attachmentThreshold)
        {
            workObject.transform.SetParent(gripperAttachmentPoint);
            rb.isKinematic = true;
            isPayloadAttached = true;

            Debug.Log("[KINEMATIC] Payload attached to gripper (physics frozen)");
        }

        // **DETACH: Gripper opened and object far**
        if (isPayloadAttached &&
            gripperController.gripperState == GripperControlSystem.GripperState.Open &&
            distanceToGripper > detachmentThreshold)
        {
            workObject.transform.SetParent(null);
            rb.isKinematic = false;
            rb.linearVelocity = Vector3.zero; // Reset velocity on release
            isPayloadAttached = false;

            Debug.Log("[KINEMATIC] Payload detached from gripper (physics active)");
        }
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
            latencyDisplay.text = $"Ghost-Real Δ: {latencyDeltaMeters * 1000f:F1}ms\n" +
                                   $"Payload: {(isPayloadAttached ? "ATTACHED" : "FREE")}";
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
