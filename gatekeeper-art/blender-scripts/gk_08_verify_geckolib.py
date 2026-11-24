"""Verify the GeckoLib export: rebuild cube corners from geo.json + animation.json using GeckoLib's own math
(as read from the 4.8.5 bytecode) and compare with the original Blender model, at rest and mid-animation."""
import bpy, sys, os, json, math
from mathutils import Matrix, Vector

ART = sys.argv[sys.argv.index("--") + 1]
ASSETS = sys.argv[sys.argv.index("--") + 2]
bpy.ops.wm.open_mainfile(filepath=os.path.join(ART, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["Gatekeeper_Rig"]
geo = json.load(open(os.path.join(ASSETS, "geo/gatekeeper.geo.json")))["minecraft:geometry"][0]
anims = json.load(open(os.path.join(ASSETS, "animations/gatekeeper.animation.json")))["animations"]
bones = {b["name"]: b for b in geo["bones"]}
M3 = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))


def Rzyx(x, y, z):   # radians, GeckoLib internal: mulPose Z, then Y, then X
    return (Matrix.Rotation(z, 4, "Z") @ Matrix.Rotation(y, 4, "Y") @ Matrix.Rotation(x, 4, "X"))


def interp(track, t):
    ks = sorted((float(k), v) for k, v in track.items())
    if t <= ks[0][0]:
        return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t0 <= t <= t1:
            a = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return [p + (q - p) * a for p, q in zip(v0, v1)]
    return ks[-1][1]


def bone_world(name, anim, t, cache):
    if name in cache:
        return cache[name]
    b = bones[name]
    pv = Vector((-b["pivot"][0], b["pivot"][1], b["pivot"][2]))          # internal
    a = anim.get(name, {}) if anim else {}
    pos = interp(a["position"], t) if "position" in a else [0, 0, 0]
    rot = interp(a["rotation"], t) if "rotation" in a else [0, 0, 0]
    scl = interp(a["scale"], t) if "scale" in a else [1, 1, 1]
    L = (Matrix.Translation((-pos[0], pos[1], pos[2])) @ Matrix.Translation(pv)
         @ Rzyx(math.radians(-rot[0]), math.radians(-rot[1]), math.radians(rot[2]))
         @ Matrix.Diagonal((scl[0], scl[1], scl[2], 1)) @ Matrix.Translation(-pv))
    Wm = bone_world(b["parent"], anim, t, cache) @ L if "parent" in b else L
    cache[name] = Wm
    return Wm


def gecko_points(anim, t):
    pts = []
    cache = {}
    for name, b in bones.items():
        Wb = bone_world(name, anim, t, cache)
        for c in b.get("cubes", []):
            sx, sy, sz = c["size"]
            ox = -(c["origin"][0] + sx); oy, oz = c["origin"][1], c["origin"][2]
            corners = [Vector((ox + dx * sx, oy + dy * sy, oz + dz * sz)) for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
            if "rotation" in c:
                pv = Vector((-c["pivot"][0], c["pivot"][1], c["pivot"][2]))
                r = c["rotation"]
                Rc = Matrix.Translation(pv) @ Rzyx(math.radians(-r[0]), math.radians(-r[1]), math.radians(r[2])) @ Matrix.Translation(-pv)
                corners = [Rc @ p for p in corners]
            pts += [M3.transposed() @ (Wb @ p).to_3d() for p in corners]   # back to Blender space (px)
    return pts


def blender_points():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.parent == rig:
            for m in o.modifiers:
                if m.type == "BEVEL":
                    m.show_viewport = False
            ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
            pts += [(o.matrix_world @ v.co) * 16 for v in me.vertices]
            ev.to_mesh_clear()
    return pts


def compare(tag, gp, bp):
    from mathutils.kdtree import KDTree
    kd = KDTree(len(bp))
    for i, p in enumerate(bp):
        kd.insert(p, i)
    kd.balance()
    d = sorted(kd.find(p)[2] for p in gp)
    print(f"CHECK {tag}: cubes-corners {len(gp)}  median {d[len(d)//2]:.3f}px  95% {d[int(len(d)*0.95)]:.3f}px  max {d[-1]:.3f}px")


rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
compare("rest", gecko_points(None, 0), blender_points())
clips = {k: list(v) for k, v in scene["gk_clips"].items()}
for clip, f in (("Gatekeeper_Overhead_Attack", 34), ("Gatekeeper_Horizontal_Sweep", 26), ("Gatekeeper_Multi_Arm_Attack", 30),
                ("Gatekeeper_Idle", 40), ("Gatekeeper_Death", 120)):
    rig.animation_data.action = bpy.data.actions[clip]
    scene.frame_set(f)
    # Blender reference without root motion (the export strips horizontal root movement)
    rp = rig.pose.bones["root"]
    rp.location = (rp.location.x, rp.location.y, rp.location.z)
    bp = blender_points()
    root_off = rig.pose.bones["root"].matrix.translation * 16
    bp = [p - Vector((root_off.x, root_off.y, 0)) for p in bp]
    a = anims["animation.gatekeeper." + clip.replace("Gatekeeper_", "").lower()]["bones"]
    compare(f"{clip}@{f}", gecko_points(a, (f - clips[clip][0]) / 30.0), bp)
print("VERIFY_OK")
