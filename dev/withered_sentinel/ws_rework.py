"""Withered Sentinel animation rework (run on withered_sentinel.blend, saves withered_sentinel_reworked.blend).
  * grip: the sword stays locked in his hand (no 180-degree spins between keys)
  * arm structure: forearm / hand / sword follow the upper arm on springs (overlap + settle) in every attack
  * walk: hunched, head low, sword dragged behind him with the tip scraping the ground, free claw swinging
  * idle / idle_combat / summon_loop: breathing, jaw, claw and sword-hand life
  * howl: new intimidation animation (gather, rear up, jaw wide, arms out, trembling howl)
Blender world: front = -Y, up = +Z. Bones are axis-aligned at their pivots (see tools/blender-geckolib)."""
import bpy, sys, os, math, random
from mathutils import Matrix, Vector, Euler, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "withered_sentinel.blend")
OUT = os.path.join(HERE, "withered_sentinel_reworked.blend")
bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
FPS = 20
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
PB = rig.pose.bones
R = random.Random(7)


def upd():
    bpy.context.view_layer.update()


# ---------------------------------------------------------------- rest-space reference points for aiming
def vg_points(name):
    idx = mesh.vertex_groups[name].index
    return [mesh.matrix_world @ v.co for v in mesh.data.vertices if any(g.group == idx and g.weight > 0.5 for g in v.groups)]


def head_rest(b):
    return rig.data.bones[b].head_local.copy()


SEG = {}
for S in ("right", "left"):
    SEG[f"{S}_arm"] = head_rest(f"{S}_forearm")
    SEG[f"{S}_forearm"] = head_rest(f"{S}_hand")
    pts = vg_points(f"{S}_hand"); SEG[f"{S}_hand"] = sum(pts, Vector()) / len(pts)
sw = vg_points("sword"); sh = head_rest("sword")
SEG["sword"] = max(sw, key=lambda p: (p - sh).length)            # blade tip
SWORD_PTS = sw


def world_pt(b, rest_pt):
    pb = PB[b]
    return pb.matrix @ pb.bone.matrix_local.inverted() @ rest_pt


def seg(b):
    return world_pt(b, SEG[b]) - PB[b].matrix.translation


def rotate_world(b, Rm):
    """Rotate bone b about its head by world rotation Rm (3x3 / quaternion)."""
    pb = PB[b]
    h = pb.matrix.translation.copy()
    M = Rm.to_matrix().to_4x4() if isinstance(Rm, Quaternion) else Rm.to_4x4()
    pb.matrix = Matrix.Translation(h) @ M @ Matrix.Translation(-h) @ pb.matrix
    upd()


def aim(b, d, blend=1.0):
    q = seg(b).normalized().rotation_difference(Vector(d).normalized())
    if blend < 1.0:
        q = Quaternion().slerp(q, blend)
    rotate_world(b, q)


def eul(x=0, y=0, z=0):
    return Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_matrix()


def sword_min_z():
    pb = PB["sword"]; M = pb.matrix @ pb.bone.matrix_local.inverted()
    return min((M @ p).z for p in SWORD_PTS)


# ---------------------------------------------------------------- action plumbing
def fcurve_bags(act):
    try:
        return [act.fcurves]
    except AttributeError:
        return [bag.fcurves for layer in act.layers for strip in layer.strips for bag in strip.channelbags]


def sample_locals(act, frames):
    rig.animation_data.action = act
    out = {}
    for f in frames:
        scene.frame_set(int(f), subframe=f - int(f)); upd()
        out[f] = {pb.name: (pb.rotation_euler.copy(), pb.location.copy(), pb.scale.copy()) for pb in PB}
    return out


PREV = {}


def key_all(f):
    for pb in PB:
        e = pb.rotation_euler.copy()
        if pb.name in PREV:
            e.make_compatible(PREV[pb.name])
        pb.rotation_euler = e; PREV[pb.name] = e.copy()
        pb.keyframe_insert("rotation_euler", frame=f, group=pb.name)
        pb.keyframe_insert("location", frame=f, group=pb.name)
        pb.keyframe_insert("scale", frame=f, group=pb.name)


def bake(name, base_act, length_s, override, base_frame=None, step=2, loop=None, gk_name=None):
    """Rebuild action `name`: per frame, start from base_act's pose (at base_frame(f) or f), apply override(f), key everything."""
    n = int(round(length_s * FPS))
    frames = list(range(0, n + 1, step))
    if frames[-1] != n:
        frames.append(n)
    src_frames = sorted(set((base_frame(f) if base_frame else f) for f in range(0, n + 1)))
    base = sample_locals(base_act, src_frames)
    old = bpy.data.actions.get(name)
    props = {k: old[k] for k in ("gk_name", "gk_length", "gk_loop")} if old and "gk_name" in old else {}
    act = bpy.data.actions.new(name + "__new"); act.use_fake_user = True
    rig.animation_data.action = act
    PREV.clear()
    for f in range(0, n + 1):                       # override runs every frame (springs), keys every `step`
        bf = base_frame(f) if base_frame else f
        for pb in PB:
            e, l, s = base[bf][pb.name]
            pb.rotation_euler = e; pb.location = l; pb.scale = s
        upd()
        override(f)
        if f in frames:
            key_all(f)
    for fc_list in fcurve_bags(act):
        for fc in fc_list:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    if old:
        old.use_fake_user = False; old.name = name + "__old"
    act.name = name
    act["gk_name"] = props.get("gk_name", gk_name or f"animation.withered_sentinel.{name}")
    act["gk_length"] = float(length_s)
    act["gk_loop"] = props.get("gk_loop", '"true"' if loop is True else ("false" if loop is None else '"%s"' % loop))
    if loop is True:
        act["gk_loop"] = "true"
    act.frame_range = (0, n)
    print("BAKED", name, n, "frames", flush=True)
    return act


# ---------------------------------------------------------------- springs: forearm / hand / sword trail the upper arm
class Spring:
    def __init__(self, lag, k=0.22, c=0.42, limit=28):
        self.lag, self.k, self.c, self.lim = lag, k, c, math.radians(limit)
        self.th = Vector(); self.v = Vector(); self.prev = None

    def step(self, parent_rot):
        if self.prev is None:
            self.prev = parent_rot.copy()
        dq = (parent_rot @ self.prev.inverted()).to_quaternion()
        w = dq.axis * dq.angle if dq.angle > 1e-6 else Vector()
        if w.length > math.pi * 0.5:
            w = Vector()
        self.prev = parent_rot.copy()
        target = -w * self.lag
        self.v += (target - self.th) * self.k - self.v * self.c
        self.th += self.v
        if self.th.length > self.lim:
            self.th = self.th.normalized() * self.lim
        return Matrix.Rotation(self.th.length, 3, self.th.normalized()) if self.th.length > 1e-6 else Matrix.Identity(3)


CHAINS = {"right": ["right_arm", "right_forearm", "right_hand", "sword"], "left": ["left_arm", "left_forearm", "left_hand"]}
LAGS = {"right_forearm": 1.5, "right_hand": 2.3, "sword": 3.0, "left_forearm": 1.6, "left_hand": 2.6}


def make_follow():
    springs = {b: Spring(l) for b, l in LAGS.items()}

    def follow():
        for chain in CHAINS.values():
            for i, b in enumerate(chain[1:], 1):
                parent = chain[i - 1]
                off = springs[b].step(PB[parent].matrix.to_3x3())
                rotate_world(b, off)
    return follow


# ================================================================ 1. sword grip: no half-turn spins
HELD = Euler((math.radians(59), 0, 0), "XZY")          # file (59, 180, 0) on top of the sword's rest (0, -180, 0)
for act in list(bpy.data.actions):
    if "gk_name" not in act:
        continue
    for fcs in fcurve_bags(act):
        cur = [fc for fc in fcs if fc.data_path == 'pose.bones["sword"].rotation_euler']
        if len(cur) != 3:
            continue
        cur.sort(key=lambda fc: fc.array_index)
        for kx, ky, kz in zip(*[fc.keyframe_points for fc in cur]):
            if abs(kx.co.y) < 0.05 and abs(abs(kz.co.y) - math.pi) < 0.05:      # the unrotated default = a spin
                kx.co.y, ky.co.y, kz.co.y = HELD.x, HELD.y, HELD.z
                for kp in (kx, ky, kz):
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        for fc in cur:
            fc.update()
print("GRIP_FIXED")

# ================================================================ 2. follow-through in every attack
for name in ("sweep", "push", "summon_start", "summon_end", "awaken", "stomp", "dash", "death"):
    act = bpy.data.actions[name]
    follow = make_follow()
    bake(name, act, act["gk_length"], lambda f: follow())

# ================================================================ 3. the walk: sword dragged behind him
walk_src = bpy.data.actions["walk"]
WALK_LEN = walk_src["gk_length"]                        # 2.4 s
NW = int(round(WALK_LEN * FPS))
foot_y = {}
for f, poses in sample_locals(walk_src, list(range(0, NW + 1))).items():
    pass


def walk_override_factory():
    follow_left = Spring(1.6); follow_left_hand = Spring(2.6)

    def ov(f):
        s = 2 * math.pi * f / NW
        step = abs(math.sin(s))                         # 0 at contacts (two per cycle), 1 mid-stride
        impact = math.exp(-((f % (NW // 2)) / 2.5))
        rotate_world("waist", eul(6 + 2 * impact))                       # hunched, heavy
        rotate_world("chest", eul(8 + 3 * impact, 0, 4 * math.sin(s)))
        rotate_world("head", eul(10 - 6 * impact, 0, -6 * math.sin(s - 0.7)))   # head low, slow menacing sway
        rotate_world("jaw", eul(10 + 6 * (0.5 + 0.5 * math.sin(2 * s + 1.0))))  # jaw hangs open, breathing
        # right arm: trailing behind, pulled by the weight of the dragging blade
        tug = 0.06 * math.sin(2 * s)
        aim("right_arm", (-0.30, 0.40 + tug, -0.87))
        aim("right_forearm", (-0.20, 0.62 + tug, -0.76))
        aim("right_hand", (-0.12, 0.80, -0.58))
        az = Vector((-0.18, 1.0, 0.0)).normalized()
        lo, hi = 0.0, 1.45                                                # blade angle below horizontal
        for _ in range(22):
            mid = (lo + hi) / 2
            aim("sword", az * math.cos(mid) + Vector((0, 0, -math.sin(mid))))
            if sword_min_z() < 0.02:
                hi = mid
            else:
                lo = mid
        aim("sword", az * math.cos(lo) + Vector((0, 0, -math.sin(lo))))
        rotate_world("sword", Matrix.Rotation(math.radians(R.uniform(-1.6, 1.6)), 3, seg("sword").normalized()))  # scrape chatter
        # left arm: free claw swinging with the stride (opposite leg), elbow bent, wrist lags
        sw_ = math.sin(s + math.pi)
        aim("left_arm", (0.30, -0.18 - 0.32 * sw_, -0.92))
        aim("left_forearm", (0.24, -0.55 - 0.25 * sw_, -0.75))
        rotate_world("left_forearm", follow_left.step(PB["left_arm"].matrix.to_3x3()))
        rotate_world("left_hand", eul(-18, 0, 0))                          # claw cocked up
        rotate_world("left_hand", follow_left_hand.step(PB["left_forearm"].matrix.to_3x3()))
    return ov


bake("walk", walk_src, WALK_LEN, walk_override_factory(), loop=True)

# ================================================================ 4. idles: breathing, jaw, claw, sword hand
def idle_factory(n, combat):
    follow = make_follow()

    def ov(f):
        s = 2 * math.pi * f / n
        b = math.sin(s)
        rotate_world("chest", eul(-1.5 * b))
        rotate_world("head", eul(2 * b, 0, (5 if combat else 3) * math.sin(s * 0.5 + 0.4)))
        rotate_world("jaw", eul(6 + 5 * (0.5 + 0.5 * math.sin(s - 0.6))))
        rotate_world("right_arm", eul(2.0 * b, 0, 1.5 * math.sin(s + 0.8)))        # sword hand shifts its weight
        rotate_world("left_arm", eul(3.5 * math.sin(s + 1.3), 0, -2 * b))
        rotate_world("left_hand", eul(-10 - 9 * math.sin(s * 2 + 0.3)))            # claw flexes
        follow()
    return ov


for name in ("idle", "idle_combat"):
    a = bpy.data.actions[name]
    bake(name, a, a["gk_length"], idle_factory(int(round(a["gk_length"] * FPS)), name == "idle_combat"), loop=True)


def channel_factory(n):
    follow = make_follow()

    def ov(f):
        s = 2 * math.pi * f / n
        tremble = math.sin(s * 6)
        rotate_world("chest", eul(-2 * math.sin(s), 0, 1.2 * tremble))
        rotate_world("head", eul(-4 - 3 * math.sin(s), 0, 2 * math.sin(s * 0.5)))
        rotate_world("jaw", eul(14 + 6 * math.sin(s * 2)))
        rotate_world("left_arm", eul(3 * math.sin(s), 0, 2 * tremble))
        rotate_world("right_arm", eul(2 * math.sin(s + 1), 0, -2 * tremble))
        rotate_world("left_hand", eul(-15 + 8 * tremble))
        follow()
    return ov


a = bpy.data.actions["summon_loop"]
bake("summon_loop", a, a["gk_length"], channel_factory(int(round(a["gk_length"] * FPS))), loop=True)

# ================================================================ 5. howl: the intimidation roar
HOWL_LEN = 3.2
NH = int(round(HOWL_LEN * FPS))


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def howl_factory():
    follow = make_follow()

    def ov(f):
        # phase weights: gather (0..12), rear (12..20), hold+tremble (20..48), settle (48..64)
        g = smooth(f / 12) * (1 - smooth((f - 12) / 8))
        r = smooth((f - 12) / 8) * (1 - smooth((f - 48) / 16))
        tr = math.sin(f * 2.6) * smooth((f - 20) / 4) * (1 - smooth((f - 44) / 6))
        rotate_world("waist", eul(10 * g - 10 * r))
        rotate_world("chest", eul(18 * g - 24 * r + 2.5 * tr, 0, 2.5 * tr))
        rotate_world("head", eul(16 * g - 40 * r + 3 * tr, 0, 4 * tr))
        rotate_world("jaw", eul(4 + 8 * g + 40 * r + 6 * tr))
        if r > 0.01 or g > 0.01:
            aim("left_arm", Vector((0.25, -0.35, -0.9)).lerp(Vector((0.85, -0.2, 0.35)), r) * 1.0, blend=max(g, r))
            aim("left_forearm", Vector((0.0, -0.6, -0.8)).lerp(Vector((0.7, -0.35, 0.6)), r), blend=max(g, r))
            rotate_world("left_hand", eul(-28 * r + 8 * tr))                   # claw splayed back
            aim("right_arm", Vector((-0.3, -0.3, -0.9)).lerp(Vector((-0.8, -0.1, -0.3)), r), blend=max(g, r))
            rotate_world("right_forearm", eul(-12 * r, 0, -8 * r))
        if abs(tr) > 0.0:
            rotate_world("left_arm", eul(2 * tr, 0, 2 * tr))
        follow()
    return ov


bake("howl", bpy.data.actions["idle_combat"], HOWL_LEN, howl_factory(), base_frame=lambda f: 0, loop=None,
     gk_name="animation.withered_sentinel.howl")

for a in list(bpy.data.actions):
    if a.name.endswith("__old"):
        bpy.data.actions.remove(a)
rig.animation_data.action = bpy.data.actions["walk"]
scene.frame_start, scene.frame_end = 0, NW
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REWORK_OK", OUT)
