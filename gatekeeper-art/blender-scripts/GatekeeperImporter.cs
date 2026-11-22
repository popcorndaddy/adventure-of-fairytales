// Ancient Gatekeeper - Unity import setup.
// Put this file in any "Editor" folder (e.g. Assets/Gatekeeper/Editor/). It configures the FBX, its clips and
// textures automatically on import, and adds  Tools > Gatekeeper > Build Materials  to create glowing URP/Standard
// materials from the exported textures and hook them up to the model.
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public class GatekeeperImporter : AssetPostprocessor
{
    static readonly HashSet<string> Loops = new HashSet<string> {
        "Gatekeeper_Idle", "Gatekeeper_Walking", "Gatekeeper_Heavy_Walk", "Gatekeeper_Sword_Drag" };
    static readonly HashSet<string> RootMotion = new HashSet<string> {
        "Gatekeeper_Walking", "Gatekeeper_Heavy_Walk", "Gatekeeper_Sword_Drag", "Gatekeeper_Entrance" };

    // material name -> (metallic, smoothness, emission intensity)
    static readonly Dictionary<string, Vector3> Mats = new Dictionary<string, Vector3> {
        { "GK_CorruptedStone",   new Vector3(0.0f,  0.08f, 0f) },
        { "GK_RuneStone",        new Vector3(0.0f,  0.10f, 1.6f) },
        { "GK_AncientDarkIron",  new Vector3(0.75f, 0.45f, 0f) },
        { "GK_WeatheredBronze",  new Vector3(0.8f,  0.50f, 0f) },
        { "GK_DarkSteel",        new Vector3(0.85f, 0.62f, 0f) },
        { "GK_TatteredCloth",    new Vector3(0.0f,  0.05f, 1f) },
        { "GK_ChainIron",        new Vector3(0.8f,  0.50f, 0f) },
        { "GK_PurpleEnergy",     new Vector3(0.0f,  0.60f, 4f) },
        { "GK_CyanRunes",        new Vector3(0.0f,  0.60f, 3.5f) },
        { "GK_MagentaFragments", new Vector3(0.0f,  0.60f, 5f) },
        { "GK_EyeGlow",          new Vector3(0.0f,  0.70f, 16f) },
        { "GK_FireEnergy",       new Vector3(0.0f,  0.60f, 6f) },
    };

    static bool IsGatekeeper(string path) => path.Replace('\\', '/').Contains("Gatekeeper");

    void OnPreprocessModel()
    {
        if (!IsGatekeeper(assetPath) || !assetPath.ToLower().EndsWith(".fbx")) return;
        var mi = (ModelImporter)assetImporter;
        mi.useFileScale = true;
        mi.globalScale = 1f;                       // 1 Minecraft block = 1 metre; the boss is ~8.4 m tall
        mi.importBlendShapes = false;
        mi.importAnimation = true;
        mi.animationType = ModelImporterAnimationType.Generic;
        mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        mi.motionNodeName = "Gatekeeper_Rig/root"; // root bone drives root motion on the walk clips
        mi.resampleCurves = false;
        mi.animationCompression = ModelImporterAnimationCompression.KeyframeReduction;
    }

    void OnPreprocessAnimation()
    {
        if (!IsGatekeeper(assetPath) || !assetPath.ToLower().EndsWith(".fbx")) return;
        var mi = (ModelImporter)assetImporter;
        var clips = mi.defaultClipAnimations;
        foreach (var c in clips)
        {
            string n = c.name.Contains("|") ? c.name.Substring(c.name.LastIndexOf('|') + 1) : c.name;
            c.name = n;
            c.loopTime = Loops.Contains(n);
            c.loopPose = c.loopTime;
            bool rm = RootMotion.Contains(n);
            c.lockRootRotation = true;              // bake rotation into pose (no root turning)
            c.lockRootHeightY = true;               // bake height into pose
            c.lockRootPositionXZ = !rm;             // walk clips move the character; everything else stays in place
            c.keepOriginalOrientation = true;
            c.keepOriginalPositionY = true;
            c.keepOriginalPositionXZ = true;
            c.events = EventsFor(n);
        }
        mi.clipAnimations = clips;
    }

    // gatekeeper_events.txt (written by the Blender export): clip|event|frame|lastFrame per line
    AnimationEvent[] EventsFor(string clip)
    {
        var list = new List<AnimationEvent>();
        string file = Path.Combine(Path.GetDirectoryName(assetPath), "gatekeeper_events.txt");
        if (!File.Exists(file)) return list.ToArray();
        foreach (var line in File.ReadAllLines(file))
        {
            var p = line.Split('|');
            if (p.Length < 4 || p[0] != clip) continue;
            float frame = float.Parse(p[2], System.Globalization.CultureInfo.InvariantCulture);
            float last = float.Parse(p[3], System.Globalization.CultureInfo.InvariantCulture);
            list.Add(new AnimationEvent { time = Mathf.Clamp01(frame / Mathf.Max(1f, last)), functionName = "OnGatekeeperEvent", stringParameter = p[1] });
        }
        return list.ToArray();
    }

    void OnPreprocessTexture()
    {
        if (!IsGatekeeper(assetPath) || !Path.GetFileName(assetPath).StartsWith("GK_")) return;
        var ti = (TextureImporter)assetImporter;
        ti.filterMode = FilterMode.Point;          // crisp voxel pixels
        ti.mipmapEnabled = false;
        ti.textureCompression = TextureImporterCompression.Uncompressed;
        ti.wrapMode = TextureWrapMode.Repeat;
        ti.sRGBTexture = true;
    }

    [MenuItem("Tools/Gatekeeper/Build Materials")]
    static void BuildMaterials()
    {
        string fbxPath = null;
        foreach (var guid in AssetDatabase.FindAssets("Gatekeeper t:Model"))
        {
            string p = AssetDatabase.GUIDToAssetPath(guid);
            if (p.ToLower().EndsWith(".fbx")) { fbxPath = p; break; }
        }
        if (fbxPath == null) { Debug.LogError("Gatekeeper.fbx not found in the project."); return; }
        string dir = Path.GetDirectoryName(fbxPath).Replace('\\', '/');
        string matDir = dir + "/Materials";
        if (!AssetDatabase.IsValidFolder(matDir)) AssetDatabase.CreateFolder(dir, "Materials");

        Shader urp = Shader.Find("Universal Render Pipeline/Lit");
        Shader sh = urp != null ? urp : Shader.Find("Standard");
        var importer = (ModelImporter)AssetImporter.GetAtPath(fbxPath);

        foreach (var kv in Mats)
        {
            string mp = $"{matDir}/{kv.Key}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(mp);
            if (mat == null) { mat = new Material(sh); AssetDatabase.CreateAsset(mat, mp); }
            mat.shader = sh;
            var alb = FindTex($"{kv.Key}_Albedo");
            var emi = FindTex($"{kv.Key}_Emission");
            if (urp != null) { mat.SetTexture("_BaseMap", alb); mat.SetFloat("_Smoothness", kv.Value.y); }
            else { mat.SetTexture("_MainTex", alb); mat.SetFloat("_Glossiness", kv.Value.y); }
            mat.SetFloat("_Metallic", kv.Value.x);
            if (kv.Value.z > 0f)
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetTexture("_EmissionMap", emi);
                mat.SetColor("_EmissionColor", Color.white * kv.Value.z);   // HDR intensity -> works with Bloom
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            else mat.DisableKeyword("_EMISSION");
            EditorUtility.SetDirty(mat);
            importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), mat);
        }
        AssetDatabase.SaveAssets();
        importer.SaveAndReimport();
        Debug.Log("Gatekeeper materials built and assigned. Add a Volume with Bloom to see the runes glow.");
    }

    static Texture2D FindTex(string name)
    {
        foreach (var guid in AssetDatabase.FindAssets(name + " t:Texture2D"))
        {
            string p = AssetDatabase.GUIDToAssetPath(guid);
            if (Path.GetFileNameWithoutExtension(p) == name) return AssetDatabase.LoadAssetAtPath<Texture2D>(p);
        }
        return null;
    }
}
