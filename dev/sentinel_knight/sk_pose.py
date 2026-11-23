"""Posing toolkit for the Withered Sentinel knight rig (Sentinel_Rig in sentinel_knight.blend).
World = armature space (rig at the origin). Front = -Y, his LEFT = +X, up = +Z. Helpers take pixels (16 px = 1 m).

Main entry: pose(r, P) poses the whole body from a parameter dict (see DEFAULT) - pelvis/spine/chest/head,
planted feet via leg IK, the sword gripped by the right hand (and the left hand on the handle when two-handed)
via arm IK, or a free left arm, finger curl, and the heart pulse."""
import bpy, math
from mathutils import Matrix, Vector, Quaternion, Euler

PX = 1 / 16.0
FPS = 20


def V(*a):
    return Vector(a[0] if len(a) == 1 else a)


class Rig:
    def __init__(self):
        self.ob = bpy.data.objects["Sentinel_Rig"]
        self.pb = self.ob.pose.bones
        self.scene = bpy.context.scene
        self.rest_pose()
        self.base = {p.name: p.matrix.to_3x3().copy() for p in self.pb}
        self.head0 = {p.name: p.matrix.translation.copy() for p in self.pb}
        self.len = {p.name: (p.tail - p.head).length for p in self.pb}
        sc = self.scene
        self.grip0 = Vector(sc["sk_grip"]) * PX
        self.grip_l_s = sc["sk_grip_l_s"] * PX
        self.sword_len = sc["sk_sword_len"] * PX

    def upd(self):
        bpy.context.view_layer.update()

    def rest_pose(self):
        for p in self.pb:
            p.rotation_mode = "QUATERNION"; p.rotation_quaternion = (1, 0, 0, 0)
            p.location = (0, 0, 0); p.scale = (1, 1, 1)
        self.upd()

    def head(self, b):
        return self.pb[b].head.copy()

    def tail(self, b):
        return self.pb[b].tail.copy()

    def rot(self, b):
        return self.pb[b].matrix.to_3x3()

    def rotate(self, b, R):
        """Rotate bone b (and its children) by world rotation R about its head."""
        p = self.pb[b]; h = p.matrix.translation.copy()
        M = (R.to_matrix() if isinstance(R, Quaternion) else R).to_4x4()
        p.matrix = Matrix.Translation(h) @ M @ Matrix.Translation(-h) @ p.matrix
        self.upd()

    def set_world_rot(self, b, R3):
        p = self.pb[b]; h = p.matrix.translation.copy()
        p.matrix = Matrix.Translation(h) @ R3.to_4x4()
        self.upd()

    def move(self, b, v_px):
        p = self.pb[b]; M = p.matrix.copy(); M.translation += Vector(v_px) * PX
        p.matrix = M; self.upd()

    def aim(self, b, d, blend=1.0):
        cur = (self.tail(b) - self.head(b)).normalized()
        q = cur.rotation_difference(Vector(d).normalized())
        if blend < 1:
            q = Quaternion().slerp(q, blend)
        self.rotate(b, q)

    def scale(self, b, s):
        self.pb[b].scale = (s, s, s); self.upd()

    def ik(self, upper, lower, target, pole):
        """End of lower bone at world target (metres), knee/elbow bent toward pole direction."""
        A = self.head(upper)
        l1, l2 = self.len[upper], self.len[lower]
        T = Vector(target); D = T - A
        d = min(max(D.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
        u = D.normalized()
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, l1 * l1 - a * a))
        pv = Vector(pole); v = pv - u * pv.dot(u)
        v = v.normalized() if v.length > 1e-6 else Vector((0, -1, 0))
        knee = A + u * a + v * h
        self.aim(upper, knee - A)
        self.aim(lower, (A + u * d) - self.head(lower))
        return knee


# ---------------------------------------------------------------- curves
def clamp01(t):
    return max(0.0, min(1.0, t))


def smooth(t):
    t = clamp01(t); return t * t * (3 - 2 * t)


def ease_in(t):
    t = clamp01(t); return t * t


def ease_out(t):
    t = clamp01(t); return 1 - (1 - t) * (1 - t)


def _lerp(a, b, w):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


def _catmull(p0, p1, p2, p3, t):
    if isinstance(p1, (tuple, list)):
        return tuple(_catmull(a, b, c, d, t) for a, b, c, d in zip(p0, p1, p2, p3))
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def track(keys, f):
    """(frame, value[, easing]) keys; easing of a key applies to the segment after it: s smooth, i in, o out, l linear, c catmull."""
    if f <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0[0] <= f <= k1[0]:
            t = (f - k0[0]) / (k1[0] - k0[0]) if k1[0] > k0[0] else 1.0
            e = k0[2] if len(k0) > 2 else "s"
            if e == "c":
                p0 = keys[i - 1][1] if i > 0 else k0[1]
                p3 = keys[i + 2][1] if i + 2 < len(keys) else k1[1]
                return _catmull(p0, k0[1], k1[1], p3, t)
            w = {"s": smooth, "i": ease_in, "o": ease_out, "l": lambda x: x}[e](t)
            return _lerp(k0[1], k1[1], w)
    return keys[-1][1]


def wave(f, n, *terms):
    """Sum of sines with whole harmonics over n frames (seamless loops): (amp, harmonic, phase)."""
    return sum(a * math.sin(2 * math.pi * h * f / n + p) for a, h, p in terms)


def bump(x, c, w):
    d = (x - c) / w
    return math.exp(-d * d)


def eul(x=0, y=0, z=0):
    return Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_matrix()


def dir_az_el(az, el):
    """Azimuth 0 = straight ahead (-Y), + = toward his LEFT (+X); elevation + = up. Degrees."""
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def heartbeat(t_sec, bpm, amp=1.0):
    """Lub-dub: two contractions per beat; returns (heart scale, glow scale)."""
    ph = (t_sec * bpm / 60.0) % 1.0
    lub = bump(ph, 0.06, 0.045); dub = 0.62 * bump(ph, 0.24, 0.05)
    k = lub + dub
    return 1.0 + 0.22 * amp * k, 0.75 + 0.55 * amp * k


# ---------------------------------------------------------------- the whole-body pose
DEFAULT = dict(
    body=(0.0, 0.0, 0.0),            # pelvis offset (px)
    hips=(0.0, 0.0, 0.0),            # pelvis world rotation: pitch (+ = lean forward), roll (+ = his left side down), yaw (+ = turn to his left)
    spine=(0.0, 0.0, 0.0),           # extra rotation of the spine (pitch, roll, yaw) relative to the pelvis
    chest=(0.0, 0.0, 0.0),           # extra rotation of the chest relative to the spine
    head=(0.0, 0.0, 0.0),            # head WORLD look: yaw (+ left), pitch (+ down), tilt (+ toward his left shoulder)
    jaw=0.0,
    shrug_R=0.0, shrug_L=0.0,        # clavicle lift (deg)
    foot_R=((-6.0, 0.0), 0.0, 0.0, 0.0), foot_L=((6.0, 0.0), 0.0, 0.0, 0.0),   # (xy px, lift px, yaw deg, heel pitch deg)
    knee_R=(-0.25, -1.0, 0.0), knee_L=(0.25, -1.0, 0.0),
    sword=None,                      # dict(grip=(x,y,z) px world, dir=(...), flat=(...), two=True/False, two_w=0..1)
    arm_L=None,                      # free left arm: dict(hand=(x,y,z) px, palm=(dir), point=(dir fingers), elbow=(pole))
    arm_R=None,                      # free right arm (sword still attached to the hand)
    curl_R=1.0, curl_L=0.6, spread_L=0.0, thumb_L=0.5,
    heart=(1.0, 1.0),
)


def merged(**kw):
    P = dict(DEFAULT); P.update(kw); return P


def place_leg(r, S, xy, lift, yaw, pitch, pole):
    """Ankle over (x, y) px at sole height + lift; foot yawed; heel raised by pitch around the ball of the foot."""
    sole_to_ankle = 6.0
    a = Vector((xy[0], xy[1], sole_to_ankle + lift)) * PX
    Rz = Matrix.Rotation(math.radians(yaw), 3, "Z")
    if pitch > 0:
        ball = r.head0[f"toe_{S}"] - r.head0[f"foot_{S}"]                     # rest vector ankle -> ball
        ball_w = a + Rz @ ball
        Rp = Matrix.Rotation(math.radians(pitch), 3, Rz @ Vector((1, 0, 0)))
        a = ball_w - Rp @ (Rz @ ball)
    r.ik(f"thigh_{S}", f"shin_{S}", a, Vector(pole))
    R = Rz @ r.base[f"foot_{S}"]
    if pitch:
        R = Matrix.Rotation(math.radians(pitch), 3, Rz @ Vector((1, 0, 0))) @ R
    r.set_world_rot(f"foot_{S}", R)
    if pitch > 0:                                                               # toes stay flat on the floor
        r.set_world_rot(f"toe_{S}", Rz @ r.base[f"toe_{S}"])
    elif pitch < 0:
        r.rotate(f"toe_{S}", Matrix.Rotation(math.radians(-pitch * 0.4), 3, Rz @ Vector((1, 0, 0))))


def sword_frame(d, n):
    d = Vector(d).normalized(); n = Vector(n); n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed()


S_REST = sword_frame((0, -1, 0), (0, 0, 1))


def hold_sword(r, grip_px, d, n, two=True, two_w=1.0, elbow_R=(-0.7, 0.6, -0.3), elbow_L=(0.6, 0.6, -0.4)):
    """Right fist on the grip (sword follows rigidly); optionally the left fist lower on the handle."""
    Rs = sword_frame(d, n) @ S_REST.inverted()                                 # world rotation applied to the sword
    G = Vector(grip_px) * PX
    v0 = r.grip0 - r.head0["hand_R"]
    hand_R = G - Rs @ v0
    r.ik("upperarm_R", "forearm_R", hand_R, Vector(elbow_R))
    r.set_world_rot("hand_R", Rs @ r.base["hand_R"])
    if two and two_w > 0:
        dd = Vector(d).normalized()
        GL = G + dd * r.grip_l_s
        hand_L = GL - Rs @ v0
        free = r.head("hand_L")
        target = free.lerp(hand_L, two_w) if two_w < 1 else hand_L
        r.ik("upperarm_L", "forearm_L", target, Vector(elbow_L))
        cur = r.rot("hand_L"); want = Rs @ r.base["hand_L"]
        r.set_world_rot("hand_L", cur.to_quaternion().slerp(want.to_quaternion(), two_w).to_matrix())


def free_arm(r, S, hand_px, point, palm, elbow):
    """Free arm: wrist at hand_px, fingers pointing along `point`, palm facing `palm`."""
    r.ik(f"upperarm_{S}", f"forearm_{S}", Vector(hand_px) * PX, Vector(elbow))
    p = Vector(point).normalized(); n = Vector(palm); n = (n - p * n.dot(p)).normalized()
    # rest hand: fingers -Z, palm +X for the right hand / -X for the left hand
    rest_palm = Vector((1, 0, 0)) if S == "R" else Vector((-1, 0, 0))
    B0 = Matrix((Vector((0, 0, -1)), rest_palm, Vector((0, 0, -1)).cross(rest_palm))).transposed()
    B = Matrix((p, n, p.cross(n))).transposed()
    r.set_world_rot(f"hand_{S}", B @ B0.inverted() @ r.base[f"hand_{S}"])


def fingers(r, S, curl, spread=0.0, thumb=0.5, wobble=(0.0, 0.0, 0.0)):
    """Curl each finger (0 = straight, 1 = fist around a grip); spread fans them; wobble = per-finger offsets."""
    hand = r.rot(f"hand_{S}") @ r.base[f"hand_{S}"].inverted()
    axis = hand @ Vector((0, 1 if S == "R" else -1, 0))                     # curl toward the palm
    fan = hand @ Vector((1 if S == "R" else -1, 0, 0))
    for i, fi in enumerate(("index", "middle", "ring")):
        c = max(-0.2, curl + wobble[i])
        r.rotate(f"{fi}1_{S}", Matrix.Rotation(math.radians(80 * c), 3, axis) @ Matrix.Rotation(math.radians((i - 1) * 12 * spread), 3, fan))
        r.rotate(f"{fi}2_{S}", Matrix.Rotation(math.radians(75 * c), 3, axis))
    r.rotate(f"thumb1_{S}", Matrix.Rotation(math.radians(55 * thumb), 3, axis))
    r.rotate(f"thumb2_{S}", Matrix.Rotation(math.radians(45 * thumb), 3, axis))


def head_look(r, yaw, pitch, tilt):
    R = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X") @ Matrix.Rotation(math.radians(tilt), 3, "Y")
    # neck takes ~40% of the turn, the head the rest (keeps it from looking bolted on)
    Rn = Matrix.Rotation(math.radians(yaw * 0.4), 3, "Z") @ Matrix.Rotation(math.radians(pitch * 0.35), 3, "X")
    r.set_world_rot("neck", Rn @ r.base["neck"])
    r.set_world_rot("head", R @ r.base["head"])


def pose(r, P):
    r.rest_pose()
    bx, by, bz = P["body"]
    r.move("pelvis", (bx, by, bz))
    pitch, roll, yaw = P["hips"]
    r.rotate("pelvis", Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X") @ Matrix.Rotation(math.radians(roll), 3, "Y"))
    for b in ("spine", "chest"):
        p_, r_, y_ = P[b]
        R = r.rot(b) @ r.base[b].inverted()
        r.rotate(b, R @ (Matrix.Rotation(math.radians(y_), 3, "Z") @ Matrix.Rotation(math.radians(p_), 3, "X") @ Matrix.Rotation(math.radians(r_), 3, "Y")) @ R.inverted())
    for S, sg in (("R", -1), ("L", 1)):
        sh = P[f"shrug_{S}"]
        if sh:
            r.rotate(f"clavicle_{S}", Matrix.Rotation(math.radians(sh * -sg), 3, r.rot("chest") @ r.base["chest"].inverted() @ Vector((0, 1, 0))))
    for S in ("R", "L"):
        xy, lift, yaw_f, pit = P[f"foot_{S}"]
        place_leg(r, S, xy, lift, yaw_f, pit, P[f"knee_{S}"])
    head_look(r, *P["head"])
    sw = P["sword"]
    if P["arm_R"]:
        a = P["arm_R"]; free_arm(r, "R", a["hand"], a["point"], a["palm"], a["elbow"])
    elif sw:
        hold_sword(r, sw["grip"], sw["dir"], sw["flat"], sw.get("two", False) and not P["arm_L"], sw.get("two_w", 1.0),
                   sw.get("elbow_R", (-0.7, 0.6, -0.3)), sw.get("elbow_L", (0.6, 0.6, -0.4)))
    if P["arm_L"]:
        a = P["arm_L"]; free_arm(r, "L", a["hand"], a["point"], a["palm"], a["elbow"])
    fingers(r, "R", P["curl_R"], P.get("spread_R", 0.0), P.get("thumb_R", 0.5))
    fingers(r, "L", P["curl_L"], P["spread_L"], P["thumb_L"], P.get("wobble_L", (0, 0, 0)))
    sw_w = P.get("sword_world")
    if sw_w:                                       # sword released: placed in the world (e.g. dropped in death)
        g, d, n, w = sw_w
        if w > 0:
            Rs = sword_frame(d, n) @ S_REST.inverted()
            want = Matrix.Translation(Vector(g) * PX) @ (Rs @ r.base["sword"]).to_4x4()
            cur = r.pb["sword"].matrix.copy()
            if w < 1:
                loc = cur.translation.lerp(want.translation, w)
                q = cur.to_quaternion().slerp(want.to_quaternion(), w)
                want = Matrix.Translation(loc) @ q.to_matrix().to_4x4()
            r.pb["sword"].matrix = want; r.upd()
    hs, gs = P["heart"]
    r.scale("heart", hs); r.scale("heart_glow", gs / max(hs, 1e-3))


# ---------------------------------------------------------------- baking
def bake(r, name, n, fn, loop="false"):
    """Per-frame bake of fn(r, f) (which calls pose) into action `name` (quaternion keys, linear)."""
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    r.ob.animation_data_create(); r.ob.animation_data.action = act
    prev = {}
    for f in range(0, n + 1):
        fn(r, f)
        for p in r.pb:
            q = p.rotation_quaternion.copy()
            if p.name in prev and prev[p.name].dot(q) < 0:
                q.negate(); p.rotation_quaternion = q
            prev[p.name] = q.copy()
            p.keyframe_insert("rotation_quaternion", frame=f, group=p.name)
            p.keyframe_insert("location", frame=f, group=p.name)
            p.keyframe_insert("scale", frame=f, group=p.name)
    fcs = act.fcurves if hasattr(act, "fcurves") else [fc for l_ in act.layers for st in l_.strips for b in st.channelbags for fc in b.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    act.frame_range = (0, n)
    act["sk_export"] = True; act["sk_loop"] = loop
    return act
