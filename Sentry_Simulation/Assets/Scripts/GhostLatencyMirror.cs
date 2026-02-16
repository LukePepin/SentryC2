using UnityEngine;

/// <summary>
/// GhostLatencyMirror: Ghost robot copies RobotReal's joint positions with a delay.
/// Visualizes network latency—Ghost lags behind Real by ~50-200ms (ROS middleware tax).
/// </summary>
public class GhostLatencyMirror : MonoBehaviour
{
    [Header("Robot References")]
    public GameObject robotReal;
    public GameObject robotGhost;

    [Header("Latency Simulation")]
    [Tooltip("Delay in seconds to lag behind Real robot")]
    public float latencySeconds = 0.1f;

    private ArticulationBody[] realJoints;
    private ArticulationBody[] ghostJoints;
    private float[] positionHistory;
    private float[] timeHistory;
    private int historyIndex = 0;
    private const int HISTORY_SIZE = 60; // ~2 seconds at 30fps

    void Start()
    {
        if (robotReal == null || robotGhost == null)
        {
            Debug.LogError("[GhostLatencyMirror] RobotReal or RobotGhost not assigned");
            enabled = false;
            return;
        }

        realJoints = robotReal.GetComponentsInChildren<ArticulationBody>();
        ghostJoints = robotGhost.GetComponentsInChildren<ArticulationBody>();

        if (realJoints.Length != ghostJoints.Length)
        {
            Debug.LogWarning($"[GhostLatencyMirror] Joint count mismatch: Real={realJoints.Length}, Ghost={ghostJoints.Length}");
        }

        // Initialize history buffer
        positionHistory = new float[HISTORY_SIZE * realJoints.Length];
        timeHistory = new float[HISTORY_SIZE];
    }

    void FixedUpdate()
    {
        if (realJoints == null || ghostJoints == null || realJoints.Length == 0)
            return;

        // Record current Real robot positions
        for (int i = 0; i < realJoints.Length; i++)
        {
            positionHistory[historyIndex * realJoints.Length + i] = realJoints[i].xDrive.target;
        }
        timeHistory[historyIndex] = Time.time;

        // Find delayed position (lookup oldest entry older than latencySeconds)
        int delayedIndex = -1;
        for (int i = 0; i < HISTORY_SIZE; i++)
        {
            int idx = (historyIndex - i + HISTORY_SIZE) % HISTORY_SIZE;
            float timeDelta = Time.time - timeHistory[idx];
            if (timeDelta >= latencySeconds)
            {
                delayedIndex = idx;
                break;
            }
        }

        // If found delayed state, apply to Ghost
        if (delayedIndex >= 0)
        {
            for (int i = 0; i < Mathf.Min(realJoints.Length, ghostJoints.Length); i++)
            {
                float delayedPosition = positionHistory[delayedIndex * realJoints.Length + i];
                
                ArticulationDrive drive = ghostJoints[i].xDrive;
                drive.target = delayedPosition;
                ghostJoints[i].xDrive = drive;
            }
        }

        // Advance history buffer
        historyIndex = (historyIndex + 1) % HISTORY_SIZE;
    }
}
