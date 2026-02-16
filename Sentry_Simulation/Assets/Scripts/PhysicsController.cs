using UnityEngine;

namespace Unity.Robotics.UrdfImporter.Control
{
    /// <summary>
    /// Simplified physics controller for URDF robots without keyboard input.
    /// Sets ArticulationBody physics parameters (stiffness, damping, force limits) 
    /// for ROS2-controlled robots.
    /// </summary>
    public class PhysicsController : MonoBehaviour
    {
        private ArticulationBody[] articulationChain;

        [Header("Joint Drive Parameters")]
        [Tooltip("Stiffness of the joint drive (higher = stiffer)")]
        public float stiffness = 10000f;
        
        [Tooltip("Damping of the joint drive (higher = more damping)")]
        public float damping = 1000f;
        
        [Tooltip("Maximum force the joint can apply")]
        public float forceLimit = 1000f;
        
        [Tooltip("Joint friction coefficient")]
        public float jointFriction = 10f;
        
        [Tooltip("Angular damping for joint movement")]
        public float angularDamping = 10f;

        void Start()
        {
            // Add the FKRobot helper component
            if (GetComponent<FKRobot>() == null)
            {
                gameObject.AddComponent<FKRobot>();
            }

            // Get all articulation bodies in the robot
            articulationChain = GetComponentsInChildren<ArticulationBody>();

            // Configure each joint
            foreach (ArticulationBody joint in articulationChain)
            {
                // Set physics parameters
                joint.jointFriction = jointFriction;
                joint.angularDamping = angularDamping;

                // Configure the drive (for revolute/prismatic joints)
                ArticulationDrive drive = joint.xDrive;
                drive.stiffness = stiffness;
                drive.damping = damping;
                drive.forceLimit = forceLimit;
                joint.xDrive = drive;
            }
        }

        /// <summary>
        /// Update physics parameters at runtime if changed in inspector
        /// </summary>
        void OnValidate()
        {
            if (Application.isPlaying && articulationChain != null)
            {
                foreach (ArticulationBody joint in articulationChain)
                {
                    joint.jointFriction = jointFriction;
                    joint.angularDamping = angularDamping;

                    ArticulationDrive drive = joint.xDrive;
                    drive.stiffness = stiffness;
                    drive.damping = damping;
                    drive.forceLimit = forceLimit;
                    joint.xDrive = drive;
                }
            }
        }
    }
}
