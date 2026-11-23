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
        self.sec = {}                     # secondary-motion state (cape / tasset springs), reset per action

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


def free_target(r, S, a):
    """World wrist position, hand rotation and elbow pole for a free hand described by dict a."""
    p = Vector(a["point"]).normalized(); n = Vector(a["palm"]); n = (n - p * n.dot(p)).normalized()
    rest_palm = Vector((1, 0, 0)) if S == "R" else Vector((-1, 0, 0))
    B0 = Matrix((Vector((0, 0, -1)), rest_palm, Vector((0, 0, -1)).cross(rest_palm))).transposed()
    B = Matrix((p, n, p.cross(n))).transposed()
    return Vector(a["hand"]) * PX, B @ B0.inverted() @ r.base[f"hand_{S}"], Vector(a["elbow"])


def sword_targets(r, sw):
    """Where each fist must be (and how it is turned) to hold the sword described by sw."""
    d = Vector(sw["dir"]).normalized()
    Rs = sword_frame(d, sw["flat"]) @ S_REST.inverted()
    G = Vector(sw["grip"]) * PX
    v0 = r.grip0 - r.head0["hand_R"]
    R_t = (G - Rs @ v0, Rs @ r.base["hand_R"], Vector(sw.get("elbow_R", (-0.7, 0.6, -0.3))))
    GL = G + d * r.grip_l_s
    L_t = (GL - Rs @ v0, Rs @ r.base["hand_L"], Vector(sw.get("elbow_L", (0.6, 0.6, -0.4))))
    return R_t, L_t


def place_hand(r, S, pos, R3, pole):
    r.ik(f"upperarm_{S}", f"forearm_{S}", pos, pole)
    r.set_world_rot(f"hand_{S}", R3)


def blend_target(a, b, w):
    """Blend two (pos, rot, pole) hand targets: w = 0 -> a, 1 -> b."""
    if w <= 0:
        return a
    if w >= 1:
        return b
    q = a[1].to_quaternion().slerp(b[1].to_quaternion(), w)
    return a[0].lerp(b[0], w), q.to_matrix(), a[2].lerp(b[2], w)


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
    axis = hand @ Vector((0, -1 if S == "R" else 1, 0))                     # curl toward the palm (+X right / -X left at rest)
    fan = hand @ Vector((1 if S == "R" else -1, 0, 0))
    for i, fi in enumerate(("index", "middle", "ring")):
        c = max(-0.2, curl + wobble[i])
        r.rotate(f"{fi}1_{S}", Matrix.Rotation(math.radians(92 * c), 3, axis) @ Matrix.Rotation(math.radians((i - 1) * 12 * spread), 3, fan))
        r.rotate(f"{fi}2_{S}", Matrix.Rotation(math.radians(100 * c), 3, axis))
    r.rotate(f"thumb1_{S}", Matrix.Rotation(math.radians(62 * thumb), 3, axis))
    r.rotate(f"thumb2_{S}", Matrix.Rotation(math.radians(60 * thumb), 3, axis))


def head_look(r, yaw, pitch, tilt):
    R = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X") @ Matrix.Rotation(math.radians(tilt), 3, "Y")
    # neck takes ~40% of the turn, the head the rest (keeps it from looking bolted on)
    Rn = Matrix.Rotation(math.radians(yaw * 0.4), 3, "Z") @ Matrix.Rotation(math.radians(pitch * 0.35), 3, "X")
    r.set_world_rot("neck", Rn @ r.base["neck"])
    r.set_world_rot("head", R @ r.base["head"])


HEAD_LOOK_PITCH = 9.0          # he looks slightly down: at a player standing in front of a 4.5-block knight
NECK_SOFT, NECK_MAX = 45.0, 65.0


def calm_head(r, P):
    """The head stays on the target (the entity always faces it) with only a few degrees of drift, follows the body
    through a soft spring, and never twists more than ~65 deg from the chest. head_mode: 'calm' (default),
    'pitch' (keeps the authored nod/tilt, calms the turning: kneeling, collapse), 'free' (as authored)."""
    hy, hp, ht = P["head"]
    mode = P.get("head_mode", "calm")
    if mode == "free":
        return hy, hp, ht
    hy = 0.12 * hy
    if mode == "calm":
        hp = HEAD_LOOK_PITCH + 0.25 * (hp - HEAD_LOOK_PITCH); ht = 0.25 * ht
    hy = _spring(r.sec, "head_y", hy, 0.3, 0.45)
    hp = _spring(r.sec, "head_p", hp, 0.3, 0.45)
    ht = _spring(r.sec, "head_t", ht, 0.3, 0.45)
    cy = P["hips"][2] + P["spine"][2] + P["chest"][2]           # where the chest points (world yaw)
    rel = hy - cy
    a = abs(rel)
    if a > NECK_SOFT:                                            # soft limit: the neck gives way to the shoulders
        rel = math.copysign(NECK_SOFT + (NECK_MAX - NECK_SOFT) * math.tanh((a - NECK_SOFT) / (NECK_MAX - NECK_SOFT)), rel)
    return cy + rel, hp, ht


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
        y0 = P.get(f"pivot_{S}")
        if y0 is not None and yaw_f != y0:                       # turn about the ball of the foot, not the ankle
            b0 = (r.head0[f"toe_{S}"] - r.head0[f"foot_{S}"]) / PX; b0.z = 0
            d = Matrix.Rotation(math.radians(y0), 3, "Z") @ b0 - Matrix.Rotation(math.radians(yaw_f), 3, "Z") @ b0
            xy = (xy[0] + d.x, xy[1] + d.y)
        place_leg(r, S, xy, lift, yaw_f, pit, P[f"knee_{S}"])
    head_look(r, *calm_head(r, P))
    sw = P["sword"]
    # Each hand is a blend of "on the sword" and "free" (arm_R_w / arm_L_w, 0..1), so a hand never jumps between
    # the two in one tick. Without a weight, a given free arm wins outright (the old behaviour).
    wR = P.get("arm_R_w", 1.0) if P["arm_R"] else 0.0
    wL = P.get("arm_L_w", 1.0) if P["arm_L"] else 0.0
    tR = tL = None
    if sw:
        tR, tL = sword_targets(r, sw)
    if P["arm_R"] or tR:
        fR = free_target(r, "R", P["arm_R"]) if P["arm_R"] else None
        place_hand(r, "R", *(blend_target(tR, fR, wR) if (tR and fR) else (fR or tR)))
    on_L = (sw.get("two_w", 1.0) if (sw and sw.get("two", False)) else 0.0) * (1.0 - wL)
    if P["arm_L"]:
        fL = free_target(r, "L", P["arm_L"])
        place_hand(r, "L", *(blend_target(fL, tL, on_L) if tL else fL))
    elif tL and on_L > 0:
        cur = (r.head("hand_L"), r.rot("hand_L"), tL[2])
        place_hand(r, "L", *blend_target(cur, tL, on_L))
    cl, sp, th = P["curl_L"], P["spread_L"], P["thumb_L"]
    if P["arm_L"] and on_L > 0:                                  # fingers close round the handle as the hand arrives
        cl = cl + (1.0 - cl) * on_L; sp = sp * (1 - on_L); th = th + (0.9 - th) * on_L
    cr = P["curl_R"]
    if P["arm_R"] and sw and wR < 1:
        cr = cr + (1.0 - cr) * (1 - wR)
    fingers(r, "R", cr, P.get("spread_R", 0.0), P.get("thumb_R", 0.5))
    fingers(r, "L", cl, sp, th, P.get("wobble_L", (0, 0, 0)))
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
    secondary(r, P)


# ---------------------------------------------------------------- secondary motion: cape + tassets
LEG_BONES = [f"{b}_{S}" for S in ("R", "L") for b in ("thigh", "shin", "foot", "toe")]


def _leg_points(r):
    pts = []
    for b in LEG_BONES:
        for p in (r.pb[b].head, r.pb[b].tail, (r.pb[b].head + r.pb[b].tail) / 2):
            pts.append(p / PX)
    return pts


def _spring(st, key, target, k=0.22, c=0.62):
    """Under-damped spring per frame: the value overshoots a little and settles (follow-through)."""
    x, v = st.get(key, (target, 0.0))
    v = v * c + (target - x) * k
    x = x + v
    st[key] = (x, v)
    return x


def secondary(r, P):
    st = r.sec
    pel = r.head("pelvis") / PX
    prev = st.get("pelvis", pel)
    vel = pel - prev                                             # px per frame of the body itself
    st["pelvis"] = pel
    move = P.get("move", 0.0)                                    # forward speed of the entity (walk / dash), px per frame
    fwd = (-vel.y) + move
    chest_R = r.rot("chest") @ r.base["chest"].inverted()
    chest_right = chest_R @ Vector((1, 0, 0))                   # stays level when he bends forward (the forward axis does not)
    yaw = math.degrees(math.atan2(chest_right.y, chest_right.x))
    yaw_lag = _spring(st, "yaw", yaw, 0.12, 0.7)
    flutter = P.get("cape_flutter", 0.0)
    legs = _leg_points(r)
    lie = P.get("cape_on_legs", 0.0)
    if lie > 0:                                                  # down the back: from the shoulders to the hips, just off the armour
        spine_down = (r.head("pelvis") - r.tail("chest")).normalized()
        back_out = chest_R @ Vector((0, 1, 0))
        along_back = (spine_down + back_out * 0.25).normalized()
    # ---- cape: three panels, three segments. Angles are measured in HIS turning frame (behind his back, not behind
    # the world), trailing his turns a little; springs give follow-through; never inside his legs.
    for s, side in (("L", 1), ("M", 0), ("R", -1)):
        prev_angle = 0.0
        for k in (1, 2, 3):
            b = f"cape_{s}{k}"
            yaw_k = yaw + (yaw_lag - yaw) * (0.35 + 0.2 * k)          # lower segments trail the turn more
            Rk = Matrix.Rotation(math.radians(yaw_k), 3, "Z"); Rki = Rk.transposed()
            A = Rki @ (r.head(b) / PX)
            L = r.len[b] / PX
            base = 7.0 + 3.0 * (k - 1)
            target = base + min(48.0, 9.0 * max(0.0, fwd) * (0.8 + 0.25 * k)) - 3.0 * vel.z * k
            target += 0.18 * abs(yaw - yaw_lag) * k                     # flares out behind a fast turn
            target += flutter * math.sin(P.get("t", 0) * (1.3 + 0.4 * k) + side) * k
            th = _spring(st, b, max(prev_angle - 4.0, target), 0.20 - 0.03 * k, 0.66)
            # clearance from the legs (in his frame): the segment's end must stay behind every leg point at its height
            need = -1e9
            free = P.get("cape_on_legs", 0.0) > 0.5                # collapsed: the cape lies down his back, then falls free
            for q0 in ([] if free else legs):
                q = Rki @ q0
                if A.z - L - 6 <= q.z <= A.z + 2 and abs(q.x - A.x) < 10.0:
                    need = max(need, q.y + 5.0)
            if need > -1e9:
                ratio = (need - A.y) / L
                if ratio > -1.0:
                    th_min = math.degrees(math.asin(max(-1.0, min(1.0, ratio))))
                    if th < th_min:
                        th = th_min; st[b] = (th, 0.0)
            if A.z - L * math.cos(math.radians(th)) < 0.6 and A.z - 0.6 < L:    # never through the floor: it pools
                th = max(th, math.degrees(math.acos(max(-1.0, min(1.0, (A.z - 0.6) / L))))); st[b] = (th, 0.0)
            last = st.get(b + "_out")
            if last is not None and abs(th - last) > 20.0:             # pushed by a fast leg: give way over a few ticks
                th = last + math.copysign(20.0, th - last); st[b] = (th, 0.0)
            st[b + "_out"] = th
            sway = side * (1.5 + 0.8 * k)
            d = Vector((math.sin(math.radians(sway)), math.sin(math.radians(th)), -math.cos(math.radians(th))))
            wd = Rk @ d
            if lie > 0 and k == 1:
                wd = wd.lerp(along_back, lie).normalized()
            r.aim(b, wd)
            prev_angle = th
    # ---- tassets follow the thigh that moves into them
    down = Vector((0, 0, -1))
    th_dirs = {S: (r.tail(f"thigh_{S}") - r.head(f"thigh_{S}")).normalized() for S in ("R", "L")}
    front = min(th_dirs.values(), key=lambda d: d.y)
    back = max(th_dirs.values(), key=lambda d: d.y)
    pel_R = r.rot("pelvis") @ r.base["pelvis"].inverted()
    pdown = pel_R @ down
    r.aim("tasset_F", (pdown * 0.3 + front * 0.7).normalized() + Vector((0, -0.12, 0)))
    r.aim("tasset_B", (pdown * 0.35 + back * 0.65).normalized() + Vector((0, 0.1, 0)))
    for S in ("R", "L"):
        out = Vector((1 if S == "L" else -1, 0, 0)) * 0.12
        r.aim(f"tasset_{S}", (pdown * 0.3 + th_dirs[S] * 0.7).normalized() + out)


# ---------------------------------------------------------------- baking
def bake(r, name, n, fn, loop="false"):
    """Per-frame bake of fn(r, f) (which calls pose) into action `name` (quaternion keys, linear)."""
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    r.ob.animation_data_create(); r.ob.animation_data.action = act
    prev = {}
    # warm the secondary-motion springs: a full pre-roll for loops (seamless), a settle on frame 0 otherwise
    r.sec = {}
    if loop == "true":
        for f in range(0, n + 1):
            fn(r, f)
    else:
        for _ in range(40):
            fn(r, 0)
        for key in list(r.sec):
            if isinstance(r.sec[key], tuple):
                r.sec[key] = (r.sec[key][0], 0.0)
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
