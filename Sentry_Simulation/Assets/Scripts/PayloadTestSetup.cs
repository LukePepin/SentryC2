using UnityEngine;

/// <summary>
/// WorkObject Setup for TEST 2 (Payload Attachment Test)
/// Spawns a test cube near the gripper that can be grasped and held during motion
/// </summary>
public class PayloadTestSetup : MonoBehaviour
{
    [SerializeField] private Transform gripperPosition;  // Reference to hand_link
    [SerializeField] private float spawnDistance = 0.15f;  // Distance in front of gripper
    [SerializeField] private string payloadTag = "Payload";

    private GameObject workObject;

    private void Start()
    {
        CreateWorkObject();
    }

    private void CreateWorkObject()
    {
        // Create test cube
        workObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
        workObject.name = "WorkObject";
        workObject.tag = payloadTag;

        // Position near gripper
        if (gripperPosition != null)
        {
            workObject.transform.position = gripperPosition.position + Vector3.forward * spawnDistance;
        }
        else
        {
            Debug.LogWarning("[PayloadTestSetup] Gripper position not assigned, using default offset");
            workObject.transform.position = new Vector3(0, 0.3f, 0.15f);
        }

        // Scale to reasonable size
        workObject.transform.localScale = new Vector3(0.08f, 0.08f, 0.08f);

        // Configure physics
        Rigidbody rb = workObject.GetComponent<Rigidbody>();
        rb.mass = 0.5f;
        rb.useGravity = true;
        rb.isKinematic = false;

        // Remove primitive collider and add fresh one
        Collider[] colliders = workObject.GetComponents<Collider>();
        foreach (Collider col in colliders)
        {
            DestroyImmediate(col);
        }
        workObject.AddComponent<BoxCollider>();

        // Visual feedback
        Renderer renderer = workObject.GetComponent<Renderer>();
        renderer.material.color = new Color(1, 0.5f, 0, 1);  // Orange for visibility

        Debug.Log($"[PayloadTestSetup] WorkObject created at {workObject.transform.position}");
        Debug.Log($"[PayloadTestSetup] Mass: {rb.mass}kg | Position: ({workObject.transform.position.x:F3}, {workObject.transform.position.y:F3}, {workObject.transform.position.z:F3})");
    }

    public GameObject GetWorkObject() => workObject;
}
