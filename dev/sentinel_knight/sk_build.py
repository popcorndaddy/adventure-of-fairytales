"""Withered Sentinel (knight) - builds the Blender scene from scratch: armature, rigid armour blocks parented to bones,
two-handed greatsword on its own bone, heart + glow shell, FX anchors and collision / hitbox helpers.

Units: the spec is in Minecraft model pixels (16 px = 1 block = 1 Blender metre). Blender axes: +X = his LEFT,
-Y = his FRONT, +Z = up. Every block is a unit cube scaled to size; its material key is stored in the custom
property "sk_mat" and drives the texture painter in sk_export.py.

Run: blender -b --python sk_build.py -- <out.blend>"""
import bpy, sys, math
from mathutils import Vector, Matrix, Euler

OUT = sys.argv[sys.argv.index("--") + 1]
PX = 1 / 16

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene
scene.render.fps = 20

COLS = {}
for name in ("Sentinel_Armature", "Sentinel_Body", "Sentinel_Armor", "Sentinel_Weapon", "Sentinel_Heart",
             "Sentinel_Effects", "Sentinel_Collision", "Sentinel_Export"):
    c = bpy.data.collections.new(name); scene.collection.children.link(c); COLS[name] = c

# ============================================================== skeleton (heads/tails in px)
SIDE = {"R": -1, "L": 1}
ARM_X, LEG_X = 16.0, 10.0            # v15: shoulders and hips set wider to carry the user's model (was 14 / 6)
BONES = [  # name, parent, head, tail
    ("root", None, (0, 0, 0), (0, -4, 0)),
    ("pelvis", "root", (0, 0, 38), (0, 0, 44)),
    ("spine", "pelvis", (0, 0, 44), (0, 0, 52)),
    ("chest", "spine", (0, 0, 52), (0, 0, 64)),
    ("neck", "chest", (0, 0, 64), (0, 0, 68)),
    ("head", "neck", (0, 0, 68), (0, 0, 78)),
    ("heart", "chest", (0, -1.4, 58), (0, -1.4, 60)),
    ("heart_glow", "heart", (0, -1.4, 58), (0, -1.4, 60)),
]
for S, s in SIDE.items():
    x = s
    BONES += [
        (f"clavicle_{S}", "chest", (3 * x, 0, 62), ((ARM_X - 3) * x, 0, 62)),
        (f"upperarm_{S}", f"clavicle_{S}", (ARM_X * x, 0, 61), (ARM_X * x, 0, 47)),
        (f"forearm_{S}", f"upperarm_{S}", (ARM_X * x, 0, 47), (ARM_X * x, 0, 35)),
        (f"hand_{S}", f"forearm_{S}", (ARM_X * x, 0, 35), (ARM_X * x, 0, 30)),
        (f"thigh_{S}", "pelvis", (LEG_X * x, 0, 38), (LEG_X * x, 0, 22)),
        (f"shin_{S}", f"thigh_{S}", (LEG_X * x, 0, 22), (LEG_X * x, 0, 6)),
        (f"foot_{S}", f"shin_{S}", (LEG_X * x, 0, 6), (LEG_X * x, -5.5, 2)),
        (f"toe_{S}", f"foot_{S}", (LEG_X * x, -5.5, 2), (LEG_X * x, -10, 1.5)),
    ]
    for fi, fy in (("index", -1.7), ("middle", 0.0), ("ring", 1.7)):
        BONES += [(f"{fi}1_{S}", f"hand_{S}", ((ARM_X + 0.2) * x, fy, 30), ((ARM_X + 0.2) * x, fy, 27.3)),
                  (f"{fi}2_{S}", f"{fi}1_{S}", ((ARM_X + 0.2) * x, fy, 27.3), ((ARM_X + 0.2) * x, fy, 24.8))]
    BONES += [(f"thumb1_{S}", f"hand_{S}", ((ARM_X - 1.4) * x, -2.4, 33), ((ARM_X - 1.7) * x, -3.4, 30.6)),
              (f"thumb2_{S}", f"thumb1_{S}", ((ARM_X - 1.7) * x, -3.4, 30.6), ((ARM_X - 1.9) * x, -4.0, 28.6))]
# the sword: bone head = right-hand grip point; at rest the blade points straight forward (-Y)
GRIP = (-ARM_X, -1.0, 32.0)
BONES.append(("sword", "hand_R", GRIP, (GRIP[0], GRIP[1] - 6, GRIP[2])))
# secondary motion: a three-panel cape (three segments each) and four tassets that swing with the legs
BONES.append(("cape_root", "chest", (0, 5.6, 63.5), (0, 5.6, 61.5)))
for s, x in (("L", 8.6), ("M", 0.0), ("R", -8.6)):
    BONES += [(f"cape_{s}1", "cape_root", (x, 6.4, 62.5), (x, 6.4, 43.5)),
              (f"cape_{s}2", f"cape_{s}1", (x, 6.4, 43.5), (x, 6.4, 24.5)),
              (f"cape_{s}3", f"cape_{s}2", (x, 6.4, 24.5), (x, 6.4, 5.5))]
for n, h in (("F", (0, -5.4, 40.5)), ("B", (0, 5.8, 40.5)), ("L", (9.0, 0.0, 40.5)), ("R", (-9.0, 0.0, 40.5))):
    BONES.append((f"tasset_{n}", "pelvis", h, (h[0], h[1], h[2] - 10)))

arm = bpy.data.armatures.new("Sentinel_Armature")
rig = bpy.data.objects.new("Sentinel_Rig", arm)
COLS["Sentinel_Armature"].objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
for name, parent, h, t in BONES:
    b = arm.edit_bones.new(name)
    b.head = Vector(h) * PX; b.tail = Vector(t) * PX; b.roll = 0
    if parent:
        b.parent = eb[parent]
    b.use_connect = False
    eb[name] = b
bpy.ops.object.mode_set(mode="OBJECT")
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"
arm.display_type = "STICK"

# ============================================================== blocks
NB = {"n": 0}


def block(bone, c, size, mat, rot=(0, 0, 0), coll="Sentinel_Armor", name=None):
    NB["n"] += 1
    me = bpy.data.meshes.new(f"blk{NB['n']}")
    v = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
         (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
    f = [(0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)]
    me.from_pydata(v, [], f); me.update()
    o = bpy.data.objects.new(name or f"{bone}.{mat}.{NB['n']:03d}", me)
    COLS[coll].objects.link(o)
    W = Matrix.Translation(Vector(c) * PX) @ Euler(tuple(math.radians(a) for a in rot), "XYZ").to_matrix().to_4x4() \
        @ Matrix.Diagonal((*(Vector(size) * PX), 1))
    o.parent = rig; o.parent_type = "BONE"; o.parent_bone = bone
    o.matrix_world = W
    o["sk_mat"] = mat; o["sk_bone"] = bone
    o.color = MAT_COLOR.get(mat, (0.3, 0.3, 0.3, 1))
    return o


MAT_COLOR = {"obsidian": (0.05, 0.045, 0.06, 1), "gunmetal": (0.16, 0.16, 0.18, 1), "iron": (0.1, 0.095, 0.11, 1),
             "void": (0.0, 0.0, 0.0, 1), "cavity": (0.15, 0.03, 0.22, 1), "heart": (0.8, 0.2, 0.9, 1),
             "heart_glow": (0.5, 0.1, 0.7, 1), "eye": (0.6, 0.3, 1.0, 1), "blade": (0.13, 0.13, 0.15, 1),
             "grip": (0.12, 0.08, 0.06, 1), "rune": (0.06, 0.05, 0.08, 1), "cloth": (0.16, 0.05, 0.24, 1),
             "emblem": (0.1, 0.05, 0.16, 1), "energy": (0.7, 0.3, 1.0, 1), "bronze": (0.35, 0.25, 0.12, 1)}


def sym(bone, c, size, mat, rot=(0, 0, 0), coll="Sentinel_Armor"):
    """Build for the RIGHT side (x < 0 given as negative), mirror to the left."""
    block(f"{bone}_R", c, size, mat, rot, coll)
    block(f"{bone}_L", (-c[0], c[1], c[2]), size, mat, (rot[0], -rot[1], -rot[2]), coll)


# ---------------- armour, heart and sword live in sk_armor.py
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sk_armor.py")).read())


# ---------------------------------------------------------------- v7: bulkier armour (+35% width) around the same skeleton
# Every block is widened about its own bone's axis, so it stays centred on the joint the animations move:
# torso pieces get wider and deeper, limbs get more girth, boots get wider (not taller), the cape spans the wider back.
WIDEN = 1.15                                                      # v10: less bulk (was 1.35)
# the torso follows a curved V profile by height (px): broad upper chest, narrow waist, a little flare at the hips
TORSO_PROFILE = [(30, 1.0), (38, 1.0), (42, 0.92), (46, 0.8), (50, 0.84), (55, 0.9), (60, 0.95), (66, 0.98), (80, 0.98)]   # v14: narrow enough that the arms stand clear


def torso_k(z_px):
    for (z0, k0), (z1, k1) in zip(TORSO_PROFILE, TORSO_PROFILE[1:]):
        if z_px <= z1:
            w = max(0.0, min(1.0, (z_px - z0) / (z1 - z0)))
            w = w * w * (3 - 2 * w)                                   # smooth, so the outline curves
            return k0 + (k1 - k0) * w
    return TORSO_PROFILE[-1][1]
TORSO = ("pelvis", "spine", "chest", "neck", "cape_root", "clavicle_L", "clavicle_R", "tasset_F", "tasset_B", "tasset_L", "tasset_R", "heart", "heart_glow")
LIMB = ("upperarm_L", "upperarm_R", "forearm_L", "forearm_R", "thigh_L", "thigh_R", "shin_L", "shin_R", "hand_L", "hand_R")


def _widen():
    n = 0
    for o in [o for o in bpy.data.objects if "sk_mat" in o]:
        b = o["sk_bone"]
        bone = rig.data.bones[b]
        h = bone.head_local.copy(); a = (bone.tail_local - bone.head_local).normalized()
        k = WIDEN
        if b in TORSO or b == "head":
            if b == "head":
                W = Matrix.Diagonal((1.2, 1.12, 1.0))             # v14: a big helm, as in the pictures
            else:
                kz = torso_k(o.matrix_world.translation.z * 16)   # width by height: the V and the waist curve
                if b in ("clavicle_L", "clavicle_R", "tasset_L", "tasset_R"):
                    h = rig.data.bones["pelvis"].head_local.copy()  # side pieces follow the torso outline
                W = Matrix.Diagonal((kz, 1 + (kz - 1) * 0.55, 1.0))  # depth follows the width, more gently
        elif b in LIMB:
            if b.startswith("hand"):
                k = 1.1
            I = Matrix.Identity(3); aa = Matrix(((a.x * a.x, a.x * a.y, a.x * a.z), (a.y * a.x, a.y * a.y, a.y * a.z), (a.z * a.x, a.z * a.y, a.z * a.z)))
            W = I + (I - aa) * (k - 1)                              # more girth, same length
        elif b.startswith(("foot_", "toe_")):
            W = Matrix.Diagonal((k, 1.0, 1.0))                    # wider sabatons, sole stays on the floor
        elif b.startswith("cape_"):
            h = Vector((0, h.y, h.z))
            W = Matrix.Diagonal((k, 1.0, 1.0))
        else:
            continue                                              # sword, fingers, thumbs keep their size
        M = o.matrix_world.copy()
        loc, rot, scl = M.decompose()
        R = rot.to_matrix()
        p = h + W @ (loc - h)
        s_new = [scl[i] * (W @ R.col[i]).length for i in range(3)]
        o.matrix_world = Matrix.Translation(p) @ R.to_4x4() @ Matrix.Diagonal((*s_new, 1))
        n += 1
    print("WIDENED", n, "blocks", flush=True)


_widen()

# ---------------- FX anchors (empties on bones: where effects / hits are spawned)
def anchor(name, bone, p):
    e = bpy.data.objects.new(name, None); e.empty_display_type = "SPHERE"; e.empty_display_size = 0.12
    COLS["Sentinel_Effects"].objects.link(e)
    e.parent = rig; e.parent_type = "BONE"; e.parent_bone = bone
    e.matrix_world = Matrix.Translation(Vector(p) * PX)
    return e


anchor("FX_Heart", "heart", (0, -1.4, 58))
anchor("FX_SwordTip", "sword", (gx, gy - SWORD_LEN, gz))
anchor("FX_SwordMid", "sword", (gx, gy - 30, gz))
anchor("FX_Palm_L", "hand_L", (14, -1.0, 30))
anchor("FX_Foot_R", "foot_R", (-6, -2, 0))
anchor("FX_Foot_L", "foot_L", (6, -2, 0))
anchor("FX_Eyes", "head", (0, -4.2, 74))

# ---------------- collision + hitbox helpers (NOT exported as model geometry)
def helper(name, c, size, bone=None, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    v = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
         (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
    f = [(0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)]
    me.from_pydata(v, [], f)
    o = bpy.data.objects.new(name, me); COLS["Sentinel_Collision"].objects.link(o)
    W = Matrix.Translation(Vector(c) * PX) @ Euler(tuple(math.radians(a) for a in rot), "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((*(Vector(size) * PX), 1))
    if bone:
        o.parent = rig; o.parent_type = "BONE"; o.parent_bone = bone
    o.matrix_world = W
    o.display_type = "WIRE"; o.hide_render = True
    return o


def ring_helper(name, radius_px, arc_deg=360, z=0.1):
    n = 48
    a0 = -math.radians(arc_deg) / 2
    pts = [(0, 0, z * PX)] if arc_deg < 360 else []
    for i in range(n + 1):
        a = a0 + math.radians(arc_deg) * i / n
        pts.append((math.sin(a) * radius_px * PX, -math.cos(a) * radius_px * PX, z * PX))
    me = bpy.data.meshes.new(name); me.from_pydata(pts, [(i, i + 1) for i in range(len(pts) - 1)], [])
    o = bpy.data.objects.new(name, me); COLS["Sentinel_Collision"].objects.link(o); o.hide_render = True
    return o


helper("COL_Body", (0, 0, 40), (35, 35, 83))                    # entity box: 2.2 x 5.2 blocks
helper("COL_Head", (0, 0, 74), (11, 11, 12), "head")
helper("COL_Chest", (0, 0.5, 57), (21, 11, 14), "chest")
for S, x in (("R", -1), ("L", 1)):
    helper(f"COL_Arm_{S}", (14 * x, 0, 47), (7, 7, 30), f"upperarm_{S}")
    helper(f"COL_Leg_{S}", (6 * x, 0, 22), (8.5, 8.5, 32), f"thigh_{S}")
    helper(f"COL_Foot_{S}", (6 * x, -2, 3), (8, 12, 6), f"foot_{S}")
helper("COL_Sword", (gx, gy - 30, gz), (8.4, 52, 2.2), "sword")
ring_helper("HIT_Sweep_Arc", 5.2 * 16, 230)                     # sweep: 5.2 blocks, 230 degrees in front
ring_helper("HIT_Stomp_Radius", 4.5 * 16)                       # stomp: 4.5 blocks all round
helper("HIT_Dash_Box", (0, -2.2 * 16, 40), (3.0 * 16, 3.0 * 16, 60))   # dash: 3 blocks ahead while lunging
helper("HIT_Push_Cone", (0, -5 * 16, 48), (5 * 16, 9 * 16, 48))         # push: 9 blocks forward, wide
for o in COLS["Sentinel_Collision"].objects:
    o["sk_helper"] = True

# ---------------- export settings
t = bpy.data.texts.new("Sentinel_Export_README")
t.write("Export with sk_export.py: model blocks = Sentinel_Body/Armor/Weapon/Heart (rigid bone parented).\n"
        "Sentinel_Collision holds helpers only: COL_* = gameplay/collision references, HIT_* = attack shapes.\n"
        "Sentinel_Effects holds FX_* anchors used for particle/hit spawn points.\n")
# v15: the user's own model replaces the hand-built armour when its working copy is present
if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "meshy", "user_glb", "work.blend")):
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sk_glb.py")).read())
scene["sk_grip_l_s"] = GRIP_L_S; scene["sk_sword_len"] = SWORD_LEN; scene["sk_grip"] = GRIP
bpy.ops.wm.save_as_mainfile(filepath=OUT)
n = sum(1 for o in bpy.data.objects if "sk_mat" in o)
print(f"BUILD_OK bones {len(arm.bones)} blocks {n}")
