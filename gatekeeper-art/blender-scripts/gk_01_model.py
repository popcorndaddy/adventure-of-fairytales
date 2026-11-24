"""Stage 1 - build the Ancient Gatekeeper: collections, materials, skeleton, all meshes (skinned), save + rest renders."""
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from mathutils import Matrix, Vector
import gk_lib as L
import gk_scene as SC

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"; scene.unit_settings.scale_length = 1.0

# ---------------------------------------------------------------- collections
root = bpy.data.collections.new("Gatekeeper_Root"); scene.collection.children.link(root)
NAMES = ["Gatekeeper_Torso", "Gatekeeper_Head", "Gatekeeper_Arm_L", "Gatekeeper_Arm_R", "Gatekeeper_Additional_Arms",
         "Gatekeeper_Legs", "Gatekeeper_Armor", "Gatekeeper_Runes", "Gatekeeper_Weapon", "Gatekeeper_Visual_Effects",
         "Gatekeeper_Rig"]
C = {}
for n in NAMES:
    c = bpy.data.collections.new(n); root.children.link(c); C[n] = c

mats = L.make_materials(os.path.join(OUT, "textures"))
rig = L.build_armature(C["Gatekeeper_Rig"])
B = L.Builder(mats)

TORSO = ("Gatekeeper_Torso", "GK_Torso"); ROBE = ("Gatekeeper_Torso", "GK_Robe")
HEAD = ("Gatekeeper_Head", "GK_Head"); LEGS = ("Gatekeeper_Legs", "GK_Legs")
ARMOR = ("Gatekeeper_Armor", "GK_Armor"); ARMOR_ARMS = ("Gatekeeper_Armor", "GK_Armor_Arms")
CHAINS = ("Gatekeeper_Armor", "GK_Chains"); RUNES = ("Gatekeeper_Runes", "GK_Runes")
WEAPON = ("Gatekeeper_Weapon", "GK_Weapon"); VFX = ("Gatekeeper_Visual_Effects", "GK_VFX")
ARM = {"L": ("Gatekeeper_Arm_L", "GK_Arm_L"), "R": ("Gatekeeper_Arm_R", "GK_Arm_R")}
XARM = {"L": ("Gatekeeper_Additional_Arms", "GK_Arm_Extra_L"), "R": ("Gatekeeper_Additional_Arms", "GK_Arm_Extra_R")}
G = L.GLYPHS
box = B.box


def sx(a, b, s):
    """x-range a..b mirrored to side s (+1 left / -1 right), returned sorted."""
    return (min(a * s, b * s), max(a * s, b * s))


def glyph_front(obj, bone, g, cx, ztop, y, px=1.0, mat="PurpleEnergy", hot=None):
    w = len(g[0]) * px
    L.glyph(B, obj, bone, g, (cx - w / 2, y, ztop), (1, 0, 0), (0, 0, 1), (0, -1, 0), px=px, depth=0.6, mat=mat, hot_top=hot)


def glyph_side(obj, bone, g, s, x, cy, ztop, px=1.0, mat="PurpleEnergy"):
    # on a face looking toward +X (s=+1) or -X (s=-1); 'right' as seen from outside
    w = len(g[0]) * px
    right = (0, s, 0)
    L.glyph(B, obj, bone, g, (x, cy - w / 2 * s, ztop), right, (0, 0, 1), (s, 0, 0), px=px, depth=0.6, mat=mat)


def frame(obj, bone, x0, x1, z0, z1, y, t=1.0, mat="WeatheredBronze"):
    box(obj, bone, x0, x1, y - 0.8, y, z1 - t, z1, mat, bevel=True)
    box(obj, bone, x0, x1, y - 0.8, y, z0, z0 + t, mat, bevel=True)
    box(obj, bone, x0, x0 + t, y - 0.8, y, z0, z1, mat, bevel=True)
    box(obj, bone, x1 - t, x1, y - 0.8, y, z0, z1, mat, bevel=True)


def link_basis(d, twist):
    y = Vector(d).normalized()
    h = Vector((0, 0, 1)) if abs(y.z) < 0.9 else Vector((1, 0, 0))
    x = y.cross(h).normalized(); z = x.cross(y)
    if twist:
        x, z = z, -x
    return Matrix((x, y, z)).transposed().to_4x4()


def chain_line(obj, bone, a, b, link=3.4):
    a, b = Vector(a), Vector(b)
    d = b - a; n = max(1, round(d.length / (link * 0.82)))
    for i in range(n):
        c = a + d * ((i + 0.5) / n)
        M = Matrix.Translation(c) @ link_basis(d, i % 2)
        box(obj, bone, -1.3, 1.3, -link / 2, link / 2, -0.5, 0.5, "ChainIron", M=M)


def hang_chain(obj, bone, x, ztop, y, length, tablet=None):
    n = max(1, round(length / 3.0))
    for i in range(n):
        z1 = ztop - i * 3.0; z0 = z1 - 3.6
        if i % 2 == 0:
            box(obj, bone, x - 1.3, x + 1.3, y - 0.5, y + 0.5, z0, z1, "ChainIron")
        else:
            box(obj, bone, x - 0.5, x + 0.5, y - 1.3, y + 1.3, z0, z1, "ChainIron")
    if tablet:
        zb = ztop - n * 3.0 - 0.5
        box(obj, bone, x - 4, x + 4, y - 0.7, y + 0.7, zb - 10, zb, "AncientDarkIron", bevel=True)
        frame(obj, bone, x - 4, x + 4, zb - 10, zb, y - 0.7, 0.8)
        L.glyph(B, RUNES, bone, tablet[0], (x - 2.25, y - 1.5, zb - 1.5), (1, 0, 0), (0, 0, 1), (0, -1, 0), px=0.9, depth=0.5, mat=tablet[1])


# ================================================================ TORSO
box(TORSO, "hips", -12, 12, -9, 8, 36, 48, "AncientDarkIron", bevel=True)
box(ARMOR, "hips", -15, 15, -11, 11, 44, 51, "CorruptedStone", bevel=True)
for x in (-9.5, 0, 9.5):
    box(ARMOR, "hips", x - 4, x + 4, -12.2, -11, 44.5, 50.5, "WeatheredBronze", bevel=True)
    box(ARMOR, "hips", x - 4, x + 4, 11, 12.2, 44.5, 50.5, "WeatheredBronze", bevel=True)
glyph_front(RUNES, "hips", G[3], 0, 50.2, -12.2, px=0.82, mat="CyanRunes")
glyph_front(RUNES, "hips", G[1], -9.5, 50.2, -12.2, px=0.82)
glyph_front(RUNES, "hips", G[4], 9.5, 50.2, -12.2, px=0.82)

box(TORSO, "spine", -10, 10, -7, 7, 50, 66, "DarkSteel")
for i, z in enumerate((51, 55.5, 60)):                       # layered abdominal lames
    w = 11 + i * 1.2
    box(ARMOR, "spine", -w, w, -9 - i * 0.4, 8.5, z, z + 5, "AncientDarkIron", bevel=True)
    box(ARMOR, "spine", -w + 1, w - 1, -9.6 - i * 0.4, -9 - i * 0.4, z + 3.6, z + 5, "WeatheredBronze")

box(TORSO, "chest", -14, 14, -9, 9, 64, 86, "CorruptedStone", bevel=True)
for (x0, x1, z0, z1) in ((-15.5, -8, 64, 85), (8, 15.5, 64, 85), (-8, 8, 83, 86), (-8, 8, 64, 70)):
    box(ARMOR, "chest", x0, x1, -11, -9, z0, z1, "AncientDarkIron", bevel=True)
for x0, x1 in ((-8, -7), (-0.75, 0.75), (7, 8)):            # 2x2 core window frame
    box(ARMOR, "chest", x0, x1, -11.6, -9.2, 70, 83, "WeatheredBronze", bevel=True)
for z0, z1 in ((70, 71), (76, 77), (82, 83)):
    box(ARMOR, "chest", -8, 8, -11.6, -9.2, z0, z1, "WeatheredBronze", bevel=True)
for xs in ((-7, -0.75), (0.75, 7)):
    for zs in ((71, 76), (77, 82)):
        box(VFX, "chest", xs[0], xs[1], -10.4, -9.4, zs[0], zs[1], "PurpleEnergy")
        cx, cz = sum(xs) / 2, sum(zs) / 2
        box(VFX, "chest", cx - 1.6, cx + 1.6, -10.7, -10.3, cz - 1.6, cz + 1.6, "EyeGlow")
glyph_front(RUNES, "chest", G[5], 0, 69.4, -11, px=0.72, mat="CyanRunes")
glyph_front(RUNES, "chest", G[2], -11.8, 82, -11, px=0.95)
glyph_front(RUNES, "chest", G[3], 11.8, 82, -11, px=0.95)
box(ARMOR, "chest", -16, 16, -12, 11, 84, 88, "AncientDarkIron", bevel=True)
box(ARMOR, "chest", -15, 15, 9, 11.5, 66, 85, "RuneStone", bevel=True)
for z in (68, 73.5, 79):
    box(ARMOR, "chest", -3, 3, 11.5, 14, z, z + 4, "WeatheredBronze", bevel=True)
for s, S in ((1, "L"), (-1, "R")):                             # lower-arm shoulder joint housings
    a, b = sx(13, 19, s)
    box(ARMOR, f"clavicle_{S}", a, b, -6.5, 6.5, 63, 74, "WeatheredBronze", bevel=True)
    a, b = sx(19, 21, s)
    box(ARMOR, f"clavicle_{S}", a, b, -4.5, 4.5, 64.5, 72.5, "DarkSteel", bevel=True)
# chains across the chest
chain_line(CHAINS, "chest", (-21, -12.3, 86), (0, -12.9, 66.5))
chain_line(CHAINS, "chest", (0, -12.9, 66.5), (21, -12.3, 86))
chain_line(CHAINS, "chest", (-17, -12.6, 86.5), (17, -12.6, 86.5))
hang_chain(CHAINS, "chain_chest", 0, 66, -13, 5, (G[3], "CyanRunes"))
# belt chains and tablets
chain_line(CHAINS, "hips", (-15, -12.8, 50), (0, -13.4, 44.5))
chain_line(CHAINS, "hips", (0, -13.4, 44.5), (15, -12.8, 50))
hang_chain(CHAINS, "chain_belt", -8, 44, -13.2, 6, (G[0], "PurpleEnergy"))
hang_chain(CHAINS, "chain_belt", 8, 44, -13.2, 4, (G[4], "PurpleEnergy"))

# ---------------------------------------------------------------- tattered robe
rr = random.Random(500)


def robe_ring(N, rx, ry, ztop, tilt0, tilt_side, gap, plated):
    for i in range(N):
        phi = 2 * math.pi * i / N                      # 0 = back (+Y), pi = front (-Y)
        fr = abs(((phi - math.pi) + math.pi) % (2 * math.pi) - math.pi)
        if fr < gap:
            continue
        pos = Vector((rx * math.sin(phi), ry * math.cos(phi), ztop))
        side = abs(math.sin(phi))
        tilt = math.radians(tilt0 + tilt_side * side + rr.uniform(0, 4))
        maxL = (ztop - 0.6) / math.cos(tilt)
        Lr = min(maxL, maxL - rr.uniform(0, 6)); w = rr.uniform(6, 8.5)
        bone = "robe_B" if math.cos(phi) > 0.7 else ("robe_L" if pos.x > 0 else "robe_R")
        if fr < math.radians(70):
            bone = "robe_L" if pos.x > 0 else "robe_R"
        M = Matrix.Translation(pos) @ Matrix.Rotation(-phi, 4, "Z") @ Matrix.Rotation(tilt, 4, "X")
        mat = "RuneStone" if plated and i % 3 == 0 else "TatteredCloth"
        box(ROBE, bone, -w / 2, w / 2, -1, 1, -Lr, 0, mat, M=M)
        tip = min(rr.uniform(3, 8), maxL - Lr)
        if tip > 1:
            box(ROBE, bone, -w / 5, w / 5, -1, 1, -Lr - tip, -Lr + 1, "TatteredCloth", M=M)
        if rr.random() < 0.3:
            box(ROBE, bone, -0.5, 0.5, -1.15, 1.15, -Lr * 0.75, -Lr * 0.2, "PurpleEnergy", M=M)
        if plated and i % 3 == 0:
            box(ROBE, bone, -w / 2 - 0.3, w / 2 + 0.3, -1.3, 1.3, -3, 0, "WeatheredBronze", M=M)


robe_ring(24, 14, 11, 46, 6, 6, math.radians(44), False)
robe_ring(32, 18.5, 14.5, 47, 15, 15, math.radians(40), True)
box(ROBE, "robe_F", -5, 5, -12.4, -11.4, 9, 44, "TatteredCloth")
box(ROBE, "robe_F", -2.5, 2.5, -12.4, -11.4, 3.5, 9, "TatteredCloth")
box(ROBE, "robe_F", -4, 4, -12.9, -12.4, 22, 33, "AncientDarkIron", bevel=True)
glyph_front(RUNES, "robe_F", G[0], 0, 31.5, -12.9, px=1.05, mat="CyanRunes")

# ================================================================ LEGS (rune pillars)
for s, S in ((1, "L"), (-1, "R")):
    box(LEGS, f"thigh_{S}", *sx(2, 14, s), -6, 6, 28, 46, "AncientDarkIron", bevel=True)
    box(ARMOR, f"shin_{S}", *sx(1.5, 16.5, s), -8.5, 6.5, 25, 31, "WeatheredBronze", bevel=True)
    box(LEGS, f"shin_{S}", *sx(2, 16, s), -7.5, 6.5, 7, 26, "CorruptedStone", bevel=True,
        faces={"left": "RuneStone", "right": "RuneStone"})
    a, b = sx(3.5, 14.5, s)
    frame(ARMOR, f"shin_{S}", a, b, 9, 24, -7.5, 1.1)
    glyph_front(RUNES, f"shin_{S}", G[4], (a + b) / 2, 22.7, -8.3, px=1.55)
    box(ARMOR, f"shin_{S}", *sx(1, 17, s), -9, 7.5, 5.5, 9, "AncientDarkIron", bevel=True)
    box(LEGS, f"foot_{S}", *sx(0, 18, s), -12.5, 8, 0, 6, "RuneStone", bevel=True)
    box(ARMOR, f"foot_{S}", *sx(1, 17, s), -13.5, -11.5, 0, 5, "WeatheredBronze", bevel=True)
    box(LEGS, f"foot_{S}", *sx(1.5, 16.5, s), -10.5, 7, 6, 7.5, "CorruptedStone", bevel=True)

# ================================================================ HEAD + CROWN
box(HEAD, "neck", -5, 5, -6, 4, 85, 92, "DarkSteel")
box(HEAD, "head", -9, 9, -9, 8, 91, 108, "CorruptedStone", bevel=True)
box(HEAD, "head", -8, 8, -10.2, -9, 92, 103.5, "DarkSteel", bevel=True)
L.glyph(B, RUNES, "head", L.EYE, (-7, -10.2, 102.5), (1, 0, 0), (0, 0, 1), (0, -1, 0), px=1, depth=0.6, mat="EyeGlow", hot_top="EyeGlow")
L.glyph(B, RUNES, "head", L.EYE, (2, -10.2, 102.5), (1, 0, 0), (0, 0, 1), (0, -1, 0), px=1, depth=0.6, mat="EyeGlow", hot_top="EyeGlow")
box(RUNES, "head", -6.5, -5.5, -10.6, -10.2, 94, 97.5, "PurpleEnergy")
box(RUNES, "head", 5.5, 6.5, -10.6, -10.2, 93, 97.5, "PurpleEnergy")
frame(ARMOR, "head", -5.5, 5.5, 92, 96.5, -10.2, 0.9)
for (x0, x1, z0, z1) in ((-3.6, -1.2, 93.6, 94.8), (1.2, 3.6, 93.6, 94.8), (-0.8, 0.8, 92.9, 93.9)):
    box(RUNES, "head", x0, x1, -10.8, -10.2, z0, z1, "CyanRunes")
box(ARMOR, "head", -10, 10, -11.2, 9.5, 104, 110, "AncientDarkIron", bevel=True)
for s in (1, -1):
    box(ARMOR, "head", *sx(9, 11, s), -9.5, 6, 93, 104.5, "AncientDarkIron", bevel=True)
box(HEAD, "head", -8, 8, -8, 7, 110, 116, "RuneStone", bevel=True)
box(ARMOR, "head", -9, 9, -9, 8, 115, 117, "WeatheredBronze", bevel=True)
box(HEAD, "head", -5, 5, -5.5, 4.5, 117, 123, "RuneStone", bevel=True)
box(HEAD, "head", -1.5, 1.5, -2, 1, 123, 133, "DarkSteel", bevel=True)
box(RUNES, "head", -4.5, 4.5, -1.6, 0.6, 128, 130, "PurpleEnergy")
box(RUNES, "head", -1, 1, -1.5, 0.5, 133, 135, "MagentaFragments")
glyph_front(RUNES, "head", G[0], 0, 115.4, -8.2, px=0.72)
for x in (-6.5, 6.5):                                           # spired crown towers (second reference)
    for y, fm, top in ((-6.5, "CyanRunes", 127), (5.5, "PurpleEnergy", 124)):
        box(ARMOR, "head", x - 1.4, x + 1.4, y - 1.4, y + 1.4, 116, top - 3, "AncientDarkIron", bevel=True)
        box(ARMOR, "head", x - 1.0, x + 1.0, y - 1.0, y + 1.0, top - 3, top, "DarkSteel", bevel=True)
        box(RUNES, "head", x - 1.5, x + 1.5, y - 1.5, y + 1.5, top - 6, top - 5.2, fm)
        box(VFX, "head", x - 0.7, x + 0.7, y - 0.7, y + 0.7, top, top + 2.2, fm)
for x, y in ((-4, -4.5), (4, -4.5), (-4, 3.5), (4, 3.5)):
    box(ARMOR, "head", x - 0.9, x + 0.9, y - 0.9, y + 0.9, 123, 128.5, "DarkSteel", bevel=True)
    box(RUNES, "head", x - 0.5, x + 0.5, y - 0.5, y + 0.5, 128.5, 130, "MagentaFragments")

# ================================================================ PAULDRONS (huge rune shoulders)
for s, S in ((1, "L"), (-1, "R")):
    bone = f"clavicle_extra_{S}"
    cx = 25 * s
    box(ARMOR, bone, *sx(13, 37, s), -13, 13, 76, 96, "RuneStone", bevel=True, faces={"front": "CorruptedStone"})
    a, b = sx(15.5, 34.5, s)
    frame(ARMOR, bone, a, b, 78.5, 93.5, -13, 1.2)
    glyph_front(RUNES, bone, G[2], cx, 92, -13.8, px=1.55)
    box(ARMOR, bone, *sx(12, 38, s), -14, 14, 94, 96.5, "WeatheredBronze", bevel=True)
    box(ARMOR, bone, *sx(15, 35, s), -11, 11, 96.5, 101, "AncientDarkIron", bevel=True)
    box(ARMOR, bone, *sx(21, 29, s), -4, 4, 101, 105, "DarkSteel", bevel=True)
    for (h0, h1, w) in ((105, 109, 3), (109, 112.5, 2.2), (112.5, 115, 1.2)):
        box(VFX, bone, cx - w, cx + w, -w, w, h0, h1, "CyanRunes")
    box(ARMOR, bone, *sx(37, 39.5, s), -10, 10, 78, 94, "AncientDarkIron", bevel=True)
    glyph_side(RUNES, bone, G[1], s, 39.5 * s, 0, 91, px=1.3)
    box(ARMOR, bone, *sx(15, 37.5, s), -12.5, 12.5, 72, 76.5, "AncientDarkIron", bevel=True)
    box(ARMOR, bone, *sx(18, 36, s), -11, 11, 68.5, 72.5, "DarkSteel", bevel=True)
    for (x0, z0, x1, z1) in ((14, 93, 17, 88), (17, 88, 16, 83)):   # glowing magenta cracks in the stone
        a, b = sx(x0, x0 + 0.6, s)
        box(RUNES, bone, a, b, -13.3, -12.9, min(z0, z1), max(z0, z1), "MagentaFragments")
    for i, (x, ln, tab) in enumerate(((16, 10, None), (25, 18, (G[0], "PurpleEnergy")), (34, 8, None))):
        hang_chain(CHAINS, f"chain_shoulder_{S}", x * s, 72, -13.6, ln, tab)
    hang_chain(CHAINS, f"chain_shoulder_back_{S}", 24 * s, 72, 12.8, 14)
    chain_line(CHAINS, bone, (14 * s, -13.8, 80), (28 * s, -13.8, 74))
    for (x0, x1, z0, z1) in ((35, 37.5, 93, 96), (13, 15.5, 76, 78.5)):  # broken chips on the corners
        a, b = sx(x0, x1, s)
        box(ARMOR, bone, a, b, -14.2, -12.5, z0, z1, "CorruptedStone")


# ================================================================ ARMS
def MB(name):
    return L.bone_px_matrix(rig, name)


def axes(name, s):
    """Local axes of a bone: (spread_axis_index, out_axis_vector_local) - spread = the local X/Z most aligned
    with world Y; front = local axis most aligned with world -Y."""
    R3 = rig.data.bones[name].matrix_local.to_3x3()
    cands = [Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1)), Vector((0, 0, -1))]
    front = max(cands, key=lambda c: (R3 @ c).dot(Vector((0, -1, 0))))
    outw = max(cands, key=lambda c: (R3 @ c).dot(Vector((s, 0, 0))))
    return front, outw


def ring(obj, bone, y0, y1, hx, hz, mat, M, bevel=True, faces=None):
    box(obj, bone, -hx, hx, y0, y1, -hz, hz, mat, M=M, bevel=bevel, faces=faces)


def octo(obj, bone, y0, y1, r, mat, M):
    box(obj, bone, -r, r, y0, y1, -r, r, mat, M=M, bevel=True)
    box(obj, bone, -r * 0.92, r * 0.92, y0 + 0.2, y1 - 0.2, -r * 0.92, r * 0.92, mat, M=M @ Matrix.Rotation(math.radians(45), 4, "Y"), bevel=True)


def face_glyph(obj, bone, g, M, front, half, ymid, px=1.0, mat="PurpleEnergy"):
    """Glyph on the local face whose outward axis is `front` (unit local X or Z), centred at ymid along the bone."""
    up = Vector((0, -1, 0))                     # toward the bone head
    out = Vector(front)
    right = up.cross(out)
    w, h = len(g[0]) * px, len(g) * px
    origin = out * half + Vector((0, ymid, 0)) - right * (w / 2) + up * (h / 2)
    L.glyph(B, RUNES, bone, g, tuple(origin), tuple(right), tuple(up), tuple(out), px=px, depth=0.6, mat=mat, M=M)


def finger(obj, bone, length, r, claw):
    M = MB(bone)
    ring(obj, bone, 0, length * 0.55, r, r, "DarkSteel", M, bevel=False)
    ring(ARMOR_ARMS, bone, length * 0.45, length * 0.62, r + 0.3, r + 0.3, "WeatheredBronze", M, bevel=False)
    ring(obj, bone, length * 0.55, length, r * 0.85, r * 0.85, "AncientDarkIron", M, bevel=False)
    if claw:
        ring(RUNES, bone, length, length + 2.8, r * 0.6, r * 0.6, "MagentaFragments", M, bevel=False)


for s, S in ((1, "L"), (-1, "R")):
    # ---------------- main (lower) arm: heavy, bronze-jointed, layered plates
    obj = ARM[S]
    Mu, Mf, Mh = MB(f"upperarm_{S}"), MB(f"forearm_{S}"), MB(f"hand_{S}")
    fu, ou = axes(f"upperarm_{S}", s)
    octo(ARMOR_ARMS, f"upperarm_{S}", -3.5, 3.5, 7.5, "WeatheredBronze", Mu)
    ring(obj, f"upperarm_{S}", 0, 20, 5.5, 5.5, "DarkSteel", Mu, bevel=False)
    ring(ARMOR_ARMS, f"upperarm_{S}", 1.5, 8.5, 7.2, 7.2, "AncientDarkIron", Mu)
    ring(ARMOR_ARMS, f"upperarm_{S}", 7, 13.5, 7.7, 7.7, "AncientDarkIron", Mu, faces={"front": "RuneStone"})
    ring(ARMOR_ARMS, f"upperarm_{S}", 12, 18.5, 8.2, 8.2, "WeatheredBronze", Mu)
    ring(RUNES, f"upperarm_{S}", 14.4, 15.6, 8.5, 8.5, "CyanRunes", Mu, bevel=False)
    face_glyph(RUNES, f"upperarm_{S}", G[1], Mu, fu, 7.7, 10.2, px=0.85)
    octo(ARMOR_ARMS, f"forearm_{S}", -3.5, 3.5, 7.2, "WeatheredBronze", Mf)
    box(ARMOR_ARMS, f"forearm_{S}", -9, 9, -1.3, 1.3, -1.3, 1.3, "DarkSteel", M=Mf)                       # elbow hinge pin
    box(ARMOR_ARMS, f"forearm_{S}", -1.3, 1.3, -1.3, 1.3, -9, 9, "DarkSteel", M=Mf)
    ring(obj, f"forearm_{S}", 0, 18, 5, 5, "DarkSteel", Mf, bevel=False)
    ring(ARMOR_ARMS, f"forearm_{S}", 1, 6.5, 7.6, 7.6, "AncientDarkIron", Mf)
    ring(ARMOR_ARMS, f"forearm_{S}", 6, 16, 8.8, 8.8, "RuneStone", Mf)
    ring(RUNES, f"forearm_{S}", 10.2, 11.4, 9.1, 9.1, "PurpleEnergy", Mf, bevel=False)
    ring(ARMOR_ARMS, f"forearm_{S}", 15.5, 19.5, 7.4, 7.4, "WeatheredBronze", Mf)
    for k in (-1, 1):                                                  # chipped bracer edges
        box(ARMOR_ARMS, f"forearm_{S}", 7.5 * k - 1.2, 7.5 * k + 1.2, 5.6, 7, 7.6, 9.4, "CorruptedStone", M=Mf)
    fh, oh = axes(f"hand_{S}", s)
    spread_is_x = abs((rig.data.bones[f"hand_{S}"].matrix_local.to_3x3() @ Vector((1, 0, 0))).y) > 0.5
    hx, hz = (6.8, 5.2) if spread_is_x else (5.2, 6.8)
    box(obj, f"hand_{S}", -hx, hx, 0, 9.5, -hz, hz, "AncientDarkIron", M=Mh, bevel=True)
    box(ARMOR_ARMS, f"hand_{S}", -hx - 0.3, hx + 0.3, 6, 10, -hz - 0.3, hz + 0.3, "WeatheredBronze", M=Mh, bevel=True)
    if S == "L":
        face_glyph(RUNES, f"hand_{S}", G[1], Mh, oh, hz if abs(oh.z) > 0.5 else hx, 4.8, px=0.95, mat="CyanRunes")
    for k in range(3):
        finger(obj, f"finger{k + 1}_{S}", 8, 1.6, False)
    finger(obj, f"thumb_{S}", 5, 1.6, False)

    # ---------------- additional (upper) arm: slimmer segmented steel, claws, purple fire
    obj = XARM[S]
    Mu, Mf, Mh = MB(f"upperarm_extra_{S}"), MB(f"forearm_extra_{S}"), MB(f"hand_extra_{S}")
    fu, ou = axes(f"upperarm_extra_{S}", s)
    octo(ARMOR_ARMS, f"upperarm_extra_{S}", -3, 3, 6.5, "DarkSteel", Mu)
    ring(obj, f"upperarm_extra_{S}", 0, 22, 4.5, 4.5, "DarkSteel", Mu, bevel=False)
    for i in range(4):
        y0 = 1 + i * 5
        ring(ARMOR_ARMS, f"upperarm_extra_{S}", y0, y0 + 6, 6.2 - i * 0.25, 6.2 - i * 0.25,
             "AncientDarkIron" if i % 2 == 0 else "DarkSteel", Mu)
    ring(RUNES, f"upperarm_extra_{S}", 19.2, 20.2, 6.1, 6.1, "CyanRunes", Mu, bevel=False)
    for k in (-1, 1):                                                  # mechanical elbow discs
        box(ARMOR_ARMS, f"forearm_extra_{S}", 4.5 * k - (1.5 if k > 0 else -1.5) * 0, 4.5 * k + 2.5 * k, -3.2, 3.2, -3.2, 3.2,
            "WeatheredBronze", M=Mf, bevel=True)
    box(ARMOR_ARMS, f"forearm_extra_{S}", -5, 5, -2.6, 2.6, -4.2, 4.2, "DarkSteel", M=Mf @ Matrix.Rotation(math.radians(45), 4, "Y"), bevel=True)
    ring(obj, f"forearm_extra_{S}", 0, 20, 4, 4, "DarkSteel", Mf, bevel=False)
    ring(ARMOR_ARMS, f"forearm_extra_{S}", 2, 7.5, 5.3, 5.3, "DarkSteel", Mf)
    ring(ARMOR_ARMS, f"forearm_extra_{S}", 7, 18, 6.6, 6.6, "AncientDarkIron", Mf, faces={"front": "RuneStone"})
    face_glyph(RUNES, f"forearm_extra_{S}", G[0], Mf, axes(f"forearm_extra_{S}", s)[0], 6.6, 12.5, px=0.9)
    ring(ARMOR_ARMS, f"forearm_extra_{S}", 17.5, 21, 6, 6, "WeatheredBronze", Mf)
    spread_is_x = abs((rig.data.bones[f"hand_extra_{S}"].matrix_local.to_3x3() @ Vector((1, 0, 0))).y) > 0.5
    hx, hz = (6, 4.4) if spread_is_x else (4.4, 6)
    box(obj, f"hand_extra_{S}", -hx, hx, 0, 9, -hz, hz, "DarkSteel", M=Mh, bevel=True)
    box(ARMOR_ARMS, f"hand_extra_{S}", -hx - 0.3, hx + 0.3, 1, 5, -hz - 0.3, hz + 0.3, "AncientDarkIron", M=Mh, bevel=True)
    for k in range(3):
        finger(obj, f"finger{k + 1}_extra_{S}", 9, 1.35, True)
    finger(obj, f"thumb_extra_{S}", 5.5, 1.35, True)
    # purple fire held above the claw
    Mfx = MB(f"fx_fire_{S}")
    fr = random.Random(900 + s)
    for (y0, y1, w) in ((-2, 3, 6.5), (3, 7, 5.4), (7, 11, 4.2), (11, 15, 2.8), (15, 18, 1.5)):
        box(VFX, f"fx_fire_{S}", -w, w, y0, y1, -w * 0.55, w * 0.55, "FireEnergy", M=Mfx)
        box(VFX, f"fx_fire_{S}", -w * 0.55, w * 0.55, y0 + 0.5, y1 + 0.5, -w, w, "FireEnergy", M=Mfx)
    # voxel energy orb held in the claw (second reference)
    for (a, b) in ((4.2, 2.4), (3.4, 3.4), (2.4, 4.2)):
        box(VFX, f"fx_fire_{S}", -a, a, 4.5 - b, 4.5 + b, -a, a, "MagentaFragments", M=Mfx)
        box(VFX, f"fx_fire_{S}", -b, b, 4.5 - a, 4.5 + a, -b, b, "MagentaFragments", M=Mfx)
    box(VFX, f"fx_fire_{S}", -2.2, 2.2, 2.3, 6.7, -2.2, 2.2, "EyeGlow", M=Mfx)
    for i in range(10):
        p = Vector((fr.uniform(-8, 8), fr.uniform(-2, 20), fr.uniform(-8, 8))); q = fr.uniform(0.6, 1.3)
        box(VFX, f"fx_fire_{S}", p.x - q, p.x + q, p.y - q, p.y + q, p.z - q, p.z + q, "FireEnergy" if i % 3 else "MagentaFragments", M=Mfx)

# ================================================================ WEAPON (rune greatsword)
Mw = MB("weapon")
W = WEAPON
box(W, "weapon", -3, 3, -14, -9.5, -3, 3, "WeatheredBronze", M=Mw, bevel=True)
box(RUNES, "weapon", -1.2, 1.2, -15.3, -14, -1.2, 1.2, "MagentaFragments", M=Mw)
box(W, "weapon", -1.7, 1.7, -9.5, 5, -1.7, 1.7, "AncientDarkIron", M=Mw)
for y in (-8, -5, -2, 1, 3.8):
    box(W, "weapon", -1.95, 1.95, y, y + 1.1, -1.95, 1.95, "WeatheredBronze", M=Mw)
box(W, "weapon", -13, 13, 5, 9, -3, 3, "DarkSteel", M=Mw, bevel=True)
for k in (-1, 1):
    box(W, "weapon", *sorted((12.5 * k, 15.5 * k)), 3.5, 11, -3.6, 3.6, "WeatheredBronze", M=Mw, bevel=True)
box(W, "weapon", -3.2, 3.2, 4.5, 9.5, -3.4, 3.4, "RuneStone", M=Mw, bevel=True)
for zf in (1, -1):
    L.glyph(B, RUNES, "weapon", G[3], (-1.75, 9.2, 3.4 * zf), (zf, 0, 0), (0, 1, 0), (0, 0, zf), px=0.7, depth=0.4, mat="CyanRunes", M=Mw)
box(W, "weapon", -5, 5, 9, 14, -1.6, 1.6, "DarkSteel", M=Mw, bevel=True)
for (y0, y1, w) in ((14, 62, 5.6), (62, 72, 4.4), (72, 79, 3.2), (79, 84, 2), (84, 87, 0.8)):
    box(W, "weapon", -w, w, y0, y1, -1.3, 1.3, "DarkSteel", M=Mw)
er = random.Random(66)
for k in (-1, 1):                                                       # chipped bright edges with gaps
    y = 14.5
    while y < 61:
        seg = er.uniform(3, 9)
        box(W, "weapon", *sorted((5.6 * k, 6.9 * k)), y, min(61.5, y + seg), -0.75, 0.75, "DarkSteel", M=Mw)
        y += seg + er.uniform(0.8, 2.6)
box(W, "weapon", -1.2, 1.2, 14, 76, -1.75, 1.75, "AncientDarkIron", M=Mw)
box(RUNES, "weapon", -0.35, 0.35, 16, 74, -1.95, 1.95, "MagentaFragments", M=Mw)
for zf in (1, -1):
    for i, y in enumerate((22, 36, 50)):
        for xc in (-3.6, 3.6):
            L.glyph(B, RUNES, "weapon", G[(i + (xc > 0)) % 6], (xc - 1.9 * zf, y + 2.7, 1.3 * zf), (zf * 0.76, 0, 0), (0, 0.76, 0), (0, 0, zf), px=0.76, depth=0.35,
                    mat="CyanRunes" if (i + (xc > 0)) % 2 else "PurpleEnergy", M=Mw)

objs = B.finish(rig, C)
print("OBJECTS", [(o.name, len(o.data.polygons)) for o in objs])
print("TOTAL_FACES", sum(len(o.data.polygons) for o in objs))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage1.blend"))

# rest-pose check renders
SC.setup(fog=False, arena=False)
SC.shot(os.path.join(OUT, "stage1_rest_front.png"), (0, -19, 4.5), (0, 0, 4.3), 32, (900, 1000))
SC.shot(os.path.join(OUT, "stage1_rest_34.png"), (-12, -14, 6), (0, 0, 4.3), 32, (900, 1000))
print("STAGE1_OK")
