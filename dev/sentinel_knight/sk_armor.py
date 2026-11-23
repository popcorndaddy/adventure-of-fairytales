# Armour, cape, heart and sword for the Withered Sentinel (v3, after the user's dark-knight reference):
# a tall pointed great-helm with burning purple eye slits, angular layered plate, a purple scarf and a long tattered
# cape, glowing purple tracery across the breastplate around the heart, flared bladed vambraces, layered tassets,
# and a long two-handed sword with an ornate crossguard and a glowing purple core.
# Executed inside sk_build.py (block/sym/COLS/SIDE/GRIP available). Right side authored with x < 0.
# Materials (painted in sk_export.py from the Gatekeeper texture set): plate, trim, rune, emblem, cloth, bronze,
# blade, energy, grip, iron, void, cavity, heart, heart_glow, eye.


def tooth(bone, c, s, mat="plate", rot=(0, 45, 0), coll="Sentinel_Armor"):
    return block(bone, c, (s, s, s), mat, rot, coll)


def spike(bone, base, h, w=1.5, rot=(0, 0, 0), mat="plate", tip="trim"):
    R = Euler(tuple(math.radians(a) for a in rot), "XYZ").to_matrix()
    up = R @ Vector((0, 0, 1))
    block(bone, tuple(Vector(base) + up * (h / 2)), (w, w * 0.9, h), mat, rot)
    block(bone, tuple(Vector(base) + up * (h + 0.1)), (w * 0.62, w * 0.62, w * 0.62), tip, (rot[0], rot[1], rot[2] + 45))


def oct_disc(bone, c, d, t, mat, rot=(0, 0, 0), coll="Sentinel_Armor", name=None):
    """A round(ish) disc: a square and the same square turned 45 deg about its own normal (an octagon)."""
    R = Euler(tuple(math.radians(a) for a in rot), "XYZ").to_matrix()
    R45 = R @ Euler((0, 0, math.radians(45)), "XYZ").to_matrix()
    e45 = tuple(math.degrees(a) for a in R45.to_euler("XYZ"))
    block(bone, c, (d, d, t), mat, rot, coll, name)
    block(bone, c, (d * 0.83, d * 0.83, t * 0.98), mat, e45, coll, (name + "_45") if name else None)


def dome(bone, base, axis_rot, layers, mat="plate", rim="trim", name=None):
    """A stepped dome: stacked octagonal layers along the local normal, shrinking towards the top, with a rim."""
    R = Euler(tuple(math.radians(a) for a in axis_rot), "XYZ").to_matrix()
    n = R @ Vector((0, 0, 1))
    if rim:
        d0, t0 = layers[0]
        oct_disc(bone, tuple(Vector(base) - n * 0.2), d0 * 1.08, 0.7, rim, axis_rot)
    h = 0.0
    for i, (d, t) in enumerate(layers):
        oct_disc(bone, tuple(Vector(base) + n * (h + t / 2)), d, t, mat, axis_rot, name=(f"{name}_{i}" if name else None))
        h += t * 0.92


# ---------------- pelvis core, belt with a bronze buckle
block("pelvis", (0, 0.5, 40.2), (13.6, 9.2, 6.2), "plate")
block("pelvis", (0, 0.5, 43.4), (15.4, 10.4, 1.9), "trim")
oct_disc("pelvis", (0, -5.5, 43.4), 4.0, 0.9, "bronze", (90, 0, 0), name="Buckle")                 # round medallion buckle
block("pelvis", (0, -6.1, 43.4), (1.2, 0.5, 1.2), "energy", (0, 45, 0))
# ---------------- tassets (own bones: they swing clear of the legs)
for i, (z, w, m) in enumerate(((37.4, 9.6, "plate"), (32.8, 8.6, "rune"), (28.2, 7.4, "plate"))):
    block("tasset_F", (0, -5.6 - 0.4 * i, z), (w, 1.4, 5.4), m, (6, 0, 0))
    for sx in (-1, 1):
        tooth("tasset_F", (sx * (w / 2 - 0.3), -5.6 - 0.4 * i, z - 2.6), 1.3)
block("tasset_F", (0, -6.8, 24.6), (3.8, 1.2, 3.8), "trim", (4, 45, 0))
for i, (z, w) in enumerate(((37.2, 12.4), (32.0, 10.6))):
    block("tasset_B", (0, 6.0 + 0.5 * i, z), (w, 1.4, 5.6), "plate", (-8, 0, 0))
for S, sx in (("L", 1), ("R", -1)):
    for i, z in enumerate((37.6, 33.8, 30.0)):
        block(f"tasset_{S}", (sx * (9.6 + 0.35 * i), 0.0, z), (1.4, 8.6 - 0.6 * i, 4.6), "plate" if i != 1 else "rune", (0, sx * -10, 0))
        tooth(f"tasset_{S}", (sx * (9.9 + 0.35 * i), -3.6 + 0.3 * i, z - 2.2), 1.1)
# ---------------- spine: layered faulds
for z, w, d in ((45.6, 11.6, 8.2), (48.1, 12.8, 8.8), (50.6, 14.2, 9.6)):
    block("spine", (0, 0.2, z), (w, d, 2.4), "plate")
    block("spine", (0, 0.2, z + 1.35), (w - 0.6, d - 0.6, 0.5), "trim")
# ---------------- chest: angular breastplate with glowing tracery, a central slit over the heart
block("chest", (0, 4.6, 58.4), (21.0, 3.0, 13.0), "plate")
block("chest", (0, 2.8, 58.0), (14.0, 0.6, 10.5), "cavity", coll="Sentinel_Body")
block("chest", (0, -0.6, 53.4), (12.0, 7.0, 1.0), "cavity", coll="Sentinel_Body")
for sx in (-1, 1):
    block("chest", (sx * 10.2, 0.2, 58.2), (2.8, 10.0, 12.4), "plate", (0, sx * 7, 0))            # flanks
    block("chest", (sx * 5.6, -4.7, 59.4), (7.6, 2.4, 9.6), "emblem", (-4, 0, sx * -6))          # breastplate halves
    block("chest", (sx * 6.2, -5.3, 63.0), (8.0, 1.8, 2.8), "plate", (-18, 0, sx * -8))          # upper bevel
    block("chest", (sx * 2.15, -5.7, 58.6), (0.9, 1.2, 10.0), "trim")                            # slit edges
    block("chest", (sx * 7.6, -4.4, 53.9), (5.0, 1.8, 2.4), "plate", (8, 0, sx * 14))            # lower bevel
    tooth("chest", (sx * 9.8, -4.6, 52.8), 1.4)
for z in (54.4, 56.8, 59.2, 61.6):                                                              # ribs inside the slit
    block("chest", (0, -4.0, z), (3.4, 1.0, 0.8), "iron")
block("chest", (0, 0.4, 63.6), (21.4, 10.4, 2.8), "plate")
block("chest", (0, 0.0, 52.6), (17.0, 10.0, 1.6), "trim")
# purple scarf wrapped at the neck, a fold hanging over the chest
block("chest", (0, 0.2, 65.4), (12.6, 11.2, 3.4), "cloth")
block("chest", (-1.8, -5.6, 61.9), (5.8, 1.2, 4.8), "cloth", (12, 0, 10))
block("chest", (3.0, -5.4, 60.4), (2.8, 1.0, 6.6), "cloth", (6, 0, -6))
# ---------------- heart (own bones) + additive glow shell, behind the slit
block("heart", (0, -1.4, 57.6), (4.2, 3.2, 4.4), "heart", coll="Sentinel_Heart", name="Heart_Ventricles")
block("heart", (-1.2, -1.4, 60.2), (2.0, 2.6, 1.8), "heart", coll="Sentinel_Heart", name="Heart_Atrium_R")
block("heart", (1.2, -1.4, 60.2), (2.0, 2.6, 1.8), "heart", coll="Sentinel_Heart", name="Heart_Atrium_L")
block("heart", (0, -1.4, 55.0), (2.0, 2.2, 1.4), "heart", coll="Sentinel_Heart", name="Heart_Apex")
block("heart", (0.4, -0.8, 61.6), (1.2, 1.2, 1.6), "heart", coll="Sentinel_Heart", name="Heart_Aorta")
block("heart_glow", (0, -2.0, 58.0), (5.6, 4.0, 7.2), "heart_glow", coll="Sentinel_Heart", name="Heart_GlowShell")
# ---------------- war helm (v8): a rounded power-armour helm, battle-scarred. Domed crown, heavy brow over angled
# glowing lenses, a jutting rebreather with a grille and angled cheek vents, a mohawk crest, a light purple stripe.
block("neck", (0, 0, 65.4), (8.6, 8.6, 3.0), "plate")
block("neck", (0, 0.5, 66.8), (5, 5, 3.6), "void", coll="Sentinel_Body")
oct_disc("head", (0, 0.4, 72.6), 10.4, 9.4, "plate", name="Helm_Shell")                         # round skull of the helm
dome("head", (0, 0.4, 77.2), (0, 0, 0), [(9.8, 1.6), (8.4, 1.4), (6.2, 1.2)], rim=None, name="Helm_Dome")
block("head", (0, 0.4, 77.4), (1.4, 10.8, 3.4), "accent", name="Helm_Stripe")                  # light purple stripe
block("head", (0, -4.9, 74.2), (9.6, 1.6, 4.6), "plate", name="Helm_Face")                      # faceplate
block("head", (0, -5.5, 76.6), (10.2, 1.8, 1.6), "accent", (-22, 0, 0), name="Helm_Brow")        # heavy brow
for sx in (-1, 1):
    block("head", (sx * 2.4, -5.8, 74.6), (3.2, 0.6, 1.8), "eye", (-6, 0, sx * -18), coll="Sentinel_Body",
          name=f"Eye_{'L' if sx > 0 else 'R'}")                                                      # angled lenses
    block("head", (sx * 2.4, -5.65, 74.6), (3.8, 0.4, 2.4), "accent", (-6, 0, sx * -18), name=f"Lens_Rim_{sx}")
    block("head", (sx * 3.7, -5.6, 69.8), (2.2, 2.6, 3.2), "accent", (0, 0, sx * 28), name=f"Cheek_Vent_{sx}")
    block("head", (sx * 5.4, -1.2, 71.0), (1.2, 6.4, 5.8), "plate", (0, sx * 8, 0), name=f"Helm_Cheek_{sx}")
block("head", (0, -6.6, 69.6), (4.4, 3.0, 3.8), "plate", name="Rebreather")                    # the snout
block("head", (0, -8.2, 69.4), (3.4, 0.8, 3.0), "iron", name="Grille")                          # its grille
block("head", (0, -1.0, 67.4), (7.6, 7.2, 1.4), "plate", name="Helm_Chin")
for k, (y, h) in enumerate(((-3.2, 2.6), (0.0, 3.4), (3.2, 2.8))):                            # mohawk crest
    block("head", (0, y, 81.6 + h / 2 - 1.0), (1.4, 3.4, h), "accent", name=f"Crest_{k}")
block("head", (0, -0.4, 72.8), (7.6, 7.6, 8.6), "void", coll="Sentinel_Body")
# ---------------- shoulders, arms, hands, legs (right authored, mirrored)
for S, s in SIDE.items():
    X = lambda v: v if S == "R" else -v
    sg = 1 if S == "R" else -1
    R2 = lambda r: (r[0], r[1] * sg, r[2] * sg)
    U, F, Hn = f"upperarm_{S}", f"forearm_{S}", f"hand_{S}"
    block(f"clavicle_{S}", (X(-9.0), 0, 62.4), (4.2, 6.4, 2.8), "trim")
    # domed pauldron (v8): a big rounded shell tipped out over the shoulder, a gold rim, a glowing vent band below
    dome(U, (X(-16.0), 0, 60.6), R2((0, -18, 0)), [(14.0, 2.4), (12.6, 1.8), (10.6, 1.6), (7.8, 1.4), (4.6, 1.0)], name=f"Pauldron_{S}")
    block(U, (X(-19.4), 0, 58.2), (5.6, 12.0, 2.6), "rune", R2((0, -40, 0)))
    block(U, (X(-20.6), 0, 55.8), (4.2, 10.8, 2.4), "plate", R2((0, -55, 0)))
    block(U, (X(-14.0), 0, 53.0), (6.6, 6.6, 10.0), "plate")                       # rerebrace
    block(U, (X(-17.5), 0, 53.0), (1.0, 3.2, 9.0), "trim")
    block(U, (X(-14.0), 1.8, 47.4), (5.4, 4.2, 4.6), "plate")                      # couter
    dome(U, (X(-16.6), 1.4, 47.4), R2((0, -90, 0)), [(4.6, 0.9), (3.2, 0.8)], name=f"Couter_{S}")   # round elbow cop
    block(F, (X(-14.0), 0, 41.8), (6.8, 6.8, 9.0), "plate")                        # vambrace
    block(F, (X(-14.0), 0, 37.3), (7.8, 7.8, 2.2), "trim")
    for i, z in enumerate((44.6, 42.0, 39.4)):                                       # bladed fins sweeping back
        block(F, (X(-17.9), 1.2 + 0.6 * i, z), (0.8, 5.0 - 0.8 * i, 1.6), "trim", R2((0, -20, 0)))
        tooth(F, (X(-18.2), 3.8 + 0.4 * i, z + 0.4), 1.1, rot=(45, 0, 0))
    block(Hn, (X(-14.0), 0, 32.4), (4.8, 6.2, 5.2), "plate")                       # gauntlet
    block(Hn, (X(-14.0), 0, 29.8), (5.0, 6.4, 1.2), "trim")
    for y in (-1.8, 0.0, 1.8):
        tooth(Hn, (X(-16.6), y, 30.6), 0.9, rot=(0, 0, 45))
    for fi, fy in (("index", -1.7), ("middle", 0.0), ("ring", 1.7)):
        block(f"{fi}1_{S}", (X(-14.2), fy, 28.65), (1.6, 1.6, 2.7), "plate")
        block(f"{fi}2_{S}", (X(-14.2), fy, 26.05), (1.45, 1.45, 2.5), "trim")
        block(f"{fi}2_{S}", (X(-14.2), fy - 0.25, 24.6), (0.9, 0.9, 1.1), "plate", (20, 0, 0))
    block(f"thumb1_{S}", (X(-12.45), -2.9, 31.8), (1.7, 1.7, 2.6), "plate", (24, 0, 0))
    block(f"thumb2_{S}", (X(-12.2), -3.7, 29.6), (1.45, 1.45, 2.2), "trim", (24, 0, 0))
    # legs: cuisse with three scale rows, spiked poleyn with a fan, layered greave, pointed sabaton
    T, Sh, Ft, To = f"thigh_{S}", f"shin_{S}", f"foot_{S}", f"toe_{S}"
    block(T, (X(-6.2), 0, 30.6), (8.2, 8.4, 13.2), "plate")
    for i, (z, w, m) in enumerate(((35.0, 8.8, "plate"), (31.0, 8.4, "rune"), (27.0, 8.0, "plate"))):
        block(T, (X(-6.2), -4.6 - 0.2 * i, z), (w, 1.4, 4.8), m, (14 - 2 * i, 0, 0))
    dome(Sh, (X(-6.2), -3.8, 21.8), (90, 0, 0), [(7.6, 1.2), (6.4, 1.0), (5.0, 1.2)], name=f"Knee_{S}")  # round knee cop
    block(Sh, (X(-6.2), 0, 14.0), (7.2, 7.6, 13.0), "plate")
    for i, z in enumerate((18.0, 14.0, 10.0)):
        block(Sh, (X(-6.2), -4.1 - 0.2 * i, z), (7.4 - 0.4 * i, 1.2, 4.0), "rune" if i == 1 else "plate", (10, 0, 0))
        tooth(Sh, (X(-6.2), -4.3 - 0.2 * i, z - 2.1), 1.0, rot=(90, 45, 0))
    block(Sh, (X(-9.9), 0, 15.0), (0.8, 5.0, 9.0), "trim", R2((0, -8, 0)))
    block(Sh, (X(-6.2), 3.9, 15.0), (6.2, 1.4, 10.0), "plate")
    block(Ft, (X(-6.2), 0, 6.5), (7.8, 8.0, 3.0), "trim")
    block(Ft, (X(-6.2), -1.0, 2.6), (8.0, 9.6, 5.2), "plate")
    block(Ft, (X(-6.2), -3.2, 5.6), (7.0, 4.0, 1.2), "plate", (15, 0, 0))
    block(Ft, (X(-6.2), 5.3, 3.0), (1.6, 2.6, 1.6), "plate", (-30, 0, 0))
    block(To, (X(-6.2), -8.2, 1.9), (7.0, 5.2, 3.8), "plate")
    block(To, (X(-6.2), -11.0, 1.4), (3.4, 3.4, 2.4), "trim", (0, 0, 45))
# ---------------- the cape: three panels, three segments each, tattered hem; bronze clasps at the shoulders
block("cape_root", (0, 5.9, 63.6), (21.0, 1.6, 2.2), "cloth")
for sx in (-1, 1):
    block("cape_root", (sx * 9.6, 5.4, 63.4), (2.2, 1.0, 2.2), "bronze", (0, 45, 0))
for s, x in (("L", 8.6), ("M", 0.0), ("R", -8.6)):
    w = 9.6 if s == "M" else 10.0                                           # panels overlap: one cloak, no gaps
    lean = 0
    bottom = 6.8 + (2.2 if s != "M" else 0)
    for k, (z0, z1) in enumerate(((62.6, 43.4), (43.6, 24.4), (24.6, bottom))):
        block(f"cape_{s}{k + 1}", (x, 6.6 + (0.0 if s == "M" else 0.35), (z0 + z1) / 2), (w, 0.9, z0 - z1), "cloth", (0, 0, lean))
    for j in range(3):                                                         # tattered hem
        hx = x - w / 2 + w * (j + 0.5) / 3
        hz = bottom - (1.2 if j % 2 == 0 else 0.4)
        block(f"cape_{s}3", (hx, 6.6, hz), (w / 3 - 0.4, 0.8, 1.6 if j % 2 == 0 else 0.8), "cloth", (0, 0, 10 if j == 1 else -8))

# ---------------- the longsword (bone 'sword'; at rest the blade points straight forward, flat facing up)
gx, gy, gz = GRIP


def sw(s, size, mat, rot=(0, 0, 0), dx=0.0, dz=0.0, name=None):
    return block("sword", (gx + dx, gy - s, gz + dz), size, mat, rot, coll="Sentinel_Weapon", name=name)


sw(-4.0, (1.9, 12.0, 1.9), "grip", name="Sword_Grip")
for s in (-9.6, -5.0, 0.6):
    sw(s, (2.3, 0.6, 2.3), "trim", name="Sword_GripRing")
sw(-11.6, (3.4, 3.4, 3.4), "trim", (0, 45, 0), name="Sword_Pommel")
sw(-11.6, (1.4, 3.6, 1.4), "energy", (0, 45, 0), name="Sword_PommelGem")
sw(-14.2, (1.2, 2.6, 1.2), "trim", (0, 45, 0), name="Sword_PommelSpike")
sw(2.6, (5.0, 2.6, 3.6), "plate", name="Sword_GuardCore")
sw(2.6, (1.6, 1.0, 1.6), "energy", (0, 45, 0), dz=1.9, name="Sword_GuardGem")
for sx in (-1, 1):                                                             # quillons curving toward the blade
    sw(3.0, (6.0, 1.8, 1.8), "trim", (0, 0, sx * 10), dx=sx * 5.0, name="Sword_Quillon")
    sw(4.6, (3.6, 1.6, 1.6), "trim", (0, 0, sx * 38), dx=sx * 8.9, name="Sword_QuillonTip")
    sw(5.8, (1.0, 1.0, 1.0), "plate", (0, 45, 0), dx=sx * 10.2, name="Sword_QuillonBarb")
sw(5.0, (3.0, 2.0, 2.0), "plate", name="Sword_Ricasso")
for (s0, s1, w) in ((5.0, 20.0, 5.8), (20.0, 36.0, 5.4), (36.0, 48.0, 4.8), (48.0, 54.0, 3.4), (54.0, 57.0, 1.8)):
    sw((s0 + s1) / 2, (w, s1 - s0, 1.3), "blade", name="Sword_Blade")
sw(30.5, (1.5, 49.0, 1.7), "energy", name="Sword_Core")                       # the glowing purple core
GRIP_L_S = -7.0
SWORD_LEN = 57.0
