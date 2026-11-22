"""Stage 7 - convert the Blender Gatekeeper (gatekeeper_stage3.blend) into GeckoLib assets for the Forge mod:
geo/gatekeeper.geo.json, animations/gatekeeper.animation.json, textures/entity/gatekeeper.png (+ _glowmask.png).

Coordinate conversion: Blender (X right, Y back, Z up; model faces -Y) -> Blockbench/GeckoLib internal space
(x, y up, z; model faces -Z) via  (x, y, z) -> (-x, z, y); file x is the negated internal x (Bedrock convention).
Rotations use GeckoLib's order R = Rz*Ry*Rx with file angles (-x, -y, z)."""
import bpy, sys, os, json, math, random
import numpy as np
from mathutils import Matrix, Vector

ART = sys.argv[sys.argv.index("--") + 1]          # gatekeeper-art folder
ASSETS = sys.argv[sys.argv.index("--") + 2]       # mod assets/aof_gatekeeper folder
bpy.ops.wm.open_mainfile(filepath=os.path.join(ART, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["Gatekeeper_Rig"]
for d in ("geo", "animations", "textures/entity"):
    os.makedirs(os.path.join(ASSETS, d), exist_ok=True)

M3 = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))     # Blender -> internal
M3i = M3.transposed()


def to_int(v):
    return M3 @ Vector(v)


def euler_zyx(R):
    m31 = max(-1.0, min(1.0, R[2][0]))
    ay = math.asin(-m31)
    if abs(m31) < 0.9999999:
        ax = math.atan2(R[2][1], R[2][2]); az = math.atan2(R[1][0], R[0][0])
    else:
        ax = 0.0; az = math.atan2(-R[0][1], R[1][1])
    return ax, ay, az


def file_rot(R_int):
    ax, ay, az = euler_zyx(R_int)
    return [round(-math.degrees(ax), 3), round(-math.degrees(ay), 3), round(math.degrees(az), 3)]


R6 = lambda v: round(v, 4)

# ------------------------------------------------------------------ texture atlas (4x4 tiles of 64 px)
MATS = ["CorruptedStone", "RuneStone", "AncientDarkIron", "WeatheredBronze", "DarkSteel", "TatteredCloth", "ChainIron",
        "PurpleEnergy", "CyanRunes", "MagentaFragments", "EyeGlow", "FireEnergy"]
TILE = {m: ((i % 4) * 64, (i // 4) * 64) for i, m in enumerate(MATS)}
W = H = 256
alb = np.zeros((H, W, 4), dtype=np.float32); alb[..., 3] = 1.0
glw = np.zeros((H, W, 4), dtype=np.float32)


def load(path):
    im = bpy.data.images.load(path)
    a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(a)
    a = a.reshape(im.size[1], im.size[0], 4)[::-1]          # top-down rows
    bpy.data.images.remove(im)
    return a


for m, (tx, ty) in TILE.items():
    a = load(os.path.join(ART, "textures", f"GK_{m}_Albedo.png"))
    e = load(os.path.join(ART, "textures", f"GK_{m}_Emission.png"))
    alb[ty:ty + 64, tx:tx + 64] = a
    lit = (e[..., :3].max(axis=2) > 0.02)
    g = np.zeros((64, 64, 4), dtype=np.float32)
    g[lit, :3] = a[lit, :3]; g[lit, 3] = 1.0
    glw[ty:ty + 64, tx:tx + 64] = g


def save(arr, path):
    img = bpy.data.images.new(os.path.basename(path), W, H, alpha=True)
    img.pixels.foreach_set(arr[::-1].ravel())
    img.filepath_raw = path; img.file_format = "PNG"; img.save()


save(alb, os.path.join(ASSETS, "textures/entity/gatekeeper.png"))
save(glw, os.path.join(ASSETS, "textures/entity/gatekeeper_glowmask.png"))

# ------------------------------------------------------------------ geometry
rnd = random.Random(3)
bones_out = {}
for b in rig.data.bones:
    h = to_int(b.head_local * 16)
    e = {"name": b.name, "pivot": [R6(-h.x), R6(h.y), R6(h.z)]}
    if b.parent:
        e["parent"] = b.parent.name
    bones_out[b.name] = e

FACE_OF = {0: "north", 1: "south", 2: "east", 3: "west", 4: "up", 5: "down"}   # builder order: front, back, left, right, top, bottom
n_cubes = 0
for o in bpy.data.objects:
    if o.type != "MESH" or o.parent != rig:
        continue
    me = o.data
    names = {g.index: g.name for g in o.vertex_groups}
    mats = [s.material.name[3:] if s.material else "CorruptedStone" for s in o.material_slots]
    nbox = len(me.vertices) // 8
    for bi in range(nbox):
        V = [o.matrix_world @ me.vertices[bi * 8 + k].co * 16 for k in range(8)]
        gs = me.vertices[bi * 8].groups
        bone = names[gs[0].group] if gs else "root"
        e1, e2, e3 = V[1] - V[0], V[3] - V[0], V[4] - V[0]
        sx, sz, sy = e1.length, e2.length, e3.length
        if min(sx, sy, sz) < 1e-4:
            continue
        Xi = -(M3 @ e1.normalized()); Yi = M3 @ e3.normalized(); Zi = M3 @ e2.normalized()
        R = Matrix((Xi, Yi, Zi)).transposed()
        c = to_int(sum(V, Vector()) / 8)
        frm = c - Vector((sx, sy, sz)) / 2
        cube = {"origin": [R6(-(frm.x + sx)), R6(frm.y), R6(frm.z)], "size": [R6(sx), R6(sy), R6(sz)], "uv": {}}
        rot = file_rot(R)
        if any(abs(a) > 1e-3 for a in rot):
            cube["pivot"] = [R6(-c.x), R6(c.y), R6(c.z)]
            cube["rotation"] = rot
        dims = {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}
        for k in range(6):
            poly = me.polygons[bi * 6 + k]
            mat = mats[poly.material_index] if poly.material_index < len(mats) else "CorruptedStone"
            face = FACE_OF[k]
            w, hh = dims[face]
            w, hh = min(max(w, 0.5), 64), min(max(hh, 0.5), 64)
            tx, ty = TILE.get(mat, TILE["CorruptedStone"])
            ox = rnd.uniform(0, 64 - w); oy = rnd.uniform(0, 64 - hh)
            cube["uv"][face] = {"uv": [R6(tx + ox), R6(ty + oy)], "uv_size": [R6(w), R6(hh)]}
        bones_out[bone].setdefault("cubes", []).append(cube)
        n_cubes += 1

geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.gatekeeper", "texture_width": W, "texture_height": H,
                    "visible_bounds_width": 14, "visible_bounds_height": 12, "visible_bounds_offset": [0, 5, 0]},
    "bones": list(bones_out.values())}]}
json.dump(geo, open(os.path.join(ASSETS, "geo/gatekeeper.geo.json"), "w"), separators=(",", ":"))
print("GEO cubes", n_cubes, "bones", len(bones_out))

# ------------------------------------------------------------------ animations
clips = {k: list(v) for k, v in scene["gk_clips"].items()}
S = Matrix.Scale(16, 4)
Si = Matrix.Scale(1 / 16, 4)
order = [b.name for b in rig.data.bones]
heads = {b.name: b.head_local * 16 for b in rig.data.bones}


def world_delta():
    out = {}
    for pb in rig.pose.bones:
        Wm = pb.matrix @ pb.bone.matrix_local.inverted()
        out[pb.name] = S @ Wm @ Si                       # pixel space
    return out


def sample_clip(action_name, f0, f1, step):
    rig.animation_data.action = bpy.data.actions[action_name]
    frames = list(range(int(f0), int(f1) + 1, step))
    if frames[-1] != int(f1):
        frames.append(int(f1))
    tracks = {b: {"rotation": {}, "position": {}, "scale": {}} for b in order}
    for f in frames:
        scene.frame_set(f)
        Wd = world_delta()
        t = f"{(f - f0) / 30.0:.4f}"
        for name in order:
            pb = rig.pose.bones[name]
            Q = (Wd[pb.parent.name].inverted() @ Wd[name]) if pb.parent else Wd[name].copy()
            loc, quat, scl = Q.decompose()
            D = quat.to_matrix()
            p = heads[name]
            pos = (Q @ p) - p
            if name == "root":
                pos = Vector((0, 0, pos.z))               # Minecraft moves the entity itself: no root motion
            ri = M3 @ D @ M3i
            tracks[name]["rotation"][t] = file_rot(ri)
            pi = M3 @ pos
            tracks[name]["position"][t] = [R6(-pi.x), R6(pi.y), R6(pi.z)]
            tracks[name]["scale"][t] = [R6(scl.x), R6(scl.y), R6(scl.z)]
    out = {}
    for name, ch in tracks.items():
        o = {}
        for cname, keys in ch.items():
            ident = [1, 1, 1] if cname == "scale" else [0, 0, 0]
            if all(all(abs(a - b) < 1e-3 for a, b in zip(v, ident)) for v in keys.values()):
                continue
            o[cname] = {k: v for k, v in keys.items()}
        if o:
            out[name] = o
    return out, (frames[-1] - f0) / 30.0


LOOP = {"Gatekeeper_Idle", "Gatekeeper_Walking", "Gatekeeper_Heavy_Walk", "Gatekeeper_Sword_Drag"}
HOLD = {"Gatekeeper_Death", "Gatekeeper_Block", "Gatekeeper_Awakening", "Gatekeeper_Entrance"}
anims = {}
for name, (f0, f1, loop) in clips.items():
    bones, length = sample_clip(name, f0, f1, 1 if name in ("Gatekeeper_Overhead_Attack", "Gatekeeper_Horizontal_Sweep", "Gatekeeper_Multi_Arm_Attack") else 2)
    a = {"animation_length": round(length, 4), "bones": bones}
    if name in LOOP:
        a["loop"] = True
    elif name in HOLD:
        a["loop"] = "hold_on_last_frame"
    anims["animation.gatekeeper." + name.replace("Gatekeeper_", "").lower()] = a
    print("ANIM", name, round(length, 2), "s", len(bones), "bones", flush=True)
# dormant pose = first frame of the awakening, held
f0 = clips["Gatekeeper_Awakening"][0]
bones, _ = sample_clip("Gatekeeper_Awakening", f0, f0, 1)
anims["animation.gatekeeper.dormant"] = {"loop": True, "animation_length": 0.05,
                                         "bones": {b: {c: {"0.0000": list(v.values())[0]} for c, v in ch.items()} for b, ch in bones.items()}}
json.dump({"format_version": "1.8.0", "animations": anims}, open(os.path.join(ASSETS, "animations/gatekeeper.animation.json"), "w"), separators=(",", ":"))
print("ANIMS", len(anims), "size_mb", round(os.path.getsize(os.path.join(ASSETS, "animations/gatekeeper.animation.json")) / 1e6, 2))
print("CONVERT_OK")
