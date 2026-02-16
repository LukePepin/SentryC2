using UnityEngine;
using UnityEngine.InputSystem;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Trajectory;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Std;
using TMPro;

/// <summary>
/// GhostInputController: joint-level keyboard controller for Ghost robot.
/// Left/Right = select joint, Up/Down = move selected joint.
/// Optional: publish JointTrajectory to ROS2 (pre-allocated, zero-alloc Update).
/// </summary>
public class GhostInputController : MonoBehaviour
{
    [Header("Joint Selection")]
    public ArticulationBody[] joints;
    public float jointSpeedDegPerSec = 30f;
    public TextMeshProUGUI jointNameDisplay;

    [Header("Gripper (Optional)")]
    // public ArticulationBody leftGripper;
    // public ArticulationBody rightGripper;
    // public float gripperSpeed = 0.01f;
    // public bool includeGripperInSelection = true;
    // public float leftGripperSign = -1f;
    // public float rightGripperSign = 1f;

    [Header("ROS Publish (Optional)")]
    public bool publishToRos = true;
    public string trajectoryTopic = "/niryo_robot_follow_joint_trajectory_controller/follow_joint_trajectory";
    public string[] jointNames;
    public float publishMinInterval = 0.05f;

    private Keyboard keyboard;
    private int selectedIndex = 0;
    private int selectionCount = 0;
    private string[] linkNames = { "shoulder_link", "arm_link", "elbow_link", "forearm_link", "wrist_link", "tool_link" };

    private ROSConnection ros;
    private JointTrajectoryMsg trajectoryMsg;
    private JointTrajectoryPointMsg[] points;
    private double[] jointPositionsRad;
    private DurationMsg timeFromStart;
    private float lastPublishTime = -999f;
    private bool dirty = false;

    void Start()
    {
        keyboard = Keyboard.current;
        selectionCount = joints != null ? joints.Length : 0;

        // bool hasGripper = leftGripper != null && rightGripper != null && includeGripperInSelection;
        // if (hasGripper)
        // {
        //     selectionCount += 1;
        // }

        if (publishToRos && joints != null && joints.Length > 0)
        {
            ros = ROSConnection.GetOrCreateInstance();
            ros.RegisterPublisher<JointTrajectoryMsg>(trajectoryTopic);

            if (jointNames == null || jointNames.Length != joints.Length)
            {
                jointNames = new string[joints.Length];
                for (int i = 0; i < joints.Length; i++)
                {
                    jointNames[i] = "joint_" + (i + 1);
                }
            }

            jointPositionsRad = new double[joints.Length];
            for (int i = 0; i < joints.Length; i++)
            {
                jointPositionsRad[i] = joints[i].xDrive.target * Mathf.Deg2Rad;
            }

            timeFromStart = new DurationMsg();
            timeFromStart.sec = 0;
            timeFromStart.nanosec = 100000000;

            points = new JointTrajectoryPointMsg[1];
            points[0] = new JointTrajectoryPointMsg(jointPositionsRad, new double[0], new double[0], new double[0], timeFromStart);

            trajectoryMsg = new JointTrajectoryMsg(new HeaderMsg(), jointNames, points);
        }
    }

    void Update()
    {
        if (keyboard == null || joints == null || joints.Length == 0)
            return;

        if (keyboard.leftArrowKey.wasPressedThisFrame)
        {
            selectedIndex = (selectedIndex - 1 + selectionCount) % selectionCount;
        }
        else if (keyboard.rightArrowKey.wasPressedThisFrame)
        {
            selectedIndex = (selectedIndex + 1) % selectionCount;
        }

        float direction = (keyboard.upArrowKey.isPressed ? 1f : 0f) - (keyboard.downArrowKey.isPressed ? 1f : 0f);
        if (Mathf.Abs(direction) > 0f)
        {
            if (selectedIndex < joints.Length)
            {
                ArticulationBody joint = joints[selectedIndex];
                ArticulationDrive drive = joint.xDrive;

                float target = drive.target + direction * jointSpeedDegPerSec * Time.deltaTime;
                target = Mathf.Clamp(target, drive.lowerLimit, drive.upperLimit);

                drive.target = target;
                joint.xDrive = drive;
                
                Debug.Log($"[Ghost] Joint {selectedIndex}: target={target:F2}° (drive.stiffness={drive.stiffness}, damping={drive.damping})");

                if (jointPositionsRad != null && selectedIndex < jointPositionsRad.Length)
                {
                    jointPositionsRad[selectedIndex] = target * Mathf.Deg2Rad;
                }

                dirty = true;
            }
            else
            {
                // ApplyGripperDelta(direction * gripperSpeed * Time.deltaTime);
                // dirty = true;
            }
        }

        if (dirty && publishToRos && ros != null)
        {
            if (Time.time - lastPublishTime >= publishMinInterval)
            {
                ros.Publish(trajectoryTopic, trajectoryMsg);
                lastPublishTime = Time.time;
                dirty = false;
            }
        }

        // Update joint name display
        if (jointNameDisplay != null)
        {
            string displayName = "Unknown";
            if (selectedIndex < linkNames.Length)
            {
                displayName = linkNames[selectedIndex];
            }
            
            string limitInfo = "";
            if (selectedIndex < joints.Length)
            {
                ArticulationBody joint = joints[selectedIndex];
                ArticulationDrive drive = joint.xDrive;
                float currentAngle = drive.target;
                float lower = drive.lowerLimit;
                float upper = drive.upperLimit;
                
                limitInfo = $"\nAngle: {currentAngle:F1}° | Limits: [{lower:F1}°, {upper:F1}°]";
                
                // Warn if at limit
                if (Mathf.Abs(currentAngle - lower) < 1f || Mathf.Abs(currentAngle - upper) < 1f)
                {
                    limitInfo += " [AT LIMIT]";
                }
            }
            
            jointNameDisplay.text = $"Joint: {displayName} ({selectedIndex}){limitInfo}";
        }
    }

    void ApplyGripperDelta(float delta)
    {
        // Gripper control disabled for now
        // if (leftGripper == null || rightGripper == null) return;
        //
        // ArticulationDrive leftDrive = leftGripper.xDrive;
        // ArticulationDrive rightDrive = rightGripper.xDrive;
        //
        // float leftTarget = leftDrive.target + delta * leftGripperSign;
        // float rightTarget = rightDrive.target + delta * rightGripperSign;
        //
        // leftTarget = Mathf.Clamp(leftTarget, leftDrive.lowerLimit, leftDrive.upperLimit);
        // rightTarget = Mathf.Clamp(rightTarget, rightDrive.lowerLimit, rightDrive.upperLimit);
        //
        // leftDrive.target = leftTarget;
        // rightDrive.target = rightTarget;
        //
        // leftGripper.xDrive = leftDrive;
        // rightGripper.xDrive = rightDrive;
    }
}
