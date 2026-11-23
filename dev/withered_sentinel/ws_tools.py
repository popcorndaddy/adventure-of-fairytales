"""Posing toolkit for the Withered Sentinel rig (Blender side of the GeckoLib bridge).
Bones are axis-aligned at their GeckoLib pivots; pose rotation mode XZY = GeckoLib rest + animation.
World: front = -Y, his right = -X, up = +Z. Units: Blender metres; helpers take pixels where noted (16 px = 1 m)."""
import bpy, math
from mathutils import Matrix, Vector, Quaternion, Euler

PX = 1 / 16.0
FPS = 20


class Rig:
    def __init__(self):
        self.ob = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        self.mesh = next(o for o in bpy.data.objects if o.type == "MESH")
        self.pb = self.ob.pose.bones
        self.rest_eul = {p.name: Euler(tuple(math.radians(v) for v in (p["gk_rest_rotation"][0], p["gk_rest_rotation"][2], -p["gk_rest_rotation"][1])), "XZY")
                         for p in self.pb}
        self.vg = {}
        for g in self.mesh.vertex_groups:
            self.vg[g.name] = [self.mesh.matrix_world @ v.co for v in self.mesh.data.vertices
                               if any(x.group == g.index and x.weight > 0.5 for x in v.groups)]
        self.rest_pose()
        # segment reference points (bone-local, measured in the rest pose)
        self.seg_pt = {}
        for parent, child in (("right_arm", "right_forearm"), ("right_forearm", "right_hand"), ("left_arm", "left_forearm"),
                              ("left_forearm", "left_hand"), ("right_leg", "right_shin"), ("right_shin", "right_foot"),
                              ("left_leg", "left_shin"), ("left_shin", "left_foot")):
            self.seg_pt[parent] = self.ob.data.bones[child].head_local.copy()
        for h in ("right_hand", "left_hand"):
            pts = self.vg[h]; self.seg_pt[h] = sum(pts, Vector()) / len(pts)
        sh = self.ob.data.bones["sword"].head_local
        self.seg_pt["sword"] = max(self.vg["sword"], key=lambda p: (p - sh).length)
        self.base_rot = {p.name: p.matrix.to_3x3().copy() for p in self.pb}       # rest-pose world rotations
        self.lengths = {k: (self.seg_pt[k] - self.ob.data.bones[k].head_local).length for k in self.seg_pt}
        # foot toe / sole reference (rest pose, world)
        self.toe = {}; self.ankle_rest = {}
        for S in ("right", "left"):
            pts = [self.world_pt(f"{S}_foot", p) for p in self.vg[f"{S}_foot"]]
            zmin = min(p.z for p in pts)
            sole = [p for p in pts if p.z < zmin + 0.02]
            self.toe[S] = min(sole, key=lambda p: p.y)                      # front-most sole point
            self.ankle_rest[S] = self.head(f"{S}_foot")
        self.ground = min(min(self.world_pt(f"{S}_foot", p).z for p in self.vg[f"{S}_foot"]) for S in ("right", "left"))

    # ----------------------------------------------------------- basics
    def upd(self):
        bpy.context.view_layer.update()

    def rest_pose(self):
        for p in self.pb:
            p.rotation_mode = "XZY"
            p.rotation_euler = self.rest_eul[p.name].copy() if hasattr(self, "rest_eul") else p.rotation_euler
            p.location = (0, 0, 0); p.scale = (1, 1, 1)
        self.upd()

    def head(self, b):
        return self.pb[b].matrix.translation.copy()

    def world_pt(self, b, rest_pt):
        p = self.pb[b]
        return p.matrix @ p.bone.matrix_local.inverted() @ rest_pt

    def seg(self, b):
        return self.world_pt(b, self.seg_pt[b]) - self.head(b)

    def rotate(self, b, R):
        """World rotation about the bone's head."""
        p = self.pb[b]; h = p.matrix.translation.copy()
        M = (R.to_matrix() if isinstance(R, Quaternion) else R).to_4x4()
        p.matrix = Matrix.Translation(h) @ M @ Matrix.Translation(-h) @ p.matrix
        self.upd()

    def set_world_rot(self, b, R3):
        p = self.pb[b]; h = p.matrix.translation.copy()
        p.matrix = Matrix.Translation(h) @ R3.to_4x4()
        self.upd()

    def move(self, b, v_px):
        """Translate a bone (and everything under it) by a world offset in pixels."""
        p = self.pb[b]
        M = p.matrix.copy(); M.translation += Vector(v_px) * PX
        p.matrix = M; self.upd()

    def aim(self, b, d, blend=1.0):
        q = self.seg(b).normalized().rotation_difference(Vector(d).normalized())
        if blend < 1:
            q = Quaternion().slerp(q, blend)
        self.rotate(b, q)

    def orient(self, b, d, side_hint):
        """Point the bone's segment along d, and turn it so its rest 'side' axis (local X of the rest pose)
        faces side_hint as closely as possible."""
        self.aim(b, d)
        d = Vector(d).normalized()
        side_now = (self.pb[b].matrix.to_3x3() @ (self.base_rot[b].inverted() @ Vector((1, 0, 0))))
        want = Vector(side_hint); want = (want - d * want.dot(d))
        cur = side_now - d * side_now.dot(d)
        if want.length > 1e-4 and cur.length > 1e-4:
            ang = cur.normalized().angle(want.normalized())
            if cur.normalized().cross(want.normalized()).dot(d) < 0:
                ang = -ang
            self.rotate(b, Matrix.Rotation(ang, 3, d))

    # ----------------------------------------------------------- two-bone IK
    def ik(self, upper, lower, target, pole):
        """Place the end of upper->lower (lower's segment end) at world `target`, bending toward `pole`."""
        A = self.head(upper)
        l1, l2 = self.lengths[upper], self.lengths[lower]
        T = Vector(target); D = T - A
        d = min(max(D.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
        u = D.normalized()
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, l1 * l1 - a * a))
        pv = Vector(pole); v = (pv - u * pv.dot(u))
        v = v.normalized() if v.length > 1e-6 else Vector((0, -1, 0))
        knee = A + u * a + v * h
        n = (knee - A).cross(T - knee)
        self.aim(upper, knee - A)
        self.aim(lower, (A + u * d) - self.head(lower))
        return knee

    # ----------------------------------------------------------- feet
    def place_foot(self, S, ankle_px, pitch=0.0, yaw=0.0):
        """Ankle at a pixel position (world), foot kept in its authored flat orientation, pitched (+ = heel up)."""
        self.ik(f"{S}_leg", f"{S}_shin", Vector(ankle_px) * PX, pole=Vector((0.12 if S == "left" else -0.12, -1, 0)))
        R = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X") @ self.base_rot[f"{S}_foot"]
        self.set_world_rot(f"{S}_foot", R)

    def ankle_for_toe(self, S, toe_px, pitch):
        """Ankle position that keeps the toe tip at toe_px while the heel lifts by `pitch` degrees."""
        ankle0 = self.ankle_rest[S]
        rel = ankle0 - self.toe[S]
        R = Matrix.Rotation(math.radians(pitch), 3, "X")
        return Vector(toe_px) + (R @ rel) / PX

    def sole_points(self, S):
        return [self.world_pt(f"{S}_foot", p) for p in self.vg[f"{S}_foot"]]

    def sword_tip(self):
        return self.world_pt("sword", self.seg_pt["sword"])

    def min_z(self, bone):
        return min(self.world_pt(bone, p).z for p in self.vg[bone])


# ----------------------------------------------------------------- curves
def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def ease_in(t):
    t = max(0.0, min(1.0, t)); return t * t


def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) * (1 - t)


def track(keys, f, mode=None):
    """Piecewise interpolation through (frame, value[, easing]) keys; value may be float or tuple.
    The easing on a key applies to the segment that starts at it ('s' smooth, 'i' in, 'o' out, 'l' linear, 'c' catmull)."""
    if f <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0[0] <= f <= k1[0]:
            t = (f - k0[0]) / (k1[0] - k0[0])
            e = k0[2] if len(k0) > 2 else "s"
            if e == "c":
                p0 = keys[i - 1][1] if i > 0 else k0[1]
                p3 = keys[i + 2][1] if i + 2 < len(keys) else k1[1]
                return _catmull(p0, k0[1], k1[1], p3, t)
            w = {"s": smooth, "i": ease_in, "o": ease_out, "l": lambda x: x}[e](t)
            return _lerp(k0[1], k1[1], w)
    return keys[-1][1]


def _lerp(a, b, w):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


def _catmull(p0, p1, p2, p3, t):
    if isinstance(p1, (tuple, list)):
        return tuple(_catmull(a, b, c, d, t) for a, b, c, d in zip(p0, p1, p2, p3))
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def eul(x=0, y=0, z=0):
    return Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_matrix()


def dir_az_el(az, el):
    """Horizontal azimuth (0 = straight ahead, + = toward his LEFT (+X)) and elevation (+ = up), degrees."""
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


# ----------------------------------------------------------------- baking into actions
def fcurve_bags(act):
    try:
        return [act.fcurves]
    except AttributeError:
        return [bag.fcurves for layer in act.layers for strip in layer.strips for bag in strip.channelbags]


def bake(rig, name, length_frames, pose_fn, loop=False, gk_name=None):
    """Replace action `name` with a per-frame bake of pose_fn(rig, frame) (which poses from rest each frame)."""
    old = bpy.data.actions.get(name)
    props = {k: old[k] for k in ("gk_name", "gk_length", "gk_loop") if old and k in old}
    act = bpy.data.actions.new(name + "__new"); act.use_fake_user = True
    rig.ob.animation_data_create(); rig.ob.animation_data.action = act
    prev = {}
    for f in range(0, length_frames + 1):
        rig.rest_pose()
        pose_fn(rig, f)
        for p in rig.pb:
            e = p.rotation_euler.copy()
            if p.name in prev:
                e.make_compatible(prev[p.name])
            p.rotation_euler = e; prev[p.name] = e.copy()
            p.keyframe_insert("rotation_euler", frame=f, group=p.name)
            p.keyframe_insert("location", frame=f, group=p.name)
            p.keyframe_insert("scale", frame=f, group=p.name)
    for fcs in fcurve_bags(act):
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    if old:
        old.use_fake_user = False; old.name = name + "__old"
        bpy.data.actions.remove(old)
    act.name = name
    act["gk_name"] = props.get("gk_name", gk_name or f"animation.withered_sentinel.{name}")
    act["gk_length"] = length_frames / FPS
    act["gk_loop"] = "true" if loop is True else (props.get("gk_loop", "false") if loop is None else ('"%s"' % loop if isinstance(loop, str) else "false"))
    act.frame_range = (0, length_frames)
    return act
