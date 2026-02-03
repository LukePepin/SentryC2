using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;

namespace Unity.Robotics.UrdfImporter.Control
{
    /// <summary>
    /// Subscribes to ROS2 /joint_states topic and applies positions to ArticulationBody joints.
    /// This is the Unity-side receiver for the ROS2 cyclic_action_server.
    /// </summary>
    public class JointStateSubscriber : MonoBehaviour
    {
        [Header("ROS Configuration")]
        [Tooltip("ROS2 topic to subscribe to")]
        public string topicName = "/joint_states";

        private ArticulationBody[] articulationChain;
        private ROSConnection ros;

        void Start()
        {
            // Get ROS connection
            ros = ROSConnection.GetOrCreateInstance();
            
            // Register subscriber
            ros.Subscribe<JointStateMsg>(topicName, OnJointStateReceived);
            
            Debug.Log($"JointStateSubscriber: Subscribed to {topicName}");

            // Get all articulation bodies
            articulationChain = GetComponentsInChildren<ArticulationBody>();
            
            Debug.Log($"JointStateSubscriber: Found {articulationChain.Length} ArticulationBody components");
        }

        /// <summary>
        /// Callback when JointState message is received from ROS2
        /// </summary>
        void OnJointStateReceived(JointStateMsg msg)
        {
            Debug.Log($"[JointStateSubscriber] CALLBACK FIRED: {msg.position.Length} positions received");
            
            if (msg.position == null || msg.position.Length == 0)
            {
                Debug.LogWarning("JointStateSubscriber: Received empty joint positions");
                return;
            }

            // **H1 RESILIENCE: Signal heartbeat to ControlModeManager watchdog**
            ControlModeManager controlManager = GetComponent<ControlModeManager>();
            if (controlManager != null)
            {
                controlManager.OnJointStateArrived();
            }

            // Apply positions to matching joints
            for (int i = 0; i < msg.name.Length && i < msg.position.Length; i++)
            {
                string jointName = msg.name[i];
                double position = msg.position[i];

                // Map ROS joint name to Unity link name (child link of the joint)
                string linkName = MapJointNameToLinkName(jointName);
                
                Debug.Log($"[JointStateSubscriber] Joint {i}: ROS name={jointName}, mapped to link={linkName}, position={position}");
                
                if (linkName != null)
                {
                    // Find matching ArticulationBody
                    ArticulationBody matchingJoint = FindJointByName(linkName);
                    
                    if (matchingJoint != null)
                    {
                        // Convert radians to degrees for Unity
                        float targetDegrees = (float)(position * Mathf.Rad2Deg);
                        
                        // Set target position
                        ArticulationDrive drive = matchingJoint.xDrive;
                        drive.target = targetDegrees;
                        matchingJoint.xDrive = drive;
                        
                        Debug.Log($"  → Set {matchingJoint.name} target to {targetDegrees}°");
                    }
                    else
                    {
                        Debug.LogError($"  → ERROR: Could not find joint for link {linkName}");
                    }
                }
                else
                {
                    Debug.LogWarning($"  → No mapping for joint name {jointName}");
                }
            }
        }

        /// <summary>
        /// Map ROS2 joint names to Unity link names (based on URDF child links)
        /// </summary>
        string MapJointNameToLinkName(string jointName)
        {
            switch (jointName)
            {
                case "joint_1": return "shoulder_link";
                case "joint_2": return "arm_link";
                case "joint_3": return "elbow_link";
                case "joint_4": return "forearm_link";
                case "joint_5": return "wrist_link";
                case "joint_6": return "hand_link";
                default: return null;
            }
        }

        /// <summary>
        /// Find ArticulationBody by link name
        /// </summary>
        ArticulationBody FindJointByName(string name)
        {
            foreach (var joint in articulationChain)
            {
                if (joint.name == name)
                {
                    return joint;
                }
            }
            Debug.LogWarning($"[JointStateSubscriber] Could NOT find joint: {name}. Available: {string.Join(", ", System.Linq.Enumerable.Select(articulationChain, j => j.name))}");
            return null;
        }

        /// <summary>
        /// Get gripper joint position for GripperControlSystem.
        /// Returns 0.0 if gripper is closed, > 0.05 if open.
        /// </summary>
        public float GetGripperPosition()
        {
            // Find gripper joint (usually last in chain)
            if (articulationChain == null || articulationChain.Length == 0)
                return 1.0f; // Assume open if no chain

            // Get last articulation (typically gripper)
            ArticulationBody gripperJoint = articulationChain[articulationChain.Length - 1];
            
            // Return current position (radians)
            return gripperJoint.jointPosition[0];
        }

        void OnDestroy()
        {
            if (ros != null)
            {
                ros.Unsubscribe(topicName);
            }
        }
    }
}
