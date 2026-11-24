"""Re-import the exported Gatekeeper.fbx into an empty scene and verify rig, skinning, clips, scale and a posed frame."""
import bpy, sys, os
OUT = sys.argv[sys.argv.index("--") + 1]
fbx = os.path.join(OUT, "Unity_Gatekeeper", "Gatekeeper.fbx")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx, use_anim=True)
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
skinned = [o.name for o in meshes if any(m.type == "ARMATURE" for m in o.modifiers)]
acts = sorted(a.name for a in bpy.data.actions)
arm = arms[0]
bones = [b.name for b in arm.data.bones]
need = ["weapon", "socket_hand_R", "socket_hand_L", "socket_extra_R", "socket_extra_L", "upperarm_extra_L", "forearm_extra_R", "hand_extra_L",
        "finger1_extra_R", "chain_shoulder_L", "fx_fire_R", "root"]
print("REIMPORT armatures", len(arms), "bones", len(bones), "meshes", len(meshes), "skinned", len(skinned))
print("REIMPORT missing_bones", [b for b in need if b not in bones])
print("REIMPORT actions", len(acts))
for a in acts:
    print("  ", a, tuple(round(x) for x in bpy.data.actions[a].frame_range))
dg = bpy.context.evaluated_depsgraph_get()
zs = []
for o in meshes:
    ev = o.evaluated_get(dg); m = ev.to_mesh()
    vs = m.vertices
    zs += [(o.matrix_world @ vs[i].co).z for i in range(0, len(vs), 5)]
    ev.to_mesh_clear()
print("REIMPORT height_m", round(max(zs) - min(zs), 2), "lowest_m", round(min(zs), 3))
over = [a for a in acts if "Overhead" in a]
if over:
    arm.animation_data.action = bpy.data.actions[over[0]]
    bpy.context.scene.frame_set(34)
    pb = arm.pose.bones["weapon"]
    print("REIMPORT overhead_f34_weapon_head_z", round((arm.matrix_world @ pb.head).z, 2))
print("VERIFY_OK")
