using UnityEngine;
using UnityEngine.InputSystem;
#if UNITY_XR_MANAGEMENT
using UnityEngine.XR.Management;
#endif
using System.Collections;

/// <summary>
/// Toggles between Desktop and VR camera rigs.
/// Zero-allocation hot path. XR subsystems start/stop on demand.
/// </summary>
public class ViewManager : MonoBehaviour
{
    [Header("Camera Rigs")]
    [Tooltip("Desktop camera rig (active by default)")]
    public GameObject desktopRig;
    
    [Tooltip("VR camera rig (XR Headset)")]
    public GameObject vrRig;

    [Header("Audio Safety")]
    [Tooltip("AudioListener on Desktop camera")]
    public AudioListener desktopAudioListener;
    
    [Tooltip("AudioListener on VR camera")]
    public AudioListener vrAudioListener;

    // State tracking (avoid LINQ/allocations in Update)
    private bool isVRMode = false;
    private bool isXRInitialized = false;
    private Keyboard keyboard;

    void Start()
    {
        keyboard = Keyboard.current;
        // Default: Desktop Mode
        ActivateDesktopMode();
    }

    void Update()
    {
        if (keyboard == null) return;

        // Toggle on 'V' key (single-frame detection, zero-alloc)
        if (keyboard.vKey.wasPressedThisFrame)
        {
            if (isVRMode)
            {
                ActivateDesktopMode();
            }
            else
            {
                ActivateVRMode();
            }
        }
    }

    /// <summary>
    /// Switch to Desktop camera. Stop XR subsystems.
    /// </summary>
    private void ActivateDesktopMode()
    {
        // Stop XR to save CPU/GPU when not in VR
        if (isXRInitialized)
        {
            StartCoroutine(StopXR());
        }

        // Enable Desktop, Disable VR
        if (desktopRig != null) desktopRig.SetActive(true);
        if (vrRig != null) vrRig.SetActive(false);

        // Audio Safety: Only one AudioListener active
        if (desktopAudioListener != null) desktopAudioListener.enabled = true;
        if (vrAudioListener != null) vrAudioListener.enabled = false;

        isVRMode = false;
        Debug.Log("[ViewManager] Desktop Mode Activated");
    }

    /// <summary>
    /// Switch to VR camera. Start XR subsystems.
    /// </summary>
    private void ActivateVRMode()
    {
        // Start XR subsystems
        if (!isXRInitialized)
        {
            StartCoroutine(StartXR());
        }

        // Enable VR, Disable Desktop
        if (desktopRig != null) desktopRig.SetActive(false);
        if (vrRig != null) vrRig.SetActive(true);

        // Audio Safety
        if (desktopAudioListener != null) desktopAudioListener.enabled = false;
        if (vrAudioListener != null) vrAudioListener.enabled = true;

        isVRMode = true;
        Debug.Log("[ViewManager] VR Mode Activated");
    }

    /// <summary>
    /// Initialize XR runtime. Runs async to prevent frame stutter.
    /// </summary>
    private IEnumerator StartXR()
    {
#if UNITY_XR_MANAGEMENT
        Debug.Log("[ViewManager] Initializing XR subsystems...");
        
        var xrManager = XRGeneralSettings.Instance.Manager;
        if (xrManager != null && !xrManager.isInitializationComplete)
        {
            yield return xrManager.InitializeLoader();

            if (xrManager.activeLoader != null)
            {
                xrManager.StartSubsystems();
                isXRInitialized = true;
                Debug.Log("[ViewManager] XR Started: " + xrManager.activeLoader.name);
            }
            else
            {
                Debug.LogError("[ViewManager] XR Loader failed to initialize. Check Project Settings > XR Plug-in Management.");
            }
        }
        else if (xrManager != null && xrManager.isInitializationComplete)
        {
            // Already initialized, just start subsystems
            xrManager.StartSubsystems();
            isXRInitialized = true;
        }
#else
        Debug.LogWarning("[ViewManager] XR Management not installed. Install XR Plugin Management package.");
        yield return null;
#endif
    }

    /// <summary>
    /// Stop XR runtime to save resources in Desktop mode.
    /// </summary>
    private IEnumerator StopXR()
    {
#if UNITY_XR_MANAGEMENT
        Debug.Log("[ViewManager] Stopping XR subsystems...");
        
        var xrManager = XRGeneralSettings.Instance.Manager;
        if (xrManager != null && xrManager.isInitializationComplete)
        {
            xrManager.StopSubsystems();
            yield return xrManager.DeinitializeLoader();
            isXRInitialized = false;
            Debug.Log("[ViewManager] XR Stopped");
        }
#else
        yield return null;
#endif
    }

    void OnDestroy()
    {
#if UNITY_XR_MANAGEMENT
        // Clean shutdown
        if (isXRInitialized)
        {
            var xrManager = XRGeneralSettings.Instance?.Manager;
            if (xrManager != null)
            {
                xrManager.StopSubsystems();
                xrManager.DeinitializeLoader();
            }
        }
#endif
    }
}
