"""Diagnostics: for chosen clip frames, which object/bone is lowest, and which arm parts clip into which body parts."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mathutils.bvhtree import BVHTree

OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["Gatekeeper_Rig"]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig]
for o in meshes:
    for m in o.modifiers:
        if m.type == "BEVEL":
            m.show_viewport = False
TESTS = [("Gatekeeper_Idle", 0), ("Gatekeeper_Horizontal_Sweep", 32), ("Gatekeeper_Overhead_Attack", 36), ("Gatekeeper_Multi_Arm_Attack", 64),
         ("Gatekeeper_Awakening", 40), ("Gatekeeper_Rage", 40), ("Gatekeeper_Death", 120), ("Gatekeeper_Rage", 12)]


def vgroup_of(o, vi):
    names = {g.index: g.name for g in o.vertex_groups}
    gs = o.data.vertices[vi].groups
    return names[gs[0].group] if gs else "?"


for clip, f in TESTS:
    rig.animation_data.action = bpy.data.actions[clip]
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    W = {}
    low = []
    for o in meshes:
        ev = o.evaluated_get(dg); m = ev.to_mesh()
        vs = [o.matrix_world @ v.co for v in m.vertices]; polys = [tuple(p.vertices) for p in m.polygons]
        ev.to_mesh_clear()
        W[o.name] = (vs, polys)
        i = min(range(len(vs)), key=lambda k: vs[k].z)
        low.append((round(vs[i].z * 16, 1), o.name, vgroup_of(o, i)))
    low.sort()
    print("LOW", clip, f, low[:4])
    # clipping: per-polygon bone of arm parts vs torso parts
    def polys_by_group(on):
        o = bpy.data.objects[on]
        names = {g.index: g.name for g in o.vertex_groups}
        out = {}
        for pi, p in enumerate(o.data.polygons):
            g = o.data.vertices[p.vertices[0]].groups
            out.setdefault(names[g[0].group] if g else "?", []).append(pi)
        return out
    arms = {}
    for on in ("GK_Arm_R", "GK_Arm_L", "GK_Arm_Extra_R", "GK_Arm_Extra_L", "GK_Armor_Arms"):
        for g, idx in polys_by_group(on).items():
            if g.startswith(("forearm", "hand", "finger", "thumb")):
                vs, polys = W[on]
                arms[(on, g)] = BVHTree.FromPolygons(vs, [polys[i] for i in idx])
    body = {}
    for on in ("GK_Torso", "GK_Head", "GK_Armor", "GK_Weapon"):
        for g, idx in polys_by_group(on).items():
            vs, polys = W[on]
            body[(on, g)] = BVHTree.FromPolygons(vs, [polys[i] for i in idx])
    hits = []
    for ka, ta in arms.items():
        for kb, tb in body.items():
            n = len(ta.overlap(tb))
            if n and not (ka[1].endswith("_R") and "extra" not in ka[1] and kb[0] == "GK_Weapon"):
                hits.append((n, ka[1], kb[0], kb[1]))
    hits.sort(reverse=True)
    print("CLIP", clip, f, hits[:6])
