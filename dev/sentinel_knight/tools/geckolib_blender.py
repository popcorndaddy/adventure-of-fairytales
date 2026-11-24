"""GeckoLib <-> Blender bridge for animating GeckoLib/EntityJS models in Blender.

  Import:  blender -b --python geckolib_blender.py -- import  model.geo.json anims.animation.json texture.png out.blend
  Export:  blender -b in.blend --python geckolib_blender.py -- export  anims.animation.json

Conventions (matching GeckoLib 4 / Blockbench Bedrock):
  * Internal space = geo file with x negated. Blender = internal mapped (x, y, z) -> (-x, z, y), 16 px = 1 m.
  * Bones are axis-aligned in Blender (rest matrix = pure translation at the pivot), so a pose bone's
    rotation/location are exactly GeckoLib's per-bone rotation/position about the pivot.
  * Pose bones use Euler order XZY: Blender (X, Y, Z) = file (x, z, -y) in degrees -> radians.
    GeckoLib adds animation rotation to the bone's rest rotation, so Blender value = rest + animation.
  * Position: Blender location = file (x, z, y) / 16. Scale: Blender = file (x, z, y).
"""
import bpy, sys, os, json, math
from mathutils import Matrix, Vector

M3 = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))     # internal <-> Blender (symmetric, orthogonal)
FPS = 20                                            # 1 frame = 1 Minecraft tick


def to_b(v):
    """internal px -> Blender metres"""
    return (M3 @ Vector(v)) / 16.0


def rot_int(r):
    """GeckoLib cube/bone rotation (file degrees) -> internal rotation matrix (mulPose Z, Y, X)."""
    a, b, c = math.radians(-r[0]), math.radians(-r[1]), math.radians(r[2])
    return Matrix.Rotation(c, 3, "Z") @ Matrix.Rotation(b, 3, "Y") @ Matrix.Rotation(a, 3, "X")


def file_rot_to_euler(r):
    return (math.radians(r[0]), math.radians(r[2]), math.radians(-r[1]))


def euler_to_file_rot(e):
    return [math.degrees(e[0]), -math.degrees(e[2]), math.degrees(e[1])]


# ------------------------------------------------------------------------------------------ IMPORT
def import_model(geo_path, anim_path, tex_path, out_blend):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    geo = json.load(open(geo_path))["minecraft:geometry"][0]
    desc = geo["description"]
    TW, TH = desc["texture_width"], desc["texture_height"]
    bones = geo["bones"]
    name = desc["identifier"].replace("geometry.", "")

    # texture material (pixel-crisp)
    img = bpy.data.images.load(tex_path); img.pack()
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img; tx.interpolation = "Closest"
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"]); nt.links.new(tx.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.9
    try:
        mat.blend_method = "CLIP"
    except Exception:
        pass

    # armature: one axis-aligned bone per GeckoLib bone, head at the pivot
    arm = bpy.data.armatures.new(name + "_rig"); rig = bpy.data.objects.new(name + "_rig", arm)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for b in bones:
        eb = arm.edit_bones.new(b["name"])
        p = b.get("pivot", [0, 0, 0])
        h = to_b((-p[0], p[1], p[2]))
        eb.head = h; eb.tail = h + Vector((0, 0.25, 0)); eb.roll = 0
    for b in bones:
        if b.get("parent"):
            arm.edit_bones[b["name"]].parent = arm.edit_bones[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "OCTAHEDRAL"; rig.show_in_front = True
    rest = {}
    for b in bones:
        pb = rig.pose.bones[b["name"]]
        pb.rotation_mode = "XZY"
        r = b.get("rotation", [0, 0, 0])
        rest[b["name"]] = r
        pb["gk_rest_rotation"] = list(r)
        pb.rotation_euler = file_rot_to_euler(r)

    # mesh: every cube as an 8-vertex box, weighted 100% to its bone
    verts, faces, uvs, groups = [], [], [], []
    QUADS = {  # TL, TR, BR, BL corners (internal space) as Blockbench maps a face's uv rectangle
        "north": lambda f, t: [(t[0], t[1], f[2]), (f[0], t[1], f[2]), (f[0], f[1], f[2]), (t[0], f[1], f[2])],
        "south": lambda f, t: [(f[0], t[1], t[2]), (t[0], t[1], t[2]), (t[0], f[1], t[2]), (f[0], f[1], t[2])],
        "east": lambda f, t: [(t[0], t[1], t[2]), (t[0], t[1], f[2]), (t[0], f[1], f[2]), (t[0], f[1], t[2])],
        "west": lambda f, t: [(f[0], t[1], f[2]), (f[0], t[1], t[2]), (f[0], f[1], t[2]), (f[0], f[1], f[2])],
        "up": lambda f, t: [(f[0], t[1], f[2]), (t[0], t[1], f[2]), (t[0], t[1], t[2]), (f[0], t[1], t[2])],
        "down": lambda f, t: [(f[0], f[1], t[2]), (t[0], f[1], t[2]), (t[0], f[1], f[2]), (f[0], f[1], f[2])],
    }
    for b in bones:
        for c in b.get("cubes", []):
            s = c["size"]; o = c["origin"]; inf = c.get("inflate", 0)
            f = [-(o[0] + s[0]) - inf, o[1] - inf, o[2] - inf]
            t = [-o[0] + inf, o[1] + s[1] + inf, o[2] + s[2] + inf]
            R = None
            if c.get("rotation") and any(c["rotation"]):
                pv = c.get("pivot", [0, 0, 0]); piv = Vector((-pv[0], pv[1], pv[2])); R = rot_int(c["rotation"])
            for face, uvd in c.get("uv", {}).items():
                if face not in QUADS:
                    continue
                u, v = uvd["uv"]; w, hh = uvd["uv_size"]
                if face in ("up", "down"):
                    u1, v1, u2, v2 = u + w, v + hh, u, v
                else:
                    u1, v1, u2, v2 = u, v, u + w, v + hh
                corners = [Vector(p) for p in QUADS[face](f, t)]
                if R is not None:
                    corners = [R @ (p - piv) + piv for p in corners]
                tl, tr, br, bl = [to_b(p) for p in corners]
                base = len(verts)
                verts += [tuple(bl), tuple(br), tuple(tr), tuple(tl)]
                faces.append((base, base + 1, base + 2, base + 3))
                uvs.append([(u1 / TW, 1 - v2 / TH), (u2 / TW, 1 - v2 / TH), (u2 / TW, 1 - v1 / TH), (u1 / TW, 1 - v1 / TH)])
                groups.append(b["name"])
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    lay = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, uvs):
        for li, cc in zip(poly.loop_indices, uv):
            lay.data[li].uv = cc
    me.materials.append(mat); me.update()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    for gname in set(groups):
        vg = ob.vertex_groups.new(name=gname)
        idx = [k for fi, g in enumerate(groups) if g == gname for k in range(fi * 4, fi * 4 + 4)]
        vg.add(idx, 1.0, "REPLACE")
    ob.parent = rig
    ob.modifiers.new("Armature", "ARMATURE").object = rig
    ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))

    # animations -> actions
    anims = json.load(open(anim_path))["animations"]
    rig.animation_data_create()
    for aname, a in anims.items():
        act = bpy.data.actions.new(aname.split(".")[-1]); act.use_fake_user = True
        act["gk_name"] = aname
        act["gk_length"] = float(a.get("animation_length", 0))
        act["gk_loop"] = json.dumps(a.get("loop", False))
        rig.animation_data.action = act
        for bname, bd in a.get("bones", {}).items():
            if bname not in rig.pose.bones:
                print("WARN unknown bone", bname, "in", aname); continue
            pb = rig.pose.bones[bname]
            for ch, frames in bd.items():
                if isinstance(frames, list):
                    frames = {"0.0": frames}
                for t, k in sorted(frames.items(), key=lambda kv: float(kv[0])):
                    val = k["post"] if isinstance(k, dict) else k
                    fr = float(t) * FPS
                    if ch == "rotation":
                        r = [val[i] + rest[bname][i] for i in range(3)]
                        pb.rotation_euler = file_rot_to_euler(r); pb.keyframe_insert("rotation_euler", frame=fr, group=bname)
                    elif ch == "position":
                        pb.location = (val[0] / 16, val[2] / 16, val[1] / 16); pb.keyframe_insert("location", frame=fr, group=bname)
                    elif ch == "scale":
                        sv = val if isinstance(val, list) else [val] * 3
                        pb.scale = (sv[0], sv[2], sv[1]); pb.keyframe_insert("scale", frame=fr, group=bname)
        # bones with a rest rotation but no rotation keys still need their rest pose shown
        for bname, r in rest.items():
            if any(r) and "rotation" not in a.get("bones", {}).get(bname, {}):
                pb = rig.pose.bones[bname]; pb.rotation_euler = file_rot_to_euler(r)
                pb.keyframe_insert("rotation_euler", frame=0, group=bname)
        act.frame_range = (0, max(1.0, act["gk_length"] * FPS))
        for fc in _fcurves(act):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO"   # ~ Catmull-Rom
        print("ACTION", act.name, "len", act["gk_length"], "loop", act["gk_loop"])
    first = next(iter(anims)).split(".")[-1]
    rig.animation_data.action = bpy.data.actions[first]
    scene.frame_start, scene.frame_end = 0, int(bpy.data.actions[first].frame_range[1])
    scene["gk_geo"] = geo_path; scene["gk_anim"] = anim_path
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print("IMPORT_OK", out_blend, len(verts) // 4, "faces", len(anims), "animations")


def _fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
        return out


# ------------------------------------------------------------------------------------------ EXPORT
def export_animations(anim_path, only=None):
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    data = json.load(open(anim_path)) if os.path.exists(anim_path) else {"format_version": "1.8.0", "animations": {}}
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    for act in bpy.data.actions:
        if "gk_name" not in act or (only and act.name not in only):
            continue
        rig.animation_data.action = act
        per_bone = {}
        for fc in _fcurves(act):
            if not fc.data_path.startswith('pose.bones["'):
                continue
            bname = fc.data_path.split('"')[1]
            prop = fc.data_path.split(".")[-1]
            per_bone.setdefault(bname, {}).setdefault(prop, set()).update(round(k.co.x, 4) for k in fc.keyframe_points)
        bones_out = {}
        for bname, props in per_bone.items():
            pb = rig.pose.bones.get(bname)
            if pb is None:
                continue
            rest = list(pb.get("gk_rest_rotation", [0, 0, 0]))
            out = {}
            for prop, frames in props.items():
                keys = {}
                for fr in sorted(frames):
                    scene.frame_set(int(math.floor(fr)), subframe=fr - math.floor(fr))
                    if prop == "rotation_euler":
                        r = euler_to_file_rot(pb.rotation_euler)
                        v = [r[i] - rest[i] for i in range(3)]
                    elif prop == "location":
                        l = pb.location; v = [l.x * 16, l.z * 16, l.y * 16]
                    elif prop == "scale":
                        s = pb.scale; v = [s.x, s.z, s.y]
                    else:
                        continue
                    keys[_t(fr / fps)] = {"post": [round(x, 4) + 0.0 for x in v], "lerp_mode": "catmullrom"}
                ident = [1, 1, 1] if prop == "scale" else [0, 0, 0]
                if all(all(abs(a - b) < 1e-4 for a, b in zip(k["post"], ident)) for k in keys.values()):
                    continue                                    # nothing but the rest pose: leave the channel out
                out[{"rotation_euler": "rotation", "location": "position", "scale": "scale"}[prop]] = keys
            if out:
                bones_out[bname] = out
        entry = {"animation_length": round(float(act.get("gk_length", act.frame_range[1] / fps)), 4), "bones": bones_out}
        loop = json.loads(act.get("gk_loop", "false"))
        if loop not in (False, None):
            entry["loop"] = loop
        data["animations"][act["gk_name"]] = _ordered(entry)
        print("EXPORTED", act["gk_name"], len(bones_out), "bones")
    json.dump(data, open(anim_path, "w"), indent=1)
    print("EXPORT_OK", anim_path)


def _t(sec):
    s = f"{sec:.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"


def _ordered(e):
    o = {"animation_length": e["animation_length"]}
    if "loop" in e:
        o["loop"] = e["loop"]
    o["bones"] = e["bones"]
    return o


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "import":
        import_model(*args[1:5])
    elif args[0] == "export":
        export_animations(args[1], args[2].split(",") if len(args) > 2 else None)
