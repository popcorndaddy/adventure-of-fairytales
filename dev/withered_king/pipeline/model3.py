"""Withered Sentinel v3: cluster-built skeletal crowned knight (Blockbench units, y up, faces -z, +x = its right)."""
import math, random, zlib
import numpy as np
BONES = []; CUBES = []

def bone(name, parent, pivot, rot=(0, 0, 0)):
    BONES.append(dict(name=name, parent=parent, pivot=list(pivot), rot=list(rot)))

def cube(b, name, frm, size, mat, flags=(), rot=None, pivot=None):
    CUBES.append(dict(bone=b, name=name, frm=list(frm), size=list(size), mat=mat, flags=set(flags),
                      rot=list(rot) if rot else None, pivot=list(pivot) if pivot else None))

def box(s, b, name, c, size, mat, flags=(), rot=None, pivot=None):
    """centre-based cube; s=-1 mirrors a right-side (+x) part to the left"""
    c = (c[0] * s, c[1], c[2])
    if rot: rot = (rot[0], rot[1] * s, rot[2] * s)
    if pivot: pivot = (pivot[0] * s, pivot[1], pivot[2])
    elif rot: pivot = c
    frm = [c[k] - size[k] / 2 for k in range(3)]
    cube(b, name, frm, size, mat, flags, rot, pivot)

def R(name): return random.Random(zlib.crc32(name.encode()))

def spike(s, b, name, base, rot, L, w, mat='patina', flags=(), segs=3):
    for k in range(segs):
        wk = w * (1 - 0.3 * k); hk = L / segs
        box(s, b, f'{name}_{k}', (base[0], base[1] + hk * (k + 0.5), base[2]), (wk, hk + 0.15, wk), mat,
            flags if k == 0 else (), rot=rot, pivot=base)

def jag(s, b, name, centre, rad, n, smin, smax, mat='patina', flags=(), rotmax=25, up=False):
    r = R(name)
    for i in range(n):
        d = np.array([r.gauss(0, 1) for _ in range(3)]); d /= np.linalg.norm(d) + 1e-9
        if up and d[1] < 0: d[1] = -d[1]
        p = np.array(centre) + d * np.array(rad) * (0.7 + 0.3 * r.random())
        sz = [r.uniform(smin, smax) for _ in range(3)]
        rot = tuple(r.uniform(-rotmax, rotmax) for _ in range(3))
        box(s, b, f'{name}{i}', tuple(p), sz, mat, flags, rot=rot)

def limb(s, b, name, top, bot_y, w0, w1, mat='bone', flags=(), n=3, jit=0.25, depth=1.0):
    r = R(name); L = (top[1] - bot_y) / n
    for k in range(n):
        w = w0 + (w1 - w0) * k / max(1, n - 1)
        c = (top[0] + r.uniform(-jit, jit), top[1] - L * (k + 0.5), top[2] + r.uniform(-jit, jit))
        box(s, b, f'{name}{k}', c, (w, L + 0.35, w * depth), mat, flags,
            rot=(r.uniform(-4, 4), r.uniform(-8, 8), r.uniform(-4, 4)))

def drip(s, b, name, top, L, mat='drip'):
    box(s, b, name, (top[0], top[1] - L / 2, top[2]), (0.6, L, 0.6), mat)
    box(s, b, name + '_bead', (top[0], top[1] - L, top[2]), (0.9, 0.9, 0.9), mat)

# ================================================================== skeleton
bone('root', None, (0, 0, 0))
bone('body', 'root', (0, 33, 0))
bone('skirt', 'body', (0, 34, 0))
bone('waist', 'body', (0, 36, 0), (-9, 0, 0))
bone('chest', 'waist', (0, 44, 0), (-16, 0, 0))
bone('head', 'chest', (0, 57, -1), (19, 0, 0))
bone('jaw', 'head', (0, 59.5, -1.5), (9, 0, 0))
bone('cape', 'chest', (0, 56, 5.4), (21, 0, 0))
for side, s in (('right', 1), ('left', -1)):
    bone(f'{side}_arm', 'chest', (12.5 * s, 53, 0))
    bone(f'{side}_forearm', f'{side}_arm', (12.5 * s, 38, 0))
    bone(f'{side}_hand', f'{side}_forearm', (12.5 * s, 25.5, 0))
    bone(f'{side}_leg', 'body', (6.5 * s, 33, 0))
    bone(f'{side}_shin', f'{side}_leg', (6.5 * s, 19, 0))
    bone(f'{side}_foot', f'{side}_shin', (6.5 * s, 4, -0.5))
bone('sword', 'right_hand', (12.5, 23.5, 0))

POSE = {'right_arm': (29.33, -15.6, -35.54), 'right_forearm': (111.8, -27.58, 0), 'right_hand': (2.67, 16.17, 23.47), 'sword': (0, 180, 0),
        'left_arm': (10, 0, -16), 'left_forearm': (34, 0, 0), 'left_hand': (14, 0, -8),
        'right_leg': (16, 0, 7), 'right_shin': (-30, 0, 0), 'right_foot': (14, 0, -7),
        'left_leg': (10, 0, -8), 'left_shin': (-22, 0, 0), 'left_foot': (12, 0, 8)}
import os, json
POSE.update({k: tuple(v) for k, v in json.loads(os.environ.get('POSE', '{}')).items()})
for b in BONES:
    if b['name'] in POSE: b['rot'] = list(POSE[b['name']])

# ================================================================== legs
for side, s in (('right', 1), ('left', -1)):
    L, S, F = f'{side}_leg', f'{side}_shin', f'{side}_foot'
    n = lambda t: f'{t}_{side}'
    limb(s, L, n('femur'), (6.5, 33, 0), 19.5, 3.2, 2.4, 'bone')
    box(s, L, n('thigh_plate'), (6.6, 27, -2.9), (6.6, 8.5, 1.4), 'patina', {'trim', 'moss'}, rot=(9, 0, -3))
    box(s, L, n('thigh_side'), (9.4, 25.5, -0.8), (1.4, 9, 5.5), 'patina', {'barnacles'}, rot=(0, 0, 7))
    box(s, L, n('tasset'), (6.6, 31, -3.6), (8, 3, 1.6), 'patina', {'trim'}, rot=(14, 0, -4))
    box(s, L, n('thigh_strap'), (6.5, 23.5, -0.6), (5.2, 1.2, 5.6), 'leather')
    # knee: big cop, a fan plate, an embedded skull and spikes
    box(s, S, n('knee'), (6.5, 19.2, -2.4), (6, 5.4, 5.6), 'patina', {'moss', 'barnacles', 'trim'}, rot=(0, 6, 0))
    box(s, S, n('knee_fan'), (6.5, 20.4, -5.4), (4.8, 4, 1.4), 'patina', {'trim'}, rot=(-14, 0, 0))
    box(s, S, n('knee_skull'), (6.5, 19.2, -6.4), (3, 3, 1.5), 'skull_small', {'glow_eyes'})
    spike(s, S, n('knee_spike'), (6.5, 21.5, -5.6), (-55, 0, 0), 4.5, 1.6)
    spike(s, S, n('knee_spur'), (9.2, 19.5, -2.5), (0, 0, -70), 3.2, 1.3)
    limb(s, S, n('tibia'), (6.5, 17, 0.3), 4.5, 2.2, 1.8, 'bone', n=2)
    box(s, S, n('greave'), (6.5, 10.5, -2.3), (5.6, 11, 1.6), 'patina', {'moss', 'trim'}, rot=(-5, 0, 0))
    box(s, S, n('greave_side'), (9.2, 10.5, -0.2), (1.4, 10, 4.6), 'patina', {'barnacles'}, rot=(0, 0, 4))
    box(s, S, n('greave_back'), (6.5, 11, 1.9), (4.6, 9, 1.2), 'patina')
    jag(s, S, n('greave_rim'), (6.5, 16, -1.2), (3, 0.6, 2.6), 6, 0.8, 1.8, 'patina', rotmax=30, up=True)
    # foot
    box(s, F, n('sabaton'), (6.5, 1.6, -1.2), (7, 3.2, 9), 'patina', {'barnacles', 'trim'})
    box(s, F, n('instep'), (6.5, 3.8, -1.6), (6.2, 2, 7), 'patina', {'moss'}, rot=(-6, 0, 0))
    box(s, F, n('toe_plate'), (6.5, 1.4, -6.6), (6.2, 2.6, 3), 'patina', {'trim'}, rot=(10, 0, 0))
    for k, dx in enumerate((-2, 0, 2)):
        box(s, F, n(f'toe_claw{k}'), (6.5 + dx, 0.7, -8.8), (1, 1.2, 2.6), 'claw', rot=(14, 0, 0))
    box(s, F, n('heel_spur'), (6.5, 1.4, 4), (1.4, 1.4, 2.4), 'patina', rot=(-20, 0, 0))

# ================================================================== pelvis, belt, faulds, tabard
box(1, 'body', 'pelvis', (0, 31.6, 0), (10, 4, 5.2), 'bone')
box(1, 'body', 'belt', (0, 35, 0), (17, 3, 11), 'leather', {'studs'})
box(1, 'body', 'belt_skull', (0, 35, -6), (4, 4, 1.6), 'skull_small', {'glow_eyes'})
for k, x in enumerate((-7, -2.4, 2.4, 7)):
    ln = 10 + (k % 2) * 3 - (k == 3) * 2
    box(1, 'skirt', f'fauld{k}', (x, 33.5 - ln / 2, -6), (4.6, ln, 1.2), 'patina',
        {'trim', 'moss'} if k % 2 else {'trim', 'barnacles'}, rot=(-9 + k * 2, 0, -x * 1.3), pivot=(x, 34, -6))
for s in (1, -1):
    box(s, 'skirt', f'fauld_side_{s}', (9.4, 28, -1), (1.4, 11, 8), 'patina', {'trim'}, rot=(0, 0, 11), pivot=(9, 34, -1))
box(1, 'skirt', 'tabard_front', (0, 20, -6.6), (6, 26, 0.8), 'cloth', {'ragged', 'holes'}, rot=(-4, 0, 0), pivot=(0, 33, -6.6))
box(1, 'skirt', 'tabard_back', (0, 19, 5.4), (16, 30, 0.8), 'cloth', {'ragged', 'holes', 'moss'}, rot=(5, 0, 0), pivot=(0, 34, 5.4))
for s in (1, -1):
    box(s, 'skirt', f'tabard_side_{s}', (9.6, 22, 1.5), (0.8, 22, 6), 'cloth', {'ragged'}, rot=(0, 0, 6), pivot=(9.6, 33, 1.5))
drip(1, 'body', 'belt_drip_a', (-4.5, 33.4, -5.6), 7)
drip(1, 'body', 'belt_drip_b', (5.5, 33.4, -5.4), 4.5)
drip(1, 'body', 'belt_vine', (-8, 33.6, -3), 9, 'vine')

# ================================================================== waist / spine
for k in range(4):
    box(1, 'waist', f'vertebra{k}', (0, 37 + k * 2.1, 1.2), (2.8 - (k % 2) * 0.5, 1.6, 2.8), 'bone', rot=(0, k * 9, 0))
box(1, 'waist', 'lower_spine', (0, 40, 1.4), (1.6, 8, 1.6), 'bone')

# ================================================================== chest: ribcage, broken breastplate, soul core
box(1, 'chest', 'spine', (0, 50, 2.4), (2.2, 13, 2.2), 'bone')
for k in range(5):
    y = 45 + k * 2.1; w = 6.0 + (0.4, 0.8, 0.8, 0.4, -0.4)[k]
    for s in (1, -1):
        box(s, 'chest', f'rib{k}_side_{s}', (w - 0.5, y, -0.8), (1, 1, 7), 'bone', rot=(0, 8, 0))
        box(s, 'chest', f'rib{k}_front_{s}', (w / 2 + 0.3, y - 0.6, -4.6), (w - 0.6, 1, 1), 'bone', rot=(0, -12, 12))
box(1, 'chest', 'sternum', (0, 49, -5.4), (2.2, 8, 1.2), 'bone')
box(1, 'chest', 'soul_core', (0, 48.6, -1.4), (3.6, 3.6, 3.6), 'soul', rot=(24, 36, 14))
box(1, 'chest', 'clavicle', (0, 55, -3.2), (16, 1.4, 1.6), 'bone')
box(1, 'chest', 'breastplate', (-4.2, 50.8, -6.1), (6.6, 7.6, 1.3), 'patina', {'trim', 'moss', 'barnacles'}, rot=(-6, 10, 8))
box(1, 'chest', 'breast_shard', (-6.4, 45.4, -5.6), (4, 4, 1.2), 'patina', {'trim'}, rot=(4, 14, -16))
box(1, 'chest', 'breast_shard_r', (4.6, 53.4, -5.8), (5, 3, 1.2), 'patina', {'trim'}, rot=(-8, -8, -12))
box(1, 'chest', 'backplate', (0, 49.5, 4.6), (14, 12, 1.4), 'patina', {'moss', 'barnacles'})
box(1, 'chest', 'mantle', (0, 55.8, 0.4), (20, 3, 10.5), 'cloth', {'moss', 'ragged'})
box(1, 'chest', 'mantle_drape_l', (-6.5, 51, -5.8), (5, 8, 0.8), 'cloth', {'ragged'}, rot=(0, 0, 7), pivot=(-6.5, 55, -5.8))
box(1, 'chest', 'mantle_drape_r', (7.5, 50, -5.6), (4, 10, 0.8), 'cloth', {'ragged'}, rot=(0, 0, -5), pivot=(7.5, 55, -5.6))
for k, (x, rz) in enumerate(((-3.2, 18), (0, 0), (3.2, -18))):
    box(1, 'chest', f'gorget{k}', (x, 56.8, -4.4), (3.8, 3, 1.3), 'patina', {'trim'}, rot=(-24, 0, rz))
# weapons of fallen heroes stuck in his back
for k, (base, rot, ln) in enumerate((((3, 50, 5.4), (-48, 0, -22), 15), ((-4, 47, 5.4), (-38, 0, 26), 11),
                                     ((0.6, 54, 5.4), (-62, 0, 6), 8))):
    box(1, 'chest', f'shaft{k}', (base[0], base[1] + ln / 2, base[2]), (1, ln, 1), 'wood', rot=rot, pivot=base)
    box(1, 'chest', f'shaft{k}_end', (base[0], base[1] + ln + 0.4, base[2]), (1.4, 1.2, 1.4), 'patina' if k else 'wood', rot=rot, pivot=base)
box(1, 'chest', 'banner', (5.8, 61, 4), (0.4, 7, 4.5), 'cloth', {'ragged', 'holes'}, rot=(-48, 0, -22), pivot=(3, 50, 5.4))

# ================================================================== head: skull, jagged crown, hood
box(1, 'head', 'neck', (0, 57.6, -0.6), (1.8, 3.4, 1.8), 'bone')
# a skull with real proportions: taller than wide, domed cranium, two separate sockets, long nose cavity, narrow jaw
box(1, 'head', 'cranium', (0, 64.7, -1.6), (6.4, 3.8, 7.0), 'bone_skull')
box(1, 'head', 'skull_core', (0, 61.4, -2.2), (5.0, 4.6, 5.4), 'skull_low')
box(1, 'head', 'socket_back', (0, 62.0, -4.85), (4.4, 2.4, 0.5), 'socket')
box(1, 'head', 'forehead', (0, 64.0, -5.25), (4.6, 1.2, 0.8), 'bone')
for s_ in (1, -1):
    box(s_, 'head', f'eye_{s_}', (1.4, 61.95, -5.2), (0.55, 0.55, 0.25), 'eye')
    box(s_, 'head', f'brow_{s_}', (1.45, 63.35, -5.55), (2.3, 0.8, 1.0), 'bone', rot=(0, 0, 7))
    box(s_, 'head', f'orbit_{s_}', (2.45, 62.0, -5.25), (0.6, 2.8, 1.2), 'bone')
    box(s_, 'head', f'socket_floor_{s_}', (1.45, 60.6, -5.35), (2.1, 0.6, 1.1), 'bone')
    box(s_, 'head', f'cheekbone_{s_}', (2.5, 60.4, -4.6), (0.6, 1.0, 2.2), 'bone')
    box(s_, 'head', f'temple_{s_}', (2.55, 62.6, -2.2), (0.3, 2.4, 3.0), 'bone_dark')
    box(s_, 'head', f'maxilla_{s_}', (1.05, 59.75, -5.3), (1.0, 1.7, 0.9), 'bone')
box(1, 'head', 'nasal_bridge', (0, 62.2, -5.35), (0.8, 2.0, 0.6), 'bone')
box(1, 'head', 'nose_cavity', (0, 59.95, -5.0), (1.1, 1.6, 0.5), 'socket')
box(1, 'head', 'philtrum', (0, 59.1, -5.35), (1.2, 0.3, 0.8), 'bone')
box(1, 'head', 'teeth_upper', (0, 58.55, -5.35), (3.0, 0.9, 0.7), 'teeth')
box(1, 'jaw', 'jaw', (0, 57.2, -3.4), (3.6, 1.0, 4.2), 'jaw')
box(1, 'jaw', 'teeth_lower', (0, 57.8, -5.2), (2.8, 0.7, 0.6), 'teeth')
box(1, 'jaw', 'chin', (0, 56.8, -5.15), (2.0, 1.2, 1.0), 'bone')
for s_ in (1, -1):
    box(s_, 'jaw', f'jaw_hinge_{s_}', (1.9, 58.3, -1.7), (0.6, 2.4, 1.2), 'bone', rot=(-10, 0, 0))
box(1, 'head', 'crown_rim', (0, 65.5, -2.6), (8.8, 0.9, 9), 'patina', {'barnacles'})
box(1, 'head', 'crown_band', (0, 66.9, -2.6), (8.4, 2.2, 8.6), 'patina', {'trim', 'moss'})
# eight points round the band: tall at the corners and front centre, short between, one snapped off
hx, hz = 3.75, 3.85
for k, (x, z, h, tilt) in enumerate(((0, -hz, 4.6, (-8, 0, 0)), (hx, -hz, 3.4, (-6, 0, -6)), (-hx, -hz, 3.4, (-6, 0, 6)),
                                     (hx, 0, 2.2, (0, 0, -8)), (-hx, 0, 2.4, (0, 0, 8)), (hx, hz, 3.2, (6, 0, -6)),
                                     (-hx, hz, 1.4, (6, 0, 6)), (0, hz, 2.4, (8, 0, 0)))):
    cz = z - 2.6; w = 2.0 if h > 3 else 1.7
    box(1, 'head', f'crown_point{k}', (x, 68 + h * 0.32, cz), (w, h * 0.64, 1.0), 'patina', {'trim'} if k == 0 else (), rot=tilt, pivot=(x, 68, cz))
    box(1, 'head', f'crown_point{k}_tip', (x, 68 + h * 0.82, cz), (w * 0.5, h * 0.36, 0.8), 'patina', rot=tilt, pivot=(x, 68, cz))
box(1, 'head', 'crown_gem', (0, 67.2, -7.25), (1.6, 1.6, 0.6), 'soul')
box(1, 'head', 'hood_back', (0, 61.8, 1.6), (10, 10, 6), 'cloth', {'moss'})
for s in (1, -1):
    box(s, 'head', f'hood_side_{s}', (4.9, 60.6, -2.6), (1.4, 11, 7.4), 'cloth', {'ragged'}, rot=(0, 0, -6))
box(1, 'head', 'hood_top', (0, 66.2, 1.4), (9, 1.4, 5), 'cloth', {'moss'})
box(1, 'head', 'hood_drape', (0, 54.5, 4), (11, 9, 1.5), 'cloth', {'ragged'})
drip(1, 'head', 'crown_drip', (-3.4, 65.1, -7.1), 3.5)
drip(1, 'head', 'crown_vine', (4.2, 65.1, -6.6), 5, 'vine')

# ================================================================== cape: strips of different lengths, each split at the middle so it can drape
STRIP_BONE = {0: 'cape_mid', 1: 'cape_left', 2: 'cape_right', 3: 'cape_left', 4: 'cape_right'}
for k, (x, w, ln) in enumerate(((0, 7, 47), (-6.5, 6, 41), (6.5, 6, 44), (-10.2, 3.4, 30), (10.2, 3, 26))):
    up = ln * 0.55; lo = ln - up; fl = -3 - k % 3 * 2
    bn = STRIP_BONE[k]
    if k < 3: bone(bn, 'cape', (x, 56, 5.6))
    top = (x, 56 - up * math.cos(math.radians(fl)), 5.6 - up * math.sin(math.radians(fl)))
    lb = bn + '_low' if k < 3 else bn
    if k < 3: bone(lb, bn, (x, top[1] + 0.3, top[2]))
    box(1, bn, f'cape{k}_upper', (x, 56 - up / 2, 5.6 + k % 2 * 0.3), (w, up, 0.8), 'cloth', {'ragged', 'moss'} if k < 3 else {'ragged'},
        rot=(fl, 0, -x * 0.4), pivot=(x, 56, 5.6))
    box(1, lb, f'cape{k}_lower', (x, top[1] - lo / 2 + 0.3, top[2]), (w * 0.94, lo, 0.8), 'cloth', {'ragged', 'holes'},
        rot=(fl - 6, 0, -x * 0.6), pivot=(x, top[1] + 0.3, top[2]))

# ================================================================== arms
for side, s in (('right', 1), ('left', -1)):
    A, Fa, H = f'{side}_arm', f'{side}_forearm', f'{side}_hand'
    n = lambda t: f'{t}_{side}'
    box(s, A, n('pauldron'), (13.6, 54.6, 0), (10, 6, 13), 'patina', {'trim', 'moss', 'barnacles'}, rot=(0, 0, -16))
    box(s, A, n('pauldron2'), (14.8, 51, 0), (9, 4, 12), 'patina', {'trim', 'moss'}, rot=(0, 0, -27))
    if s > 0:
        box(s, A, n('pauldron3'), (15.6, 47.8, 0), (7, 3, 10.5), 'patina', {'trim'}, rot=(0, 0, -36))
        box(s, A, n('pauldron_skull'), (14.4, 53.4, -6.8), (3.4, 3.4, 1.4), 'skull_small', {'glow_eyes'}, rot=(0, 0, -16))
        for k, (base, rot, ln) in enumerate((((12, 57.6, -3), (0, 0, -25), 7), ((13.6, 57.2, 1), (12, 0, -36), 9.5),
                                             ((15.2, 56, 4.4), (26, 0, -48), 5.5))):
            spike(s, A, n(f'pauldron_spike{k}'), base, rot, ln, 2)
    else:
        box(s, A, n('pauldron_wrap'), (14, 50.5, 0.5), (9.6, 5, 12.6), 'cloth', {'ragged', 'moss'}, rot=(0, 0, -22))
        spike(s, A, n('pauldron_spike'), (13, 57.4, -1), (6, 0, -18), 6, 2)
        spike(s, A, n('pauldron_stub'), (15.6, 56, 3), (24, 0, -50), 3, 1.8)
    jag(s, A, n('pauldron_rubble'), (13.4, 57.6, 0), (4.2, 1.2, 5.6), 11, 0.9, 2.4, 'patina', {'moss'}, rotmax=30, up=True)
    for k, (z, ln) in enumerate(((-4.5, 6), (0.5, 9), (4, 4.5))):
        drip(s, A, n(f'pauldron_drip{k}'), (18.2 - k * 0.5, 47.6 + k * 0.6, z), ln, 'drip' if k != 1 or s > 0 else 'vine')
    limb(s, A, n('humerus'), (12.5, 50, 0), 39.5, 2.6, 2.2, 'bone', n=2)
    box(s, A, n('elbow'), (12.5, 38.6, 0), (3.4, 3, 3.4), 'bone')
    # forearm: bones inside a huge layered gauntlet
    box(s, Fa, n('radius'), (11.8, 31.5, -0.6), (1.3, 12, 1.3), 'bone')
    box(s, Fa, n('ulna'), (13.2, 31.5, 0.6), (1.3, 12, 1.3), 'bone')
    for k, (y, w) in enumerate(((35, 5), (31.9, 5.8), (28.5, 6.7))):
        box(s, Fa, n(f'gauntlet{k}'), (12.5, y, 0), (w, 3.3 + k * 0.2, w), 'patina',
            {'trim', 'moss'} if k == 1 else {'trim', 'barnacles'}, rot=(0, (k - 1) * 9, (k - 1) * 3))
    box(s, Fa, n('cuff'), (12.5, 26.3, -0.2), (7.4, 1.6, 7.4), 'patina', {'trim'})
    spike(s, Fa, n('elbow_spike'), (12.5, 37, 2.2), (70, 0, 0), 5, 1.8)
    jag(s, Fa, n('gauntlet_spurs'), (15.4, 31, 0), (0.8, 4, 2.6), 5, 0.8, 1.8, 'patina', rotmax=35)
    drip(s, Fa, n('cuff_drip'), (15.8, 25.8, -2), 5)
    # clawed hand
    if s > 0:      # sword hand: a fist wrapped round the grip (grip runs along z through (12.5, 23.5))
        box(s, H, n('hand_back'), (14.5, 23.6, 0), (1.6, 4.4, 5.2), 'bone')
        box(s, H, n('knuckle_plate'), (15.5, 23.6, 0), (0.9, 4, 5.4), 'patina', {'trim'})
        for k, z in enumerate((-1.8, -0.6, 0.6, 1.8)):
            box(s, H, n(f'finger{k}'), (13.1, 25, z), (3.4, 1.1, 1), 'bone')
            box(s, H, n(f'finger{k}_mid'), (11.1, 23.7, z), (1.1, 2.9, 1), 'bone')
            box(s, H, n(f'claw{k}'), (12, 22.05, z), (1.9, 0.9, 0.85), 'claw', rot=(0, 0, 8))
        box(s, H, n('thumb'), (13.6, 21.9, -0.9), (2.6, 1, 1.1), 'bone', rot=(0, 18, 0))
        box(s, H, n('thumb_claw'), (12.2, 21.9, -0.2), (1.2, 0.8, 0.8), 'claw', rot=(0, 18, 0))
        continue
    box(s, H, n('palm'), (12.5, 23.5, 0), (4, 4, 5), 'bone')
    box(s, H, n('knuckle_plate'), (14.4, 23.6, 0), (1.2, 3.6, 5.2), 'patina', {'trim'})
    for k, z in enumerate((-1.8, -0.6, 0.6, 1.8)):
        ln = (3.2, 3.6, 3.4, 2.8)[k]
        box(s, H, n(f'finger{k}'), (12.6, 21.5 - ln / 2, z), (1, ln, 1), 'bone')
        y2 = 21.5 - ln
        box(s, H, n(f'finger{k}_mid'), (12.6, y2 - 1.3, z), (0.9, 2.8, 0.9), 'bone', rot=(0, 0, -22), pivot=(12.6, y2, z))
        box(s, H, n(f'claw{k}'), (11.9, y2 - 3.2, z), (0.7, 2.2, 0.7), 'claw', rot=(0, 0, -46), pivot=(12, y2 - 2.4, z))
    box(s, H, n('thumb'), (11.6, 21.8, -2.6), (1, 3, 1), 'bone', rot=(-24, 0, -20), pivot=(11.8, 23, -2.4))
    box(s, H, n('thumb_claw'), (11.3, 19.6, -3.6), (0.7, 2, 0.7), 'claw', rot=(-40, 0, -30), pivot=(11.4, 20.6, -3.2))

# ================================================================== greatsword (hand space: grip along z, blade along -z, flat = x)
box(1, 'sword', 'grip', (12.5, 23.5, 3.2), (1.6, 1.6, 11), 'leather', {'wrap'})
box(1, 'sword', 'pommel', (12.5, 23.5, 9.8), (2.6, 2.6, 2.4), 'skull_small', {'glow_eyes'})
box(1, 'sword', 'guard', (12.5, 23.5, -3.4), (2.8, 13, 1.8), 'patina', {'trim'})
for e in (1, -1):
    box(1, 'sword', f'guard_end{e}', (12.5, 23.5 + e * 7.4, -3.9), (2.4, 2.6, 1.8), 'patina', rot=(-22 * e, 0, 0), pivot=(12.5, 23.5 + e * 6.4, -3.4))
box(1, 'sword', 'blade', (12.5, 23.5, -4.3 - 37.5 / 2), (1.4, 9, 37.5), 'blade', {'battleworn'})

# ================================================================== solve the sword so it stands point-down, flat facing front
def rot_m(rr):
    rx, ry, rz = [math.radians(a) for a in rr]
    X = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Y = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Z = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return Z @ Y @ X
_b = {b['name']: b for b in BONES}
def world_R(name):
    ch = []
    while name: ch.append(name); name = _b[name]['parent']
    Rm = np.eye(3)
    for nm in reversed(ch): Rm = Rm @ rot_m(_b[nm]['rot'])
    return Rm
def world_pt(bname, p):
    p = np.array(p, float)
    while bname:
        b = _b[bname]; piv = np.array(b['pivot'], float)
        p = piv + rot_m(b['rot']) @ (p - piv); bname = b['parent']
    return p
def cube_corners(c):
    f0 = np.array(c['frm']); s = np.array(c['size'])
    crot = rot_m(c['rot']) if c['rot'] else None; cp = np.array(c['pivot']) if c['pivot'] else None
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                p = f0 + s * np.array([dx, dy, dz])
                if crot is not None: p = cp + crot @ (p - cp)
                yield world_pt(c['bone'], p)



# ================================================================== stand him on the ground
feet = [p[1] for c in CUBES if c['bone'].endswith('_foot') for p in cube_corners(c)]
dy = -min(feet)
for c in CUBES:
    c['frm'][1] += dy
    if c['pivot']: c['pivot'][1] += dy
for b in BONES: b['pivot'][1] += dy
SWORD_TIP = min(p[1] for c in CUBES if c['bone'] == 'sword' for p in cube_corners(c))
TOP = max(p[1] for c in CUBES for p in cube_corners(c))

HAND = world_pt('right_hand', (12.5, 23.5, 0))

def cube_corners_local(c):
    f0 = np.array(c['frm']); s = np.array(c['size'])
    crot = rot_m(c['rot']) if c['rot'] else None; cp = np.array(c['pivot']) if c['pivot'] else None
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                p = f0 + s * np.array([dx, dy, dz])
                yield cp + crot @ (p - cp) if crot is not None else p
