// Ancient Gatekeeper - runtime glow + animation-event hooks. Add to the Gatekeeper's root object (next to the Animator).
// - Eyes and core start dark and ignite on the "eyes_open" event of Gatekeeper_Awakening.
// - Runes pulse slowly (the ominous energy pulse).
// - Animation events (impact, shockwave, footstep, ...) spawn the prefab you assign and play an AudioClip.
// The Animation Events themselves are listed in gatekeeper_manifest.json and are added automatically on import.
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GatekeeperFX : MonoBehaviour
{
    [System.Serializable] public class FXEntry { public string eventName; public GameObject prefab; public AudioClip sound; public string attachBone = "root"; }

    [Header("Glow")]
    public Material eyeGlow;                // GK_EyeGlow
    public Material[] runeMaterials;        // GK_RuneStone, GK_PurpleEnergy, GK_CyanRunes, GK_MagentaFragments
    public float eyeIntensity = 16f, pulseSpeed = 0.25f, pulseDepth = 0.35f;
    public bool startDormant = true;

    [Header("Event effects")]
    public List<FXEntry> effects = new List<FXEntry>();
    public AudioSource audioSource;

    readonly Dictionary<Material, Color> baseEmission = new Dictionary<Material, Color>();
    float eyeLevel;

    void Awake()
    {
        foreach (var m in runeMaterials) if (m) baseEmission[m] = m.GetColor("_EmissionColor");
        eyeLevel = startDormant ? 0f : 1f;
        SetEyes(eyeLevel);
    }

    void Update()
    {
        float pulse = 1f - pulseDepth * 0.5f + pulseDepth * 0.5f * Mathf.Sin(Time.time * Mathf.PI * 2f * pulseSpeed);
        foreach (var kv in baseEmission) kv.Key.SetColor("_EmissionColor", kv.Value * pulse * Mathf.Lerp(0.1f, 1f, eyeLevel));
    }

    void SetEyes(float k)
    {
        if (eyeGlow) eyeGlow.SetColor("_EmissionColor", Color.white * eyeIntensity * k);
    }

    IEnumerator Ignite(float to, float seconds)
    {
        float from = eyeLevel, t = 0f;
        while (t < seconds) { t += Time.deltaTime; eyeLevel = Mathf.Lerp(from, to, t / seconds); SetEyes(eyeLevel); yield return null; }
        eyeLevel = to; SetEyes(to);
    }

    // ---- called by Animation Events (function name "OnGatekeeperEvent", string parameter = event name)
    public void OnGatekeeperEvent(string evt)
    {
        if (evt == "eyes_open") StartCoroutine(Ignite(1f, 0.6f));
        if (evt == "eyes_fade") StartCoroutine(Ignite(0f, 1.5f));
        foreach (var e in effects)
        {
            if (e.eventName != evt) continue;
            Transform at = FindDeep(transform, e.attachBone) ?? transform;
            if (e.prefab) Destroy(Instantiate(e.prefab, at.position, Quaternion.identity), 6f);
            if (e.sound && audioSource) audioSource.PlayOneShot(e.sound);
        }
    }

    static Transform FindDeep(Transform t, string n)
    {
        if (t.name == n) return t;
        foreach (Transform c in t) { var r = FindDeep(c, n); if (r) return r; }
        return null;
    }
}
