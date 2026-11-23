# Armour, heart and greatsword for the Withered Sentinel knight. Executed inside sk_build.py (uses block/sym/COLS).
# Right side is authored with x < 0 and mirrored to the left by R2L / the per-side loop.
# Design goals (from the reference): massive layered black plate, jagged scale-like edges, huge spiked pauldrons,
# a tall broken crown, V-shaped torso with an open ribcage showing the heart, long tassets, a colossal sword.


def tooth(bone, c, s, mat="obsidian", rot=(0, 45, 0), coll="Sentinel_Armor"):
    """A small block turned 45 degrees so a corner points out: the jagged, broken-edge look."""
    return block(bone, c, (s, s, s), mat, rot, coll)


def spike(bone, base, h, w=1.5, rot=(0, 0, 0), mat="obsidian", tip="gunmetal"):
    """A tall spike: shaft + diamond tip, rising from `base` along its rotated +Z."""
    R = Euler(tuple(math.radians(a) for a in rot), "XYZ").to_matrix()
    up = R @ Vector((0, 0, 1))
    c = Vector(base) + up * (h / 2)
    block(bone, tuple(c), (w, w * 0.9, h), mat, rot)
    t = Vector(base) + up * (h + 0.1)
    block(bone, tuple(t), (w * 0.62, w * 0.62, w * 0.62), tip, (rot[0], rot[1], rot[2] + 45))


# ---------------- pelvis: hips, belt, long layered front + back tassets
block("pelvis", (0, 0.5, 40), (13.5, 9, 6), "obsidian")
block("pelvis", (0, 0.5, 43.4), (15.2, 10.2, 1.8), "gunmetal")
block("pelvis", (0, -5.3, 42.4), (4.0, 1.0, 3.4), "rune")
for i, (z, w, rx, m) in enumerate(((37.0, 9.4, 8, "obsidian"), (32.4, 8.4, 6, "rune"), (27.8, 7.0, 4, "obsidian"))):
    block("pelvis", (0, -5.2 - 0.45 * i, z), (w, 1.4, 5.4), m, (rx, 0, 0))
    for sx in (-1, 1):
        tooth("pelvis", (sx * (w / 2 - 0.2), -5.2 - 0.45 * i, z - 2.6), 1.3)
block("pelvis", (0, -6.5, 24.4), (3.6, 1.2, 3.6), "obsidian", (4, 45, 0))
block("pelvis", (0, 5.6, 37.0), (12.6, 1.4, 7.6), "obsidian", (-9, 0, 0))
block("pelvis", (0, 6.4, 31.4), (9.6, 1.2, 5.4), "obsidian", (-12, 0, 0))
for sx in (-3.6, 0, 3.6):
    tooth("pelvis", (sx, 6.6, 28.6), 1.3)
# ---------------- spine: narrow segmented waist
for z, w, d in ((45.6, 11.4, 8.0), (48.1, 12.6, 8.6), (50.6, 14.0, 9.4)):
    block("spine", (0, 0.2, z), (w, d, 2.4), "obsidian")
    block("spine", (0, 0.2, z + 1.35), (w - 0.6, d - 0.6, 0.5), "gunmetal")
    tooth("spine", (0, 0.2 + d / 2 + 0.2, z), 1.2)
# ---------------- chest: V-shaped shell around the open ribcage
block("chest", (0, 4.6, 58.4), (21.0, 3.0, 13.0), "obsidian")
block("chest", (0, 2.8, 58.0), (16.0, 0.6, 10.5), "cavity", coll="Sentinel_Body")
block("chest", (0, -0.6, 53.4), (15.0, 7.0, 1.0), "cavity", coll="Sentinel_Body")
for sx in (-1, 1):
    block("chest", (sx * 10.2, 0.2, 58.2), (2.8, 10.0, 12.4), "obsidian", (0, sx * 7, 0))       # flanks, flared at the top
    block("chest", (sx * 6.8, -4.4, 62.2), (8.6, 2.2, 3.6), "obsidian", (-14, 0, sx * 6))       # breast plates
    block("chest", (sx * 7.8, -4.6, 56.2), (4.0, 1.6, 7.6), "rune", (0, 0, sx * 10))            # plates framing the ribs
    tooth("chest", (sx * 9.6, -4.8, 52.8), 1.4)
    for k, z in enumerate((55.0, 58.5, 62.0)):                                                 # scale teeth on the flanks
        tooth("chest", (sx * 11.7, 0.2, z), 1.3, rot=(0, 45, 0))
block("chest", (0, 0.4, 63.6), (21.4, 10.4, 2.8), "obsidian")
block("chest", (0, 0.0, 52.6), (17.0, 10.0, 1.6), "gunmetal")
for i, z in enumerate((54.6, 56.9, 59.2, 61.3)):                                               # ribs, open in the middle
    w = 6.8 - 0.4 * abs(i - 1.5)
    for sx in (-1, 1):
        block("chest", (sx * (1.9 + w / 2), -4.5, z), (w, 1.5, 1.4), "iron", (0, -sx * 12, sx * 9))
        tooth("chest", (sx * 1.9, -4.6, z - 0.5), 0.9, "iron")
block("chest", (0, -4.8, 62.9), (4.4, 1.5, 2.2), "gunmetal")
block("chest", (0, -5.0, 61.4), (1.6, 1.0, 1.6), "gunmetal", (0, 45, 0))
for z in (55.0, 58.4, 61.8):                                                                   # spine ridge spikes on the back
    block("chest", (0, 6.6, z), (1.4, 2.8, 1.4), "obsidian", (-35, 0, 0))
# ---------------- heart (own bones) + additive glow shell
block("heart", (0, -1.4, 57.6), (4.2, 3.2, 4.4), "heart", coll="Sentinel_Heart", name="Heart_Ventricles")
block("heart", (-1.2, -1.4, 60.2), (2.0, 2.6, 1.8), "heart", coll="Sentinel_Heart", name="Heart_Atrium_R")
block("heart", (1.2, -1.4, 60.2), (2.0, 2.6, 1.8), "heart", coll="Sentinel_Heart", name="Heart_Atrium_L")
block("heart", (0, -1.4, 55.0), (2.0, 2.2, 1.4), "heart", coll="Sentinel_Heart", name="Heart_Apex")
block("heart", (0.4, -0.8, 61.6), (1.2, 1.2, 1.6), "heart", coll="Sentinel_Heart", name="Heart_Aorta")
block("heart_glow", (0, -1.4, 58.0), (6.4, 4.6, 7.4), "heart_glow", coll="Sentinel_Heart", name="Heart_GlowShell")
# ---------------- neck + helmet (a void where the face should be) + broken crown
block("neck", (0, 0, 65.6), (9, 9, 3), "obsidian")
block("neck", (0, 0.5, 66.8), (5, 5, 3.6), "void", coll="Sentinel_Body")
block("head", (0, 3.9, 73.2), (10.4, 1.8, 10.4), "obsidian")
for sx in (-1, 1):
    block("head", (sx * 4.8, 0.0, 73.2), (1.6, 9.4, 10.4), "obsidian")
    block("head", (sx * 5.9, -1.6, 71.2), (1.2, 6.0, 5.0), "obsidian", (0, sx * 14, 0))        # flared jaw guards
    tooth("head", (sx * 6.5, -1.6, 68.6), 1.2)
    block("head", (sx * 2.7, -4.6, 76.7), (5.4, 1.4, 2.2), "obsidian", (0, 0, -sx * 9))         # angry brow
    block("head", (sx * 3.5, -4.5, 71.4), (3.2, 1.4, 8.0), "obsidian", (0, 0, sx * 6))          # cheek guards
    block("head", (sx * 1.6, -3.95, 74.1), (1.7, 0.3, 0.7), "eye", (0, 0, -sx * 12), coll="Sentinel_Body", name=f"Eye_{'L' if sx > 0 else 'R'}")
    tooth("head", (sx * 5.6, 0.0, 68.4), 1.3)
block("head", (0, 0.2, 78.4), (10.8, 9.8, 1.6), "obsidian")
block("head", (0, -4.9, 74.0), (1.2, 1.2, 8.6), "gunmetal")                                # central nasal ridge
block("head", (0, -4.6, 67.8), (3.0, 1.6, 3.0), "obsidian", (0, 45, 0))                       # chin point
block("head", (0, -0.2, 72.4), (7.6, 7.8, 8.2), "void", coll="Sentinel_Body")
block("head", (0, 0.2, 79.8), (11.8, 11.2, 1.6), "gunmetal")                                  # crown band
for (x, y, h, ry, rx) in ((0, -5.2, 10.0, 0, -6), (-2.9, -5.2, 7.0, -8, -6), (2.9, -5.2, 7.0, 8, -6),
                          (-5.4, -4.7, 6.0, -18, -5), (5.4, -4.7, 6.0, 18, -5), (-5.6, -1.4, 7.4, -16, 0),
                          (5.6, -1.4, 7.4, 16, 0), (-5.6, 2.2, 5.2, -16, 4), (5.6, 2.2, 5.2, 16, 4),
                          (0, 5.1, 8.4, 0, 9), (-3.4, 5.0, 6.0, -10, 9), (3.4, 5.0, 6.0, 10, 9)):
    spike("head", (x, y, 80.4), h, 1.5, (rx, ry, 0))
for (x, y) in ((-1.5, -5.2), (1.5, -5.2), (-4.2, -5.0), (4.2, -5.0), (-5.8, 0.4), (5.8, 0.4), (-1.7, 5.2), (1.7, 5.2)):
    tooth("head", (x, y, 81.1), 1.1, "gunmetal")
# ---------------- per side: pauldron, arm, gauntlet, fingers, leg
for S, s in SIDE.items():
    X = lambda v: v if S == "R" else -v
    sg = 1 if S == "R" else -1                         # rotation sign: mirror flips y/z rotations
    R2 = lambda r: (r[0], r[1] * sg, r[2] * sg)
    U, F, Hn = f"upperarm_{S}", f"forearm_{S}", f"hand_{S}"
    block(f"clavicle_{S}", (X(-9.0), 0, 62.4), (4.2, 6.4, 2.8), "gunmetal")
    # pauldron: four stepped plates, a gunmetal rim, a jagged hem and a crest of spikes
    block(U, (X(-15.4), 0, 63.4), (12.6, 12.8, 4.4), "obsidian", R2((0, -12, 0)))
    block(U, (X(-15.4), 0, 61.1), (13.0, 13.2, 0.7), "gunmetal", R2((0, -12, 0)))
    block(U, (X(-18.0), 0, 59.4), (8.8, 12.2, 3.4), "obsidian", R2((0, -28, 0)))
    block(U, (X(-19.8), 0, 56.4), (6.6, 11.6, 3.2), "rune", R2((0, -40, 0)))
    block(U, (X(-20.8), 0, 53.6), (4.6, 10.6, 3.0), "obsidian", R2((0, -52, 0)))
    for y in (-4.4, -2.2, 0.0, 2.2, 4.4):
        tooth(U, (X(-21.9), y, 51.9), 1.4)
    for (sx, sy, h, a) in ((-13.2, -3.8, 4.4, -14), (-15.8, -1.9, 6.4, -24), (-18.2, 0.0, 7.6, -34),
                           (-15.8, 1.9, 6.0, -24), (-13.2, 3.8, 4.2, -14)):
        spike(U, (X(sx), sy, 65.0), h, 1.6, R2((0, a, 0)))
    block(U, (X(-14.0), 0, 53.0), (6.6, 6.6, 10.0), "obsidian")                       # rerebrace
    block(U, (X(-17.5), 0, 53.0), (1.0, 3.2, 9.0), "gunmetal")
    block(U, (X(-14.0), 1.8, 47.4), (5.4, 4.2, 4.6), "obsidian")                      # couter + spur
    block(U, (X(-14.0), 4.6, 47.8), (1.6, 3.6, 1.6), "obsidian", (-30, 0, 0))
    block(F, (X(-14.0), 0, 41.8), (6.6, 6.6, 9.0), "obsidian")                       # vambrace
    block(F, (X(-14.0), 0, 37.3), (7.8, 7.8, 2.2), "gunmetal")
    for y in (-3.0, -1.0, 1.0, 3.0):
        tooth(F, (X(-14.0) + 0, y, 36.0), 1.1, rot=(45, 0, 0))
    for z in (44.4, 41.6, 38.8):
        spike(F, (X(-17.2), 0, z), 2.6, 1.1, R2((0, -48, 0)))
    block(Hn, (X(-14.0), 0, 32.4), (4.8, 6.2, 5.2), "obsidian")                       # gauntlet
    block(Hn, (X(-14.0), 0, 29.8), (5.0, 6.4, 1.2), "gunmetal")
    for y in (-1.8, 0.0, 1.8):
        tooth(Hn, (X(-16.6), y, 30.6), 0.9, rot=(0, 0, 45))
    for fi, fy in (("index", -1.7), ("middle", 0.0), ("ring", 1.7)):
        block(f"{fi}1_{S}", (X(-14.2), fy, 28.65), (1.6, 1.6, 2.7), "obsidian")
        block(f"{fi}2_{S}", (X(-14.2), fy, 26.05), (1.45, 1.45, 2.5), "gunmetal")
        block(f"{fi}2_{S}", (X(-14.2), fy - 0.25, 24.6), (0.9, 0.9, 1.1), "obsidian", (20, 0, 0))
    block(f"thumb1_{S}", (X(-12.45), -2.9, 31.8), (1.7, 1.7, 2.6), "obsidian", (24, 0, 0))
    block(f"thumb2_{S}", (X(-12.2), -3.7, 29.6), (1.45, 1.45, 2.2), "gunmetal", (24, 0, 0))
    # legs: cuisse with three rows of scale plates, side tasset, spiked poleyn, layered greave, armoured sabaton
    T, Sh, Ft, To = f"thigh_{S}", f"shin_{S}", f"foot_{S}", f"toe_{S}"
    block(T, (X(-6.2), 0, 30.6), (8.2, 8.4, 13.2), "obsidian")
    for i, (z, w, m) in enumerate(((35.6, 8.8, "obsidian"), (31.6, 8.4, "rune"), (27.6, 8.0, "obsidian"))):
        block(T, (X(-6.2), -4.6 - 0.2 * i, z), (w, 1.4, 4.8), m, (14 - 2 * i, 0, 0))
        tooth(T, (X(-6.2 - w / 2 + 0.6), -4.8 - 0.2 * i, z - 2.4), 1.1, rot=(90, 45, 0))
    block(T, (X(-10.6), 0, 33.0), (1.4, 7.6, 10.0), "obsidian", R2((0, 8, 0)))
    for y in (-2.6, 0.0, 2.6):
        tooth(T, (X(-11.2), y, 28.0), 1.2, rot=(45, 0, 0))
    block(Sh, (X(-6.2), -4.2, 21.6), (6.6, 2.6, 5.4), "gunmetal")
    block(Sh, (X(-6.2), -6.2, 23.0), (1.8, 3.4, 1.8), "obsidian", (35, 0, 0))
    block(Sh, (X(-9.6), -1.4, 21.6), (1.2, 4.6, 4.6), "obsidian", (45, 0, 0))
    block(Sh, (X(-6.2), 0, 14.0), (7.2, 7.6, 13.0), "obsidian")
    for i, z in enumerate((18.0, 14.0, 10.0)):
        block(Sh, (X(-6.2), -4.1 - 0.2 * i, z), (7.4 - 0.4 * i, 1.2, 4.0), "rune" if i == 1 else "obsidian", (10, 0, 0))
        tooth(Sh, (X(-6.2), -4.3 - 0.2 * i, z - 2.1), 1.0, rot=(90, 45, 0))
    for z in (17.0, 12.6):
        spike(Sh, (X(-9.6), 0, z), 3.0, 1.0, R2((0, -38, 0)))
    block(Sh, (X(-6.2), 3.9, 15.0), (6.2, 1.4, 10.0), "obsidian")
    block(Ft, (X(-6.2), 0, 6.5), (7.8, 8.0, 3.0), "gunmetal")
    block(Ft, (X(-6.2), -1.0, 2.6), (8.0, 9.6, 5.2), "obsidian")
    block(Ft, (X(-6.2), -3.2, 5.6), (7.0, 4.0, 1.2), "obsidian", (15, 0, 0))
    block(Ft, (X(-6.2), 5.3, 3.0), (1.6, 2.6, 1.6), "obsidian", (-30, 0, 0))
    block(To, (X(-6.2), -8.2, 1.9), (7.0, 5.2, 3.8), "obsidian")
    block(To, (X(-6.2), -11.0, 1.4), (3.4, 3.4, 2.4), "gunmetal", (0, 0, 45))

# ---------------- the greatsword (bone 'sword'; at rest the blade points straight forward, flat facing up)
gx, gy, gz = GRIP


def sw(s, size, mat, rot=(0, 0, 0), dx=0.0, dz=0.0, name=None):
    """s = distance along the blade from the right-hand grip point (+ toward the tip)."""
    return block("sword", (gx + dx, gy - s, gz + dz), size, mat, rot, coll="Sentinel_Weapon", name=name)


sw(-4.0, (2.0, 12.0, 2.0), "grip", name="Sword_Grip")
for s in (-9.6, -5.0, 0.6):
    sw(s, (2.4, 0.6, 2.4), "gunmetal", name="Sword_GripRing")
sw(-11.6, (3.8, 3.0, 3.8), "gunmetal", name="Sword_Pommel")
sw(-14.0, (1.4, 2.4, 1.4), "obsidian", (0, 45, 0), name="Sword_PommelSpike")
sw(2.8, (20.0, 2.6, 3.6), "obsidian", name="Sword_Guard")
sw(2.8, (4.0, 3.2, 4.2), "rune", name="Sword_GuardCore")
for dx in (-10.6, 10.6):
    sw(4.4, (2.0, 3.6, 2.0), "obsidian", (0, 0, 40 if dx > 0 else -40), dx=dx, name="Sword_GuardHook")
    sw(1.2, (1.4, 1.4, 1.4), "gunmetal", (0, 45, 0), dx=dx * 0.7, name="Sword_GuardStud")
for (s0, s1, w) in ((4.0, 18.0, 8.4), (18.0, 34.0, 7.6), (34.0, 46.0, 6.6), (46.0, 52.0, 4.8), (52.0, 56.0, 2.6)):
    sw((s0 + s1) / 2, (w, s1 - s0, 1.6), "blade", name="Sword_Blade")
sw(29.0, (1.2, 48.0, 2.2), "blade", name="Sword_Ridge")                                       # raised spine down the flats
for i, s in enumerate((8, 13, 19, 25, 31, 38, 43)):                                      # broken, jagged edges
    side = -1 if i % 2 == 0 else 1
    w = 8.4 if s < 18 else (7.6 if s < 34 else 6.6)
    sw(s, (1.6, 1.6, 1.4), "blade", (0, 0, 45), dx=side * (w / 2 + 0.25), name="Sword_Tooth")
GRIP_L_S = -7.0          # where the off hand holds the grip (distance along the blade axis)
SWORD_LEN = 56.0
