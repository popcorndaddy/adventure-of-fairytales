"""Stage 4 - export the Gatekeeper for Unity (FBX + textures + clip table), then re-import the FBX to verify it."""
import bpy, sys, os, json, shutil
sys.path.insert(0, os.path.dirname(__file__))

OUT = sys.argv[sys.argv.index("--") + 1]
UNITY = os.path.join(OUT, "Unity_Gatekeeper")
os.makedirs(os.path.join(UNITY, "Textures"), exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["Gatekeeper_Rig"]
clips = {k: list(v) for k, v in scene["gk_clips"].items()}

# final, clean .blend for the user: arena hidden from render, rig in rest-state idle
arena = bpy.data.collections.get("Preview_Arena")
if arena:
    arena.hide_render = False
rig.animation_data.action = bpy.data.actions["Gatekeeper_Idle"]
scene.frame_start, scene.frame_end = 0, 160
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Gatekeeper.blend"))

# ---------------------------------------------------------------- FBX for Unity
bpy.ops.object.select_all(action="DESELECT")
root = bpy.data.collections["Gatekeeper_Root"]
for o in root.all_objects:
    if o.type in ("ARMATURE", "MESH"):
        o.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx = os.path.join(UNITY, "Gatekeeper.fbx")
bpy.ops.export_scene.fbx(
    filepath=fbx, use_selection=True, object_types={"ARMATURE", "MESH"},
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False,
    add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X", use_armature_deform_only=False,
    bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=True,
    bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
    axis_forward="-Z", axis_up="Y", apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
    path_mode="COPY", embed_textures=True)
print("FBX_SIZE_MB", round(os.path.getsize(fbx) / 1e6, 2))

for f in os.listdir(os.path.join(OUT, "textures")):
    shutil.copy(os.path.join(OUT, "textures", f), os.path.join(UNITY, "Textures", f))

mats = {}
for m in bpy.data.materials:
    if m.name.startswith("GK_"):
        mats[m.name] = {"albedo": f"{m.name}_Albedo.png", "emission": f"{m.name}_Emission.png",
                        "emission_strength": float(m.get("gk_emission_strength", 0)),
                        "metallic": m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value,
                        "smoothness": 1 - m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value}
bones = [b.name for b in rig.data.bones]
events = json.loads(scene["gk_events"])
RM = ("Gatekeeper_Walking", "Gatekeeper_Heavy_Walk", "Gatekeeper_Sword_Drag", "Gatekeeper_Entrance")
json.dump({"clips": {k: {"first": v[0], "last": v[1], "loop": bool(v[2]), "root_motion": k in RM, "events": events.get(k, {})} for k, v in clips.items()},
           "materials": mats, "sockets": [b for b in bones if b.startswith("socket_") or b == "weapon"], "fps": scene.render.fps},
          open(os.path.join(UNITY, "gatekeeper_manifest.json"), "w"), indent=2)
with open(os.path.join(UNITY, "gatekeeper_events.txt"), "w") as fh:
    for k, v in clips.items():
        for ev, frames in events.get(k, {}).items():
            for fr in frames:
                fh.write(f"{k}|{ev}|{fr}|{v[1]}\n")
HERE = os.path.dirname(__file__)
os.makedirs(os.path.join(UNITY, "Editor"), exist_ok=True)
shutil.copy(os.path.join(HERE, "GatekeeperImporter.cs"), os.path.join(UNITY, "Editor", "GatekeeperImporter.cs"))
shutil.copy(os.path.join(HERE, "GatekeeperFX.cs"), os.path.join(UNITY, "GatekeeperFX.cs"))
shutil.copy(os.path.join(HERE, "README_Unity.md"), os.path.join(UNITY, "README.md"))
os.makedirs(os.path.join(UNITY, "Audio"), exist_ok=True)
for f in os.listdir(os.path.join(OUT, "sounds")):
    shutil.copy(os.path.join(OUT, "sounds", f), os.path.join(UNITY, "Audio", f))

# static portal arena for Unity
import gk_arena as AR
acol, _, _ = AR.build(length=300)
bpy.ops.object.select_all(action="DESELECT")
for o in acol.objects:
    if o.type == "MESH" and o.name in ("Arena_Floor", "Arena_PortalGate", "Arena_PortalSurface", "Arena_Pillars_Chains_Rubble", "Arena_Fissures_Glyphs"):
        o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(UNITY, "Gatekeeper_PortalArena.fbx"), use_selection=True, object_types={"MESH"},
                         mesh_smooth_type="FACE", axis_forward="-Z", axis_up="Y", apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
                         path_mode="COPY", embed_textures=True, bake_anim=False)
print("ARENA_FBX_OK")

# ---------------------------------------------------------------- verify: re-import the FBX into an empty scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx, use_anim=True)
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
skinned = [o.name for o in meshes if any(m.type == "ARMATURE" for m in o.modifiers)]
acts = sorted(a.name for a in bpy.data.actions)
dims = arms[0].dimensions if arms else None
from mathutils import Vector
zs = []
for o in meshes:
    for v in o.data.vertices[::5]:
        zs.append((o.matrix_world @ v.co).z)
print("REIMPORT armatures", len(arms), "bones", len(arms[0].data.bones) if arms else 0, "meshes", len(meshes), "skinned", len(skinned))
print("REIMPORT height_m", round(max(zs) - min(zs), 2), "lowest", round(min(zs), 3))
print("REIMPORT actions", len(acts), acts)
print("STAGE4_OK")
