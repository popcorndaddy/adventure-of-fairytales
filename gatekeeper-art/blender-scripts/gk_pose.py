"""Pose system for the Gatekeeper: a pose is a dict (body-frame directions for arm chains, world-frame deltas
for the spine, absolute ankle targets for the 2-bone leg solver). apply_pose() builds it on the rig, key_all() keys it."""
import bpy, math, copy
from mathutils import Vector, Matrix, Quaternion
import gk_lib as L

ARM_BONES = {
    "arm": ("clavicle_{S}", "upperarm_{S}", "forearm_{S}", "hand_{S}", "finger{k}_{S}", "thumb_{S}"),
    "extra": ("clavicle_extra_{S}", "upperarm_extra_{S}", "forearm_extra_{S}", "hand_extra_{S}", "finger{k}_extra_{S}", "thumb_extra_{S}"),
}
SWORD_LEN = 87.0
BASE_FEET = {"L": (11, -2, 7), "R": (-11, 2, 7)}


def mx(v):
    return (-v[0], v[1], v[2])


def mrot(r):
    return (r[0], -r[1], -r[2])


def mirror_arm(a):
    b = dict(a)
    for k in ("upper", "fore", "hand"):
        if k in b and b[k] is not None:
            b[k] = mx(b[k])
    if "clav" in b:
        b["clav"] = mrot(b["clav"])
    return b


def stance():
    xr = {"clav": (0, 10, 0), "upper": (-0.97, -0.12, 0.2), "fore": (-0.3, -0.3, 0.9), "hand": (-0.12, -0.35, 0.93), "curl": 40, "thumb": 30}
    return {
        "root": (0, 0, 0), "root_rot": (0, 0, 0),
        "hips": {"loc": (0, 0, -1), "rot": (0, 0, 0)},
        "spine": (3, 0, 0), "chest": (3, 0, 0), "neck": (0, 0, 0), "head": (8, 0, 0),
        "robe_F": (0, 0, 0), "robe_B": (0, 0, 0), "robe_L": (0, 0, 0), "robe_R": (0, 0, 0),
        "feet": {"L": BASE_FEET["L"], "R": BASE_FEET["R"]}, "foot_pitch": {"L": 0, "R": 0},
        "extra_R": xr, "extra_L": mirror_arm(xr),
        "arm_R": {"clav": (0, 0, 0), "upper": (-0.6, -0.25, -0.76), "fore": (-0.55, -0.75, -0.35), "hand": (-0.5, -0.7, -0.5), "curl": 100, "thumb": 70},
        "arm_L": {"clav": (0, 0, 0), "upper": (0.52, -0.15, -0.84), "fore": (0.3, -0.6, -0.74), "hand": (0.25, -0.6, -0.76), "curl": 120, "thumb": 80},
        "weapon": {"dir": (-0.5, -0.25, -0.83), "normal": (0, -1, 0), "ground": "clamp"},
        "fire": {"L": 1.0, "R": 1.0},
    }


def P(**changes):
    """Stance with nested overrides: P(chest=(..), arm_R={'upper':..}) merges dicts one level deep."""
    p = copy.deepcopy(stance())
    for k, v in changes.items():
        if isinstance(v, dict) and isinstance(p.get(k), dict):
            p[k].update(v)
        else:
            p[k] = v
    return p


def _arm(rig, kind, S, spec, Rb):
    names = ARM_BONES[kind]
    s = 1 if S == "L" else -1
    L.set_delta(rig, names[0].format(S=S), spec.get("clav", (0, 0, 0)))
    for key, bn in (("upper", names[1]), ("fore", names[2]), ("hand", names[3])):
        d = spec.get(key)
        if d is None and key == "hand":
            d = spec.get("fore")
        if d is not None:
            L.aim(rig, bn.format(S=S), Rb @ Vector(d), spec.get(key + "_twist", 0.0))
    hand = names[3].format(S=S)
    hd = L.bone_dir(rig, hand)
    inward = (Rb @ Vector((-s, -0.25, 0))).normalized()
    axis = hd.cross(inward)
    if axis.length < 1e-4:
        axis = Vector((0, 1, 0))
    axis.normalize()
    curl = math.radians(spec.get("curl", 0))
    for k in (1, 2, 3):
        fd = Matrix.Rotation(curl * (0.85 + 0.1 * k), 3, axis) @ hd
        L.aim(rig, names[4].format(k=k, S=S), fd)
    td = Matrix.Rotation(math.radians(spec.get("thumb", 0)), 3, axis) @ (hd + (Rb @ Vector((0, -0.8, 0)))).normalized()
    L.aim(rig, names[5].format(S=S), td)


def sword_tip_z(rig):
    return bone_min_z(rig, "weapon")


# ---------------------------------------------------------------- ground solver
_CACHE = {}


def _cache(rig):
    if _CACHE:
        return _CACHE
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent != rig:
            continue
        me = o.data
        names = {g.index: g.name for g in o.vertex_groups}
        for i in range(0, len(me.vertices), 2):
            v = me.vertices[i]
            for g in v.groups:
                if g.weight > 0.5:
                    _CACHE.setdefault(names[g.group], []).append(o.matrix_world @ v.co)
    return _CACHE


def bone_min_z(rig, name):
    vs = _cache(rig).get(name)
    if not vs:
        return 1e9
    pb = rig.pose.bones[name]
    M = pb.matrix @ pb.bone.matrix_local.inverted()
    return min((M @ v).z for v in vs) * 16.0


def _rotate_about_head(rig, name, axis, deg, base):
    pb = rig.pose.bones[name]
    h = base.translation.copy()
    R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h)
    pb.matrix = R @ base
    bpy.context.view_layer.update()


def lift(rig, name, axis, target=0.4, max_deg=85, touch=False):
    """Rotate a bone about its head around `axis` until its lowest vertex sits at `target` px
    (only upward unless touch=True, which also lowers it onto the floor)."""
    pb = rig.pose.bones[name]
    base = pb.matrix.copy()
    if not touch and bone_min_z(rig, name) >= target:
        return
    if not touch:                      # pick the rotation direction that actually raises the part
        _rotate_about_head(rig, name, axis, 25, base); up_pos = bone_min_z(rig, name)
        _rotate_about_head(rig, name, axis, -25, base); up_neg = bone_min_z(rig, name)
        _rotate_about_head(rig, name, axis, 0, base)
        if up_neg > up_pos:
            axis = -axis
    lo, hi = (-max_deg, max_deg) if touch else (0.0, max_deg)
    for _ in range(24):
        mid = (lo + hi) / 2
        _rotate_about_head(rig, name, axis, mid, base)
        if bone_min_z(rig, name) < target:
            lo = mid
        else:
            hi = mid
    _rotate_about_head(rig, name, axis, hi, base)


def ground_fix(rig, weapon_mode):
    up = Vector((0, 0, 1)); down = Vector((0, 0, -1))
    for name, out in (("robe_F", Vector((0, -1, 0))), ("robe_B", Vector((0, 1, 0))), ("robe_L", Vector((1, 0, 0))), ("robe_R", Vector((-1, 0, 0)))):
        R = rig.pose.bones["hips"].matrix.to_3x3() @ rig.pose.bones["hips"].bone.matrix_local.to_3x3().inverted()
        lift(rig, name, (down.cross(R @ out)).normalized(), target=0.3)
    wd = L.bone_dir(rig, "weapon")
    ax = wd.cross(up)
    if ax.length > 1e-3:
        lift(rig, "weapon", ax.normalized(), target=0.6, touch=(weapon_mode == "touch"))


BODY_SKIP = ("robe_", "weapon", "foot_", "socket", "fx_", "chain_")


def fix_inbetween(rig):
    """Repair an interpolated (in-between) pose: lift robe/sword off the floor, raise the hips if the body dips.
    Returns True if anything had to change."""
    changed = False
    low_w = bone_min_z(rig, "weapon")
    low_r = min(bone_min_z(rig, b) for b in ("robe_F", "robe_B", "robe_L", "robe_R"))
    if low_w < 0.2 or low_r < 0.0:
        ground_fix(rig, "clamp"); changed = True
    deficit = -min(body_min_z(rig), min(bone_min_z(rig, f"foot_{S}") for S in ("L", "R")) + 0.0)
    if deficit > 0.4:
        pb = rig.pose.bones["hips"]
        M = pb.matrix.copy(); M.translation.z += (deficit + 0.2) / 16.0
        pb.matrix = M
        bpy.context.view_layer.update()
        ground_fix(rig, "clamp"); changed = True
    return changed


def body_min_z(rig):
    return min(bone_min_z(rig, b.name) for b in rig.pose.bones if not b.name.startswith(BODY_SKIP))


def apply_pose(rig, p, _depth=0):
    _apply(rig, p)
    deficit = -body_min_z(rig)
    if deficit > 0.3 and _depth < 3:             # something of the body is under the floor: raise the hips
        q = copy.deepcopy(p)
        h = q.setdefault("hips", {})
        lx, ly, lz = h.get("loc", (0, 0, 0))
        h["loc"] = (lx, ly, lz + deficit + 0.3)
        return apply_pose(rig, q, _depth + 1)
    ground_fix(rig, (p.get("weapon") or {}).get("ground"))
    for name, rot in (p.get("chains") or {}).items():
        pb = rig.pose.bones[name]
        base = pb.matrix.copy()
        R = Matrix.Translation(base.translation) @ __import__("mathutils").Euler(tuple(math.radians(a) for a in rot), "XYZ").to_matrix().to_4x4() @ Matrix.Translation(-base.translation)
        pb.matrix = R @ base
    bpy.context.view_layer.update()


def _apply(rig, p):
    L.reset_pose(rig)
    L.set_delta(rig, "root", p.get("root_rot", (0, 0, 0)), p.get("root", (0, 0, 0)))
    h = p.get("hips", {})
    L.set_delta(rig, "hips", h.get("rot", (0, 0, 0)), h.get("loc", (0, 0, 0)))
    for b in ("spine", "chest", "neck", "head", "robe_F", "robe_B", "robe_L", "robe_R"):
        L.set_delta(rig, b, p.get(b, (0, 0, 0)))
    for S in ("L", "R"):
        L.solve_leg(rig, S, Vector(p["feet"][S]), foot_pitch=p.get("foot_pitch", {}).get(S, 0))
    Rb = L.body_rot(rig)
    for key, kind, S in (("arm_R", "arm", "R"), ("arm_L", "arm", "L"), ("extra_R", "extra", "R"), ("extra_L", "extra", "L")):
        _arm(rig, kind, S, p[key], Rb)
    w = p.get("weapon")
    if w:
        d = (Rb @ Vector(w["dir"])).normalized()
        n = Rb @ Vector(w.get("normal", (0, -1, 0)))
        L.orient(rig, "weapon", d, n)
        mode = w.get("ground")
        if mode in ("clamp", "touch"):
            lo_target = 1.5 if mode == "touch" else 0.8
            if sword_tip_z(rig) < lo_target or mode == "touch":
                # rotate the blade up/down about the horizontal axis through the grip until the tip sits at lo_target
                up = Vector((0, 0, 1))
                ax = d.cross(up)
                if ax.length < 1e-4:
                    ax = Vector((1, 0, 0))
                ax.normalize()
                lo, hi = -80.0, 80.0
                for _ in range(30):
                    mid = (lo + hi) / 2
                    L.orient(rig, "weapon", Matrix.Rotation(math.radians(mid), 3, ax) @ d, n)
                    if sword_tip_z(rig) < lo_target:
                        lo = mid
                    else:
                        hi = mid
                L.orient(rig, "weapon", Matrix.Rotation(math.radians(hi), 3, ax) @ d, n)
    for S in ("L", "R"):
        sc = p.get("fire", {}).get(S, 1.0)
        rig.pose.bones[f"fx_fire_{S}"].scale = (sc, sc, sc)
    bpy.context.view_layer.update()


_prev = {}


def key_all(rig, frame):
    for pb in rig.pose.bones:
        q = pb.rotation_quaternion.copy()
        if pb.name in _prev and _prev[pb.name].dot(q) < 0:
            q.negate(); pb.rotation_quaternion = q
        _prev[pb.name] = q
        pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
        pb.keyframe_insert("location", frame=frame, group=pb.name)
        pb.keyframe_insert("scale", frame=frame, group=pb.name)


def reset_continuity():
    _prev.clear()
