using UnityEngine;
using UnityEngine.InputSystem;

/// <summary>
/// Lightweight desktop flycam for industrial environments.
/// Zero-alloc Update loop. Direct transform manipulation (no physics).
/// Uses New Input System.
/// </summary>
public class SimpleFlyCam : MonoBehaviour
{
    [Header("Movement")]
    [Tooltip("Units per second")]
    public float moveSpeed = 2.0f;

    [Header("Mouse Look")]
    [Tooltip("Sensitivity multiplier")]
    public float sensitivity = 2.0f;
    
    [Tooltip("Invert Y-axis (flight sim style)")]
    public bool invertY = false;

    // State (pre-allocated)
    private float rotationX = 0f;
    private float rotationY = 0f;
    
    // New Input System references
    private Mouse mouse;
    private Keyboard keyboard;

    void Start()
    {
        // Lock cursor for immersive control
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
        
        // Cache input devices
        mouse = Mouse.current;
        keyboard = Keyboard.current;
    }

    void Update()
    {
        if (mouse == null || keyboard == null) return;

        // === ROTATION (Mouse) ===
        Vector2 mouseDelta = mouse.delta.ReadValue();
        rotationY += mouseDelta.x * sensitivity * 0.1f; // Scale down raw delta
        rotationX += mouseDelta.y * sensitivity * 0.1f * (invertY ? 1f : -1f);
        
        // Clamp pitch to prevent gimbal lock
        rotationX = Mathf.Clamp(rotationX, -90f, 90f);

        // Apply rotation (Euler is fast for camera-only transforms)
        transform.localEulerAngles = new Vector3(rotationX, rotationY, 0f);

        // === TRANSLATION (WASD + QE) ===
        Vector3 moveDir = Vector3.zero;
        
        // Horizontal (A/D)
        if (keyboard.aKey.isPressed) moveDir -= transform.right;
        if (keyboard.dKey.isPressed) moveDir += transform.right;
        
        // Forward (W/S)
        if (keyboard.wKey.isPressed) moveDir += transform.forward;
        if (keyboard.sKey.isPressed) moveDir -= transform.forward;
        
        // Elevation (Q/E)
        if (keyboard.eKey.isPressed) moveDir.y += 1f;
        if (keyboard.qKey.isPressed) moveDir.y -= 1f;

        // Apply movement (Time.deltaTime for frame-rate independence)
        transform.position += moveDir.normalized * moveSpeed * Time.deltaTime;

        // === CURSOR UNLOCK (Escape) ===
        if (keyboard.escapeKey.wasPressedThisFrame)
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }
    }

    void OnDisable()
    {
        // Release cursor when ViewManager switches to VR
        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;
    }
}
