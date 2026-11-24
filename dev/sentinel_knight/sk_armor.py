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
block("pelvis", (0, -5.7, 43.4), (4.2, 1.6, 3.8), "tooth", name="Skull_Buckle")                  # a skull for a buckle
# ---------------- tassets (own bones: they swing clear of the legs)
block("tasset_F", (0, -5.8, 39.0), (8.0, 1.4, 2.6), "trim", (6, 0, 0))                           # band under the belt
block("tasset_F", (0, -6.6, 30.0), (5.0, 0.7, 14.0), "cloth", (4, 0, 0), name="Tabard")           # the purple tabard (narrow)
for j, (dx, h_) in enumerate(((-1.7, 2.2), (-0.6, 3.6), (0.6, 4.4), (1.7, 2.6))):                    # pointed, ragged end
    block("tasset_F", (dx, -7.0, 23.0 - h_ / 2), (1.15, 0.6, h_), "cloth", (4, 0, 0), name=f"Tabard_Hem_{j}")
block("tasset_F", (0, -7.0, 35.8), (5.6, 0.8, 1.0), "trim", name="Tabard_Bar")
for i, (z, w) in enumerate(((37.2, 12.4), (32.0, 10.6))):
    block("tasset_B", (0, 6.0 + 0.5 * i, z), (w, 1.4, 5.6), "plate", (-8, 0, 0))
for S, sx in (("L", 1), ("R", -1)):
    for i, z in enumerate((37.6, 33.8, 30.0)):
        if i == 0:                                                     # one short hip plate per side
            block(f"tasset_{S}", (sx * 9.4, 0.0, z), (1.4, 7.6, 4.0), "plate", (0, sx * -10, 0))
# ---------------- spine: layered faulds
for z, w, d in ((45.6, 11.6, 8.2), (48.1, 12.8, 8.8), (50.6, 14.2, 9.6)):
    block("spine", (0, 0.2, z), (w, d, 2.4), "plate")
    block("spine", (0, 0.2, z + 1.35), (w - 0.6, d - 0.6, 0.5), "trim")
# ---------------- chest: angular breastplate with glowing tracery, a central slit over the heart
block("chest", (0, 4.6, 58.4), (21.0, 3.0, 13.0), "plate")
block("chest", (0, 2.8, 58.0), (14.0, 0.6, 10.5), "cavity", coll="Sentinel_Body")
block("chest", (0, -0.6, 53.4), (12.0, 7.0, 1.0), "cavity", coll="Sentinel_Body")
for sx in (-1, 1):
    block("chest", (sx * 10.0, 0.2, 58.4), (2.8, 10.0, 12.4), "plate", (0, sx * 15, 0))           # flanks, sloping in to the waist
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
block("chest", (0, 0.2, 65.4), (12.6, 11.2, 3.4), "plate", name="Gorget")                          # gorget under the helm
block("chest", (0, 0.2, 66.9), (13.2, 11.8, 0.8), "trim", name="Gorget_Rim")
# heavy chains hanging in a U from each shoulder down to the belt
for sx in (-1, 1):
    pts = [Vector((sx * 10.8, -6.6, 61.0)), Vector((sx * 9.6, -7.4, 54.0)), Vector((sx * 7.4, -7.2, 48.0)), Vector((sx * 5.0, -6.9, 45.2))]
    k = 0
    for a_, b_ in zip(pts, pts[1:]):
        n = max(2, int((b_ - a_).length / 1.7))
        for t_ in range(n):
            p_ = a_.lerp(b_, (t_ + 0.5) / n); d_ = (b_ - a_).normalized()
            sz = (1.8, 0.6, 1.1) if k % 2 == 0 else (1.8, 1.1, 0.6)
            block("chest", tuple(p_), sz, "iron", (0, math.degrees(math.atan2(-d_.z, d_.x)), 0), name=f"Chain_{sx}_{k}")
            k += 1
# ---------------- heart (own bones) + additive glow shell, behind the slit
block("heart", (0, -1.4, 57.6), (4.2, 3.2, 4.4), "heart", coll="Sentinel_Heart", name="Heart_Ventricles")
block("heart", (-1.2, -1.4, 60.2), (2.0, 2.6, 1.8), "heart", coll="Sentinel_Heart", name="Heart_Atrium_R")
block("heart", (1.2, -1.4, 60.2), (2.0, 2.6, 1.8), "heart", coll="Sentinel_Heart", name="Heart_Atrium_L")
block("heart", (0, -1.4, 55.0), (2.0, 2.2, 1.4), "heart", coll="Sentinel_Heart", name="Heart_Apex")
block("heart", (0.4, -0.8, 61.6), (1.2, 1.2, 1.6), "heart", coll="Sentinel_Heart", name="Heart_Aorta")
block("heart_glow", (0, -2.0, 58.0), (5.6, 4.0, 7.2), "heart_glow", coll="Sentinel_Heart", name="Heart_GlowShell")
# ---------------- executioner's great-helm (v14, built to the user's front/back pictures): a big square helm on a high
# collar, a tall stepped crest, a wide crown of bronze-tipped spikes, angled burning eyes, a barred grille
block("neck", (0, 0, 65.4), (8.6, 8.6, 3.0), "plate")
block("neck", (0, 0.5, 66.8), (5, 5, 3.6), "void", coll="Sentinel_Body")
block("head", (0, 0.4, 73.8), (13.2, 12.4, 12.4), "plate", name="Helm_Shell")
block("head", (0, 0.4, 80.6), (14.2, 13.4, 1.4), "trim", name="Helm_CrownRim")
block("head", (0, 0.4, 81.8), (11.6, 11.0, 1.4), "plate", name="Helm_Top")
block("head", (0, 0.0, 83.6), (7.0, 7.6, 2.4), "plate", name="Helm_CrestBase")                    # stepped crest
block("head", (0, -0.2, 87.6), (3.4, 4.0, 6.0), "plate", name="Helm_Crest")
block("head", (0, -0.2, 91.4), (2.6, 3.2, 2.0), "plate", name="Helm_CrestTop")
for sx in (-1, 1):
    block("head", (sx * 2.6, -0.2, 85.6), (1.8, 3.4, 3.6), "plate", name=f"Helm_CrestStep_{sx}")
for (x, y, tilt, hgt) in ((-6.4, -5.8, (-16, -16, 0), 4.6), (6.4, -5.8, (-16, 16, 0), 4.6), (-6.8, 0.4, (0, -22, 0), 4.0), (6.8, 0.4, (0, 22, 0), 4.0),
                          (-6.4, 6.6, (16, -16, 0), 3.6), (6.4, 6.6, (16, 16, 0), 3.6), (-3.2, -6.4, (-18, -6, 0), 3.8), (3.2, -6.4, (-18, 6, 0), 3.8)):
    spike("head", (x, y, 81.2), hgt, 1.5, tilt, mat="plate", tip="trim")                         # crown of spikes
block("head", (0, -6.4, 77.6), (13.8, 1.8, 2.4), "plate", name="Helm_Brow")
block("head", (0, -6.0, 74.4), (11.0, 0.8, 3.0), "void", coll="Sentinel_Body", name="Helm_VisorDark")
for sx in (-1, 1):
    block("head", (sx * 2.9, -6.3, 74.5), (3.8, 0.6, 1.6), "eye", (0, 0, sx * -12), coll="Sentinel_Body",
          name=f"Eye_{'L' if sx > 0 else 'R'}")
    block("head", (sx * 6.7, -0.2, 73.4), (1.6, 11.6, 10.6), "plate", name=f"Helm_Cheek_{sx}")
block("head", (0, -6.4, 70.0), (12.8, 1.4, 5.4), "plate", name="Helm_Face")
block("head", (0, -7.1, 72.0), (1.6, 0.8, 5.0), "plate", name="Helm_Nose")                           # central rib of the face
for k in (-2, -1, 1, 2):
    block("head", (k * 1.6, -7.2, 69.4), (0.8, 0.8, 4.2), "iron", name=f"Helm_Grille_{k}")
block("head", (0, -0.6, 67.4), (10.6, 10.4, 1.4), "plate", name="Helm_Chin")
block("head", (0, -0.4, 73.4), (9.6, 9.6, 9.6), "void", coll="Sentinel_Body")
# ---------------- shoulders, arms, hands, legs (v14, to the user's pictures; right authored, mirrored)
def band(bone, c, size, rot=(0, 0, 0), name=None):
    """A bronze band: slightly larger than the plate it wraps."""
    return block(bone, c, size, "trim", rot, name=name)


for S, s in SIDE.items():
    X = lambda v: v if S == "R" else -v
    sg = 1 if S == "R" else -1
    R2 = lambda r: (r[0], r[1] * sg, r[2] * sg)
    U, F, Hn = f"upperarm_{S}", f"forearm_{S}", f"hand_{S}"
    block(f"clavicle_{S}", (X(-9.0), 0, 62.4), (4.2, 6.4, 2.8), "trim")
    # pauldron: a tall box covering the shoulder and upper arm (as high as the helm), bronze bands top and bottom,
    # a stepped cap with spikes; two skulls on the left one
    rot_p = R2((0, -8, 0))
    cx_ = X(-16.6)
    block(U, (cx_ + X(-0.8), 0.0, 59.4), (13.2, 15.4, 10.4), "rune", rot_p, name=f"Pauldron_{S}_Main")      # outer wall
    band(U, (cx_ + X(-0.8), 0.0, 54.4), (14.0, 16.2, 1.3), rot_p, name=f"Pauldron_{S}_Rim0")
    block(U, (cx_ + X(1.4), 0.0, 65.2), (12.6, 14.6, 3.6), "plate", rot_p, name=f"Pauldron_{S}_Step1")      # stepped up and in
    band(U, (cx_ + X(1.4), 0.0, 63.6), (13.4, 15.4, 1.1), rot_p, name=f"Pauldron_{S}_Rim1")
    block(U, (cx_ + X(2.8), 0.0, 68.4), (9.6, 12.0, 3.0), "plate", rot_p, name=f"Pauldron_{S}_Cap")
    block(U, (cx_ + X(3.8), 0.0, 70.8), (6.4, 9.0, 2.0), "plate", rot_p, name=f"Pauldron_{S}_Top")
    for (dx_, dy_, dz_, sz_) in ((-6.6, -4.2, 61.0, (2.4, 5.6, 6.0)), (-6.6, 4.2, 61.0, (2.4, 5.6, 6.0)), (-5.8, 0.0, 66.4, (2.6, 7.0, 3.0)),
                                 (-1.6, -7.6, 60.2, (6.4, 1.6, 6.4)), (-1.6, 7.6, 60.2, (6.4, 1.6, 6.4)), (1.4, -6.8, 65.6, (5.0, 1.4, 3.0))):
        block(U, (cx_ + X(dx_), dy_, dz_), sz_, "plate", rot_p, name=f"Pauldron_{S}_Chunk")          # rough stacked edges
    block(U, (cx_ + X(-0.6), 0.0, 53.4), (12.4, 14.0, 2.4), "plate", R2((0, -12, 0)), name=f"Pauldron_{S}_Lame")
    for (dx_, y_, h_) in ((-2.8, -4.0, 5.2), (-2.8, 4.0, 4.4), (2.4, 0.0, 3.8)):
        spike(U, (cx_ + X(dx_ * 0.9 + 1.6), y_, 70.6), h_, 1.8, R2((-y_ * 3, -8 - dx_ * 3, 0)), mat="plate", tip="trim")
    if S == "L":
        for k, dz_ in enumerate((0.0, 0.2)):
            block(U, (cx_ + X(-1.0 + 4.0 * k), -7.8, 67.2 + dz_), (3.4, 2.8, 3.2), "tooth", name=f"Skull_Pauldron_{k}")
    # thick banded arms
    block(U, (X(-14.0), 0, 52.6), (10.0, 10.0, 9.0), "rune", name=f"Rerebrace_{S}")
    band(U, (X(-14.0), 0, 48.4), (10.6, 10.6, 1.1))
    block(U, (X(-14.0), 0.8, 46.6), (9.4, 8.8, 3.6), "plate", name=f"Couter_{S}")                # elbow
    band(F, (X(-14.0), 0, 45.2), (11.0, 11.0, 1.2))
    block(F, (X(-14.0), 0, 40.8), (10.4, 10.4, 8.4), "rune", name=f"Vambrace_{S}")
    band(F, (X(-14.0), 0, 36.6), (11.0, 11.0, 1.3))
    block(Hn, (X(-14.0), 0, 32.4), (8.6, 9.2, 6.4), "plate", name=f"Gauntlet_{S}")              # big gauntlet
    band(Hn, (X(-14.0), 0, 29.4), (9.0, 9.6, 1.3), name=f"Gauntlet_{S}_Knuckles")
    for fi, fy in (("index", -1.7), ("middle", 0.0), ("ring", 1.7)):
        block(f"{fi}1_{S}", (X(-14.2), fy, 28.65), (1.8, 1.8, 2.7), "plate")
        block(f"{fi}2_{S}", (X(-14.2), fy, 26.05), (1.6, 1.6, 2.5), "plate")
    block(f"thumb1_{S}", (X(-12.45), -2.9, 31.8), (1.9, 1.9, 2.6), "plate", (24, 0, 0))
    block(f"thumb2_{S}", (X(-12.2), -3.7, 29.6), (1.6, 1.6, 2.2), "plate", (24, 0, 0))
    # legs: thick banded thighs and shins, layered knees, big blocky boots with bronze caps
    T, Sh, Ft, To = f"thigh_{S}", f"shin_{S}", f"foot_{S}", f"toe_{S}"
    band(T, (X(-6.2), 0, 37.0), (11.6, 11.6, 1.2))
    block(T, (X(-6.2), 0, 30.4), (11.0, 11.0, 12.6), "rune", name=f"Cuisse_{S}")
    band(T, (X(-6.2), 0, 24.4), (11.6, 11.6, 1.2))
    block(Sh, (X(-6.2), -5.3, 21.4), (10.6, 2.0, 7.0), "plate", name=f"Knee_{S}_0")
    block(Sh, (X(-6.2), -6.4, 21.4), (8.0, 1.0, 5.0), "rune", name=f"Knee_{S}_1")
    band(Sh, (X(-6.2), 0, 18.6), (11.2, 11.2, 1.2))
    block(Sh, (X(-6.2), 0, 13.6), (10.6, 10.6, 9.4), "rune", name=f"Greave_{S}")
    band(Sh, (X(-6.2), 0, 8.4), (11.2, 11.2, 1.2))
    block(Ft, (X(-6.2), -0.6, 3.6), (11.4, 13.4, 6.8), "plate", name=f"Boot_{S}")
    band(Ft, (X(-6.2), -0.6, 7.3), (12.0, 14.0, 1.0))
    block(To, (X(-6.2), -9.4, 2.2), (10.4, 5.6, 4.4), "plate", name=f"BootToe_{S}")
    band(To, (X(-6.2), -12.0, 1.6), (10.8, 1.2, 3.0), name=f"BootToeCap_{S}")
    band(Ft, (X(-6.2), 5.8, 1.4), (11.2, 1.2, 2.8), name=f"BootHeel_{S}")
# ---------------- the cape: three panels, three segments each, tattered hem; bronze clasps at the shoulders
block("cape_root", (0, 5.9, 63.6), (21.0, 1.6, 2.2), "cloth")
for sx in (-1, 1):
    block("cape_root", (sx * 9.6, 5.4, 63.4), (2.2, 1.0, 2.2), "bronze", (0, 45, 0))
for s, x in (("L", 8.6), ("M", 0.0), ("R", -8.6)):
    w = 15.0 if s == "M" else 10.6                                          # v14: the middle panel carries the banner
    lean = 0
    bottom = 6.8 + (2.2 if s != "M" else 0)
    side = 0 if s == "M" else (1 if s == "L" else -1)
    for k, (z0, z1) in enumerate(((62.6, 43.4), (43.6, 24.4), (24.6, bottom))):
        flare = (1.0, 1.18, 1.4)[k] if s != "M" else (1.0, 1.06, 1.12)[k]          # v15: the cloak flares out
        xo = x + side * (0.0, 2.2, 5.4)[k]
        block(f"cape_{s}{k + 1}", (xo, 6.6 + (0.35 if s == "M" else 0.0), (z0 + z1) / 2), (w * flare, 0.9, z0 - z1), "cloth",
              (0, 0, -side * (0, 5, 9)[k]))
    wb = w * ((1.4 if s != "M" else 1.12)); xb = x + side * 5.4
    for j in range(6):                                                         # long ragged strips at the hem
        hx = xb - wb / 2 + wb * (j + 0.5) / 6
        L = (4.2, 2.0, 5.6, 1.4, 3.6, 2.6)[(j + (0 if s == "M" else 2)) % 6]
        block(f"cape_{s}3", (hx, 6.6, bottom - L / 2 + 0.3), (wb / 6 - 0.2, 0.8, L), "cloth", (0, 0, -side * 9), name=f"CapeRag_{s}_{j}")

# ---------------- the longsword (bone 'sword'; at rest the blade points straight forward, flat facing up)
gx, gy, gz = GRIP


def sw(s, size, mat, rot=(0, 0, 0), dx=0.0, dz=0.0, name=None):
    return block("sword", (gx + dx, gy - s, gz + dz), size, mat, rot, coll="Sentinel_Weapon", name=name)


sw(-4.0, (2.0, 12.0, 2.0), "grip", name="Sword_Grip")
for s_ in (-9.6, -5.0, 0.6):
    sw(s_, (2.4, 0.6, 2.4), "trim", name="Sword_GripRing")
sw(-11.6, (3.6, 3.6, 3.6), "trim", (0, 45, 0), name="Sword_Pommel")
sw(-11.6, (1.6, 3.8, 1.6), "energy", (0, 45, 0), name="Sword_PommelGem")
# crossguard: a heavy bronze bar with a purple gem ring at its heart, swept tips
sw(2.6, (14.0, 2.6, 2.8), "trim", name="Sword_Guard")
sw(2.6, (4.2, 3.0, 3.6), "plate", name="Sword_GuardCore")
sw(2.6, (2.6, 0.8, 2.6), "energy", (0, 0, 45), dz=0.0, name="Sword_GuardGem")
for sx in (-1, 1):
    sw(3.6, (3.2, 2.2, 2.2), "trim", (0, 0, sx * 35), dx=sx * 7.8, name="Sword_GuardTip")
# the blade: broad, dark, almost as long as he is tall; jagged crystal edges burning purple
for (s0, s1, w) in ((4.4, 18.0, 8.4), (18.0, 32.0, 8.0), (32.0, 44.0, 7.2), (44.0, 51.0, 5.6), (51.0, 55.0, 3.6), (55.0, 57.5, 1.8)):
    sw((s0 + s1) / 2, (w, s1 - s0, 1.6), "blade", name="Sword_Blade")
sw(29.0, (1.2, 46.0, 1.8), "energy", name="Sword_Core")
for k, s_ in enumerate([7.0 + 3.6 * i for i in range(12)]):                     # crystal teeth along both edges
    w_here = 8.4 if s_ < 18 else 8.0 if s_ < 32 else 7.2 if s_ < 44 else 5.6
    big = 2.3 if k % 2 == 0 else 1.6
    for sx in (-1, 1):
        sw(s_ + (0.8 if sx > 0 else 0.0), (big, big, 1.3), "energy", (0, 0, 45), dx=sx * (w_here / 2 + 0.1), name=f"Sword_Shard_{k}_{sx}")
GRIP_L_S = -7.0
SWORD_LEN = 57.0
