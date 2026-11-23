"""The Withered King, model v4: a lanky skeletal king in rotted, verdigris plate - built from the concept art.
Blockbench units (8 px = 1 block in game after the entity's 2x scale), y up, faces -z, +x = his right.

The body is a real skeleton you can see through: skull and jaw, a neck of separate vertebrae, an open ribcage (ribs,
sternum, spine, a soul glowing inside), a bare lumbar spine, pelvis, bone limbs with knobbed joints and skeletal hands
with separate finger bones. Armour is layered on top where the art has it: pauldrons, a bracer, a spiked vambrace,
belt and tassets, cuisses, knee cops and greaves, sabatons; barnacle clusters and hanging moss everywhere; a hooded,
torn cloak. Built for animation: zero rest rotations, every piece belongs to the bone it moves with, joints are knobs
centred on their pivots, armour keeps clear of the torso and head, the cloak hangs from its own bones."""
import math, random, zlib
import numpy as np
BONES = []; CUBES = []

def bone(name, parent, pivot, rot=(0, 0, 0)):
    BONES.append(dict(name=name, parent=parent, pivot=[float(v) for v in pivot], rot=list(rot)))

def cube(b, name, frm, size, mat, flags=(), rot=None, pivot=None):
    CUBES.append(dict(bone=b, name=name, frm=[float(v) for v in frm], size=[float(v) for v in size], mat=mat, flags=set(flags),
                      rot=list(rot) if rot else None, pivot=[float(v) for v in pivot] if pivot else None))

def box(s, b, name, c, size, mat, flags=(), rot=None, pivot=None):
    """centre-based cube; s=-1 mirrors a right-side (+x) part to the left"""
    c = (c[0] * s, c[1], c[2])
    if rot: rot = (rot[0], rot[1] * s, rot[2] * s)
    if pivot: pivot = (pivot[0] * s, pivot[1], pivot[2])
    elif rot: pivot = c
    frm = [c[k] - size[k] / 2 for k in range(3)]
    cube(b, name, frm, size, mat, flags, rot, pivot)

def R(name): return random.Random(zlib.crc32(name.encode()))

def barnacles(s, b, name, c, normal, n=3, spread=1.2):
    """a small cluster of barnacles on a surface; `normal` = which way the surface faces (axis, sign)"""
    r = R(name); ax, sg = normal
    for i in range(n):
        sz = r.uniform(0.7, 1.15)
        p = [c[0] + r.uniform(-spread, spread), c[1] + r.uniform(-spread, spread), c[2] + r.uniform(-spread, spread)]
        p[ax] = c[ax] + sg * sz * 0.35
        box(s, b, f'{name}{i}', tuple(p), (sz, sz, sz), 'bone_dark' if i % 3 == 2 else 'bone')

def moss(s, b, name, top, n=3, ln=(2.5, 5.5), spread=1.5, axis=0):
    """strands of moss hanging from an edge (spread along x or z)"""
    r = R(name)
    for i in range(n):
        L = r.uniform(*ln); o = (i - (n - 1) / 2) * spread / max(1, n - 1) * 2 + r.uniform(-0.2, 0.2)
        c = [top[0], top[1] - L / 2, top[2]]; c[axis] += o
        box(s, b, f'{name}{i}', tuple(c), (0.45, L, 0.45), 'vine')

def rag(s, b, name, c, w, h, d, n, mat='cloth', flags=('ragged',), axis=0):
    """a torn cloth panel: strips of uneven length hanging from one top edge (width along x, or z if axis=2)"""
    r = R(name); sw = w / n
    for i in range(n):
        hh = h * r.uniform(0.72, 1.0); o = -w / 2 + sw * (i + 0.5)
        cc = [c[0], c[1] + h / 2 - hh / 2, c[2]]; cc[axis] += o
        size = [sw + 0.05, hh, d] if axis == 0 else [d, hh, sw + 0.05]
        box(s, b, f'{name}{i}', tuple(cc), tuple(size), mat, set(flags) | ({'holes'} if i % 3 == 1 else set()))

# ================================================================== skeleton (rest = neutral standing pose)
HIP_Y, KNEE_Y, ANKLE_Y = 36.0, 20.5, 5.0
SHO_Y, ELB_Y, WRI_Y = 56.0, 42.0, 28.5
LX, AX = 4.6, 10.6
bone('root', None, (0, 0, 0))
bone('body', 'root', (0, HIP_Y, 0))
bone('skirt', 'body', (0, 38.5, 0))
bone('waist', 'body', (0, 40.0, 0.6))
bone('chest', 'waist', (0, 46.0, 0.6))
bone('neck', 'chest', (0, 57.8, 0.2))
bone('head', 'neck', (0, 60.6, 0.0))
bone('jaw', 'head', (0, 62.2, -0.9))
bone('crown', 'head', (0, 68.0, -0.6))
bone('hood_drape', 'head', (0, 63.0, 4.2))
bone('cape', 'chest', (0, 58.0, 5.2))
for side, s in (('right', 1), ('left', -1)):
    bone(f'{side}_clavicle', 'chest', (2.2 * s, 56.6, -1.2))
    bone(f'{side}_arm', f'{side}_clavicle', (AX * s, SHO_Y, 0.2))
    bone(f'{side}_forearm', f'{side}_arm', ((AX + 0.3) * s, ELB_Y, 0.8))
    bone(f'{side}_hand', f'{side}_forearm', (AX * s, WRI_Y, 0.0))
    bone(f'{side}_leg', 'body', (LX * s, HIP_Y, 0.4))
    bone(f'{side}_shin', f'{side}_leg', (LX * s, KNEE_Y, -0.6))
    bone(f'{side}_foot', f'{side}_shin', (LX * s, ANKLE_Y, 0.4))
FZ = (-1.5, -0.5, 0.5, 1.5)
for k, zc in enumerate(FZ):
    bone(f'left_finger{k}', 'left_hand', (-AX, 25.0, zc))
bone('left_thumb', 'left_hand', (-AX + 1.1, 26.6, -1.6))
bone('right_fingers', 'right_hand', (AX - 1.0, 25.4, 0.0))
bone('right_thumb', 'right_hand', (AX - 0.8, 26.4, -1.7))
GRIP = (AX + 0.3, 25.0, 0.0)                    # the greatsword's grip point: through the right fist
bone('sword', 'right_hand', GRIP, (-122, 0, 0))   # sword space: blade along -z, flat normal +x; rest: point down a little back
bone('tabard_front', 'skirt', (0, 37.6, -4.8))
bone('tabard_back', 'skirt', (0, 38.0, 4.0))
bone('tabard_right', 'skirt', (6.8, 38.0, -1.2))
bone('tabard_left', 'skirt', (-6.8, 38.0, -1.2))
bone('drape_left', 'chest', (-5.4, 57.4, -3.6))
bone('drape_right', 'chest', (5.4, 57.4, -3.6))
bone('banner', 'body', (-5.6, 38.4, -3.0))

# ================================================================== legs: cuisses, knee cops, greaves, sabatons over bone
for side, s in (('right', 1), ('left', -1)):
    Lg, S, F = f'{side}_leg', f'{side}_shin', f'{side}_foot'
    n = lambda t: f'{t}_{side}'
    box(s, Lg, n('hip_ball'), (LX, HIP_Y - 0.3, 0.4), (3.4, 3.4, 3.4), 'bone')
    box(s, Lg, n('femur'), (LX, 28.6, 0.6), (2.2, 12.0, 2.2), 'bone')
    box(s, Lg, n('cuisse'), (LX, 28.0, -1.4), (4.8, 9.4, 1.4), 'patina', {'trim', 'moss'})
    box(s, Lg, n('cuisse_side'), (LX + 2.2, 28.4, 0.2), (1.0, 8.6, 3.8), 'patina', {'barnacles'})
    box(s, Lg, n('cuisse_lame'), (LX, 23.6, -1.0), (5.0, 1.6, 2.4), 'patina', {'trim'})
    barnacles(s, Lg, n('cuisse_barn'), (LX + 0.8, 30.2, -2.1), (2, -1), 3, 0.9)
    moss(s, Lg, n('cuisse_moss'), (LX, 23.0, -2.25), 2, (2.0, 4.0), 1.2)
    box(s, S, n('knee_knob'), (LX, KNEE_Y, -0.6), (3.6, 3.4, 3.6), 'bone')
    box(s, S, n('knee_cop'), (LX, KNEE_Y + 0.4, -2.9), (4.4, 4.6, 1.4), 'patina', {'trim', 'moss'})
    box(s, S, n('knee_wing'), (LX + 2.4, KNEE_Y + 0.2, -1.6), (0.9, 3.6, 2.8), 'patina', {'trim'})
    box(s, S, n('knee_spike'), (LX, KNEE_Y + 1.6, -4.1), (1.2, 1.2, 1.6), 'patina')
    barnacles(s, S, n('knee_barn'), (LX - 0.8, KNEE_Y - 1.2, -3.6), (2, -1), 3, 0.8)
    box(s, S, n('tibia'), (LX, 13.4, 0.8), (2.0, 11.0, 2.0), 'bone')
    box(s, S, n('greave'), (LX, 11.6, -0.6), (5.2, 11.6, 3.6), 'patina', {'moss', 'barnacles'})
    box(s, S, n('greave_ridge'), (LX, 12.2, -2.65), (1.8, 9.6, 0.6), 'patina', {'trim'})
    box(s, S, n('greave_cuff'), (LX, 17.0, -0.6), (5.6, 1.4, 4.0), 'patina', {'trim'})
    moss(s, S, n('greave_moss'), (LX + 2.65, 16.4, -0.6), 2, (2.0, 4.5), 1.2, axis=2)
    box(s, F, n('ankle_knob'), (LX, ANKLE_Y, 0.4), (3.0, 2.8, 3.0), 'bone')
    box(s, F, n('sabaton'), (LX, 2.0, -1.2), (5.6, 4.0, 9.0), 'patina', {'barnacles', 'trim'})
    box(s, F, n('sabaton_top'), (LX, 4.4, -2.4), (4.8, 1.2, 5.4), 'patina', {'moss'})
    box(s, F, n('toe_plate'), (LX, 1.3, -6.6), (5.0, 2.6, 1.8), 'patina', {'trim'})
    for k, dx in enumerate((-1.6, 0, 1.6)):
        box(s, F, n(f'toe_claw{k}'), (LX + dx, 0.55, -8.0), (0.9, 1.1, 1.4), 'claw')
    box(s, F, n('heel_spur'), (LX, 1.2, 3.8), (1.4, 1.4, 1.6), 'patina')
    barnacles(s, F, n('foot_barn'), (LX + 1.6, 4.3, -1.0), (1, 1), 2, 0.6)

# ================================================================== pelvis, belt, tassets, loincloth
box(1, 'body', 'pelvis_bone', (0, 36.6, 0.6), (8.6, 3.0, 4.6), 'bone')
box(1, 'body', 'sacrum', (0, 37.4, 2.8), (2.6, 3.6, 1.0), 'bone_dark')
box(1, 'body', 'belt', (0, 39.0, 0.5), (11.0, 2.4, 7.8), 'leather', {'studs'})
box(1, 'body', 'belt_plate', (0, 38.8, -3.6), (5.2, 3.4, 0.8), 'patina', {'trim', 'moss'})
box(1, 'body', 'belt_skull', (0, 38.9, -4.25), (2.4, 2.4, 0.6), 'skull_small', {'glow_eyes'})
barnacles(1, 'body', 'belt_barn', (3.6, 39.4, -3.6), (2, -1), 3, 0.8)
moss(1, 'body', 'belt_moss', (-2.0, 37.6, -4.0), 3, (2.5, 5.0), 1.4)
for side, s in (('right', 1), ('left', -1)):
    tb = f'tabard_{side}'
    box(s, tb, f'tasset_{side}', (6.8, 33.6, -1.4), (1.0, 8.6, 6.0), 'patina', {'trim', 'moss'})
    box(s, tb, f'tasset_front_{side}', (5.4, 33.0, -4.0), (3.6, 7.6, 0.9), 'patina', {'trim', 'barnacles'})
    barnacles(s, tb, f'tasset_barn_{side}', (7.35, 34.6, -1.6), (0, 1), 3, 1.0)
    moss(s, tb, f'tasset_moss_{side}', (7.4, 29.2, -1.4), 3, (2.5, 6.0), 1.8, axis=2)
rag(1, 'tabard_front', 'loincloth', (0, 29.5, -4.4), 4.6, 16.0, 0.5, 3, flags=('ragged',))
rag(1, 'tabard_back', 'tail_cloth', (0, 27.5, 4.2), 9.0, 21.0, 0.5, 4, flags=('ragged', 'moss'))
rag(1, 'banner', 'sash', (-5.6, 31.6, -3.0), 2.2, 13.0, 0.4, 2, flags=('ragged',))

# ================================================================== the bare spine between pelvis and ribs
for k in range(4):
    box(1, 'waist', f'lumbar{k}', (0, 41.0 + k * 1.45, 1.0), (2.6 - 0.2 * (k % 2), 1.0, 2.4), 'bone')
box(1, 'waist', 'lumbar_disc', (0, 42.5, 1.0), (1.6, 4.4, 1.6), 'bone_dark')

# ================================================================== chest: an open ribcage over a glowing soul
box(1, 'chest', 'thoracic_spine', (0, 51.2, 2.4), (1.8, 11.0, 1.8), 'bone')
for k in range(6):
    y = 47.6 + k * 1.75; w = (4.0, 4.6, 5.0, 5.3, 5.3, 4.8)[k]
    for s in (1, -1):
        box(s, 'chest', f'rib{k}_back_{s}', (w * 0.55, y + 0.25, 2.0), (w * 0.9, 0.8, 1.0), 'bone')
        box(s, 'chest', f'rib{k}_side_{s}', (w, y, -0.3), (0.9, 0.8, 4.4), 'bone')
        if k >= 1:
            box(s, 'chest', f'rib{k}_front_{s}', (w * 0.58, y - 0.35, -2.75), (w * 0.85, 0.8, 0.8), 'bone')
box(1, 'chest', 'sternum', (0, 52.0, -3.05), (1.4, 7.4, 0.9), 'bone')
box(1, 'chest', 'soul_core', (0, 51.0, -0.2), (2.6, 2.6, 2.6), 'soul')
box(1, 'chest', 'collar_bone', (0, 56.9, -1.6), (7.0, 0.9, 1.0), 'bone')
# the hooded cloak's shoulders and its torn front edges
box(1, 'chest', 'mantle', (0, 57.9, 1.6), (12.4, 1.6, 7.6), 'cloth', {'moss', 'ragged'})
box(1, 'chest', 'mantle_back', (0, 54.0, 4.6), (12.0, 7.6, 0.8), 'cloth', {'moss'})
rag(1, 'drape_left', 'drape_left', (-5.4, 51.0, -3.6), 3.0, 12.0, 0.5, 2)
rag(1, 'drape_right', 'drape_right', (5.4, 50.0, -3.6), 3.0, 14.0, 0.5, 2)
moss(1, 'chest', 'mantle_moss', (-3.6, 57.0, -2.4), 3, (2.5, 6.0), 1.4)

# ================================================================== clavicles, arms, skeletal hands
for side, s in (('right', 1), ('left', -1)):
    C, A, Fa, H = f'{side}_clavicle', f'{side}_arm', f'{side}_forearm', f'{side}_hand'
    n = lambda t: f'{t}_{side}'
    box(s, C, n('clavicle'), (6.4, 56.6, -0.6), (7.2, 1.0, 1.1), 'bone')
    box(s, A, n('shoulder_ball'), (AX, SHO_Y, 0.2), (3.4, 3.4, 3.4), 'bone')
    box(s, A, n('humerus'), (AX, 49.0, 0.4), (2.2, 11.6, 2.2), 'bone')
    # pauldron: three overlapping plates, barnacles, a skull, moss hanging from the bottom edge
    box(s, A, n('pauldron'), (AX + 1.0, 58.4, 0.2), (6.6, 1.8, 8.4), 'patina', {'trim', 'moss', 'barnacles'})
    box(s, A, n('pauldron_lame1'), (AX + 2.2, 56.4, 0.2), (4.6, 2.6, 8.0), 'patina', {'trim', 'moss'})
    box(s, A, n('pauldron_lame2'), (AX + 2.9, 53.8, 0.2), (3.4, 2.8, 7.4), 'patina', {'trim'})
    box(s, A, n('pauldron_ridge'), (AX + 1.4, 59.5, 0.2), (2.6, 0.8, 7.0), 'patina', {'trim'})
    barnacles(s, A, n('pauldron_barn'), (AX + 2.0, 59.6, -1.6), (1, 1), 4, 1.4)
    box(s, A, n('pauldron_skull'), (AX + 4.75, 55.2, -1.0), (0.7, 2.4, 2.4), 'skull_small', {'glow_eyes'})
    moss(s, A, n('pauldron_moss'), (AX + 4.55, 52.4, 0.2), 4, (3.0, 7.0), 2.6, axis=2)
    box(s, Fa, n('elbow_knob'), (AX + 0.3, ELB_Y, 0.8), (3.0, 3.0, 3.0), 'bone')
    if s > 0:      # right: an armoured arm (rerebrace, elbow cop, bracer)
        box(s, A, n('rerebrace'), (AX, 48.8, 0.4), (3.8, 7.6, 3.8), 'patina', {'moss', 'trim'})
        box(s, Fa, n('elbow_cop'), (AX + 0.3, ELB_Y + 0.4, 2.8), (3.4, 3.4, 1.2), 'patina', {'trim'})
        box(s, Fa, n('radius'), (AX + 0.3, 35.6, 0.5), (1.6, 11.0, 1.6), 'bone')
        box(s, Fa, n('bracer'), (AX + 0.3, 33.6, 0.3), (3.8, 7.4, 3.8), 'patina', {'barnacles', 'trim'})
        barnacles(s, Fa, n('bracer_barn'), (AX + 2.25, 34.6, -0.4), (0, 1), 3, 1.0)
    else:          # left: bare bone above, a spiked vambrace below
        box(s, Fa, n('radius'), (AX + 0.9, 35.5, 0.4), (1.3, 11.4, 1.3), 'bone')
        box(s, Fa, n('ulna'), (AX - 0.5, 35.5, 1.0), (1.3, 11.4, 1.3), 'bone')
        box(s, Fa, n('vambrace'), (AX + 0.2, 33.0, 0.6), (4.0, 6.6, 4.0), 'patina', {'barnacles', 'moss'})
        box(s, Fa, n('vambrace_spike'), (AX + 2.4, 35.6, 0.6), (1.0, 3.0, 1.4), 'patina', {'trim'})
        box(s, Fa, n('vambrace_spike2'), (AX + 2.4, 31.6, 0.6), (0.8, 2.0, 1.0), 'patina')
        moss(s, Fa, n('vambrace_moss'), (AX + 2.1, 29.7, 0.6), 2, (2.0, 4.0), 1.2, axis=2)
    box(s, H, n('wrist_knob'), (AX, WRI_Y, 0.0), (2.4, 1.6, 2.4), 'bone')
    box(s, H, n('palm_bones'), (AX, 26.6, 0.0), (1.4, 2.8, 3.6), 'bone')
for k, zc in enumerate(FZ):                        # left: long finger bones with claw tips, spread a little
    ln = (3.6, 4.4, 4.2, 3.4)[k]
    box(1, f'left_finger{k}', f'finger{k}_left', (-AX, 25.0 - ln / 2, zc), (0.85, ln, 0.85), 'bone')
    box(1, f'left_finger{k}', f'finger{k}_knuckle_left', (-AX, 25.0 - ln * 0.55, zc), (1.05, 0.7, 1.05), 'bone_dark')
    box(1, f'left_finger{k}', f'finger{k}_claw_left', (-AX, 25.0 - ln - 0.5, zc), (0.6, 1.0, 0.6), 'claw')
box(1, 'left_thumb', 'thumb_left', (-AX + 1.1, 25.2, -1.6), (0.8, 2.8, 0.8), 'bone')
# right: four finger bones closed around the grip (front of the grip) and a thumb across them
for k, yc in enumerate((26.4, 25.4, 24.4, 23.4)):
    box(1, 'right_fingers', f'finger{k}_right', (AX - 0.6, yc, -0.3), (0.8, 0.8, 3.0), 'bone')
    box(1, 'right_fingers', f'finger{k}_tip_right', (AX + 0.2, yc, -1.6), (1.4, 0.75, 0.75), 'bone')
box(1, 'right_thumb', 'thumb_right', (AX + 0.2, 26.6, -1.9), (1.8, 0.8, 0.8), 'bone')

# ================================================================== the greatsword (sword space: grip point = pivot, blade -z)
gx, gy, gz = GRIP
box(1, 'sword', 'grip', (gx, gy, gz + 2.0), (1.5, 1.5, 10.0), 'leather', {'wrap'})
box(1, 'sword', 'pommel', (gx, gy, gz + 8.0), (2.8, 2.8, 2.0), 'patina', {'trim'})
box(1, 'sword', 'pommel_cap', (gx, gy, gz + 9.3), (1.6, 1.6, 0.6), 'patina')
barnacles(1, 'sword', 'pommel_barn', (gx + 1.4, gy, gz + 8.0), (0, 1), 2, 0.6)
box(1, 'sword', 'guard', (gx, gy, gz - 3.9), (2.2, 13.6, 1.8), 'patina', {'trim', 'moss'})
for sg in (1, -1):
    box(1, 'sword', f'guard_end{sg}', (gx, gy + 7.0 * sg, gz - 4.3), (2.6, 1.8, 2.6), 'patina')
barnacles(1, 'sword', 'guard_barn', (gx + 1.1, gy + 3.6, gz - 3.9), (0, 1), 3, 0.9)
moss(1, 'sword', 'guard_moss', (gx + 1.2, gy - 4.5, gz - 4.8), 2, (2.0, 3.5), 1.0, axis=1)
box(1, 'sword', 'ricasso', (gx, gy, gz - 6.0), (1.3, 3.4, 2.4), 'patina', {'trim'})
box(1, 'sword', 'blade', (gx, gy, gz - 4.8 - 37.0 / 2), (1.0, 5.2, 37.0), 'blade', {'battleworn'})
box(1, 'sword', 'fuller', (gx, gy, gz - 4.8 - 24.0 / 2), (1.2, 1.2, 24.0), 'patina')
barnacles(1, 'sword', 'blade_barn_a', (gx + 0.6, gy + 1.2, gz - 14.0), (0, 1), 3, 1.0)
barnacles(1, 'sword', 'blade_barn_b', (gx + 0.6, gy - 1.4, gz - 27.0), (0, 1), 2, 0.8)

# ================================================================== head: skull, hood, crown
for k in range(3):
    box(1, 'neck', f'cervical{k}', (0, 58.3 + k * 0.95, 0.5), (1.9 - 0.15 * k, 0.65, 1.9), 'bone')
box(1, 'neck', 'neck_disc', (0, 59.3, 0.5), (1.1, 2.8, 1.1), 'bone_dark')
HX = (0, 2.8, 1.0)                               # skull detail layout (from the original face), placed on this neck
def hb(name, c, size, mat, flags=(), s=1, b='head'):
    box(s, b, name, (c[0], c[1] + HX[1], c[2] + HX[2]), size, mat, flags)
hb('cranium', (0, 64.7, -1.6), (6.4, 3.8, 7.0), 'bone_skull')
hb('skull_core', (0, 61.4, -2.2), (5.0, 4.6, 5.4), 'skull_low')
hb('socket_back', (0, 62.0, -4.85), (4.4, 2.4, 0.5), 'socket')
hb('forehead', (0, 64.0, -5.25), (4.6, 1.2, 0.8), 'bone')
for s_ in (1, -1):
    hb(f'eye_{s_}', (1.4, 61.95, -5.15), (0.95, 0.85, 0.3), 'eye', s=s_)
    hb(f'brow_{s_}', (1.45, 63.35, -5.55), (2.3, 0.8, 1.0), 'bone', s=s_)
    hb(f'orbit_{s_}', (2.45, 62.0, -5.25), (0.6, 2.8, 1.2), 'bone', s=s_)
    hb(f'socket_floor_{s_}', (1.45, 60.6, -5.35), (2.1, 0.6, 1.1), 'bone', s=s_)
    hb(f'cheekbone_{s_}', (2.5, 60.4, -4.6), (0.6, 1.0, 2.2), 'bone', s=s_)
    hb(f'temple_{s_}', (2.55, 62.6, -2.2), (0.3, 2.4, 3.0), 'bone_dark', s=s_)
    hb(f'maxilla_{s_}', (1.05, 59.75, -5.3), (1.0, 1.7, 0.9), 'bone', s=s_)
hb('nasal_bridge', (0, 62.2, -5.35), (0.8, 2.0, 0.6), 'bone')
hb('nose_cavity', (0, 59.95, -5.0), (1.1, 1.6, 0.5), 'socket')
hb('philtrum', (0, 59.1, -5.35), (1.2, 0.3, 0.8), 'bone')
hb('teeth_upper', (0, 58.55, -5.35), (3.0, 0.9, 0.7), 'teeth')
hb('jaw', (0, 57.2, -3.9), (3.6, 1.0, 3.2), 'jaw', b='jaw')
hb('teeth_lower', (0, 57.8, -5.2), (2.8, 0.7, 0.6), 'teeth', b='jaw')
hb('chin', (0, 56.8, -5.15), (2.0, 1.2, 1.0), 'bone', b='jaw')
for s_ in (1, -1):
    hb(f'jaw_hinge_{s_}', (1.9, 58.0, -1.9), (0.6, 2.0, 1.2), 'bone', s=s_, b='jaw')
# hood: a torn cowl standing clear of the skull, open at the front
hb('hood_back', (0, 63.4, 2.6), (8.6, 6.6, 0.9), 'cloth', {'moss'})
hb('hood_top', (0, 67.15, -1.2), (8.4, 0.9, 7.8), 'cloth', {'moss'})
for s_ in (1, -1):
    hb(f'hood_side_{s_}', (3.95, 63.8, -1.2), (0.8, 6.2, 7.0), 'cloth', {'ragged'}, s=s_)
rag(1, 'hood_drape', 'hood_drape', (0, 59.0, 4.2), 8.0, 8.0, 0.6, 3)
# crown: rim and band on the hood, seven tall jagged points (one snapped), barnacles and hanging moss
CY = 68.0
box(1, 'crown', 'crown_rim', (0, CY + 0.45, -0.6), (9.4, 0.9, 9.0), 'patina', {'barnacles'})
box(1, 'crown', 'crown_band', (0, CY + 1.9, -0.6), (9.0, 2.0, 8.6), 'patina', {'trim', 'moss'})
hx, hz = 4.1, 3.9
for k, (x, z, h) in enumerate(((0, -hz, 7.4), (hx, -hz, 5.6), (-hx, -hz, 6.2), (hx, 0.4, 4.4), (-hx, 0.4, 4.8), (hx * 0.6, hz, 3.8), (-hx * 0.6, hz, 1.6))):
    w = 1.6 if h > 4 else 1.4
    box(1, 'crown', f'crown_point{k}', (x, CY + 2.9 + h * 0.3, z - 0.6), (w, h * 0.6, 0.9), 'patina', {'trim'} if k == 0 else ())
    box(1, 'crown', f'crown_point{k}_tip', (x, CY + 2.9 + h * 0.8, z - 0.6), (w * 0.5, h * 0.4, 0.7), 'patina')
box(1, 'crown', 'crown_gem', (0, CY + 1.9, -5.0), (1.5, 1.5, 0.5), 'soul')
barnacles(1, 'crown', 'crown_barn_a', (3.0, CY + 2.6, -4.95), (2, -1), 3, 0.8)
barnacles(1, 'crown', 'crown_barn_b', (-2.6, CY + 2.4, -4.95), (2, -1), 2, 0.7)
moss(1, 'crown', 'crown_moss_r', (4.6, CY + 0.2, -2.0), 3, (2.5, 5.5), 1.6, axis=2)
moss(1, 'crown', 'crown_moss_l', (-4.6, CY + 0.2, -1.0), 2, (2.0, 4.0), 1.2, axis=2)

# ================================================================== the cloak: three torn panels, two segments each, from the shoulders
for k, (x, w, ln) in enumerate(((0, 7.6, 50), (-6.3, 6.8, 46), (6.3, 6.8, 48))):
    bn = ('cape_mid', 'cape_left', 'cape_right')[k]
    up = ln * 0.48; lo = ln - up
    bone(bn, 'cape', (x, 58.0, 5.4))
    bone(bn + '_low', bn, (x, 58.0 - up, 5.4))
    box(1, bn, f'cape{k}_upper', (x, 58.0 - up / 2, 5.4), (w, up + 0.4, 0.6), 'cloth', {'ragged', 'moss'})
    rag(1, bn + '_low', f'cape{k}_lower', (x, 58.0 - up - lo / 2, 5.4), w * 0.96, lo, 0.6, 3, flags=('ragged',))

# ------------------------------------------------------------------ order bones parents-first, helpers used by the pipeline
_names = [b['name'] for b in BONES]
_ordered = []
def _add(n):
    if n in _ordered: return
    b = next(x for x in BONES if x['name'] == n)
    if b['parent']: _add(b['parent'])
    _ordered.append(n)
for n in _names: _add(n)
BONES[:] = [next(x for x in BONES if x['name'] == n) for n in _ordered]

def rot_m(rr):
    rx, ry, rz = [math.radians(a) for a in rr]
    X = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Y = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Z = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return Z @ Y @ X
_b = {b['name']: b for b in BONES}
def world_pt(bname, p):
    p = np.array(p, float)
    while bname:
        b = _b[bname]; piv = np.array(b['pivot'], float)
        p = piv + rot_m(b['rot']) @ (p - piv); bname = b['parent']
    return p
def cube_corners_local(c):
    f0 = np.array(c['frm']); s = np.array(c['size'])
    crot = rot_m(c['rot']) if c['rot'] else None; cp = np.array(c['pivot']) if c['pivot'] else None
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                p = f0 + s * np.array([dx, dy, dz])
                yield cp + crot @ (p - cp) if crot is not None else p
def cube_corners(c):
    for p in cube_corners_local(c): yield world_pt(c['bone'], p)
SWORD_TIP = min(p[1] for c in CUBES if c['bone'] == 'sword' for p in cube_corners(c))
TOP = max(p[1] for c in CUBES for p in cube_corners(c))
HAND = world_pt('right_hand', GRIP)
