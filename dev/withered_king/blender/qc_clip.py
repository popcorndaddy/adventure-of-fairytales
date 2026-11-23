"""Interpenetration QC: deepest penetration (px) of sword / crown into the body, per action, plus foot sliding and ground clipping.
blender -b withered_king_anim.blend --python qc_clip.py -- [act,act..]"""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
import anim_lib as L
ONLY = sys.argv[sys.argv.index('--') + 1].split(',') if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1 else []
D = json.load(open(os.path.join(L.BM.HERE, 'king_data.json')))
def solid(c):
    faces = c['faces'] if isinstance(c['faces'], list) else list(c['faces'].values())
    pts = []; [pts.extend(Vector(p) for p in f['p']) for f in faces]
    ctr = sum(pts, Vector()) / len(pts)
    planes = []
    for f in faces:
        a, b, cc = (Vector(p) for p in f['p'][:3]); n = (b - a).cross(cc - a)
        if n.length < 1e-9: continue
        n.normalize()
        if n.dot(ctr - a) > 0: n = -n
        planes.append((a, n))
    return dict(bone=c['bone'], name=c['name'], pts=pts, planes=planes)
S = [solid(c) for c in D['cubes']]
CLOTH = ('cape', 'tabard', 'drape', 'banner', 'skirt', 'hood_drape')
HANDS = ('hand', 'finger', 'thumb', 'forearm')
BODY = [s for s in S if s['bone'] not in ('sword', 'crown') and not any(k in s['bone'] for k in CLOTH + HANDS)]
SW = [s for s in S if s['bone'] == 'sword']; CR = [s for s in S if s['bone'] == 'crown']
import numpy as np
def M4(K): return np.array([list(r) for r in K], float)
for s in S:
    P = np.array([list(p) for p in s['pts']]); s['P'] = np.concatenate([P, [(P[i] + P[j]) / 2 for i in range(len(P)) for j in range(i + 1, len(P))]])
    s['N'] = np.array([list(n) for a, n in s['planes']]); s['O'] = np.array([n.dot(a) for a, n in s['planes']])
def worst(A, B, Kc):
    best = (0, '', '')
    for a in A:
        Ka = Kc[a['bone']]; wp = a['P'] @ Ka[:3, :3].T + Ka[:3, 3]
        for b in B:
            Ki = Kc['_inv'][b['bone']]; q = wp @ Ki[:3, :3].T + Ki[:3, 3]
            d = (b['O'][None, :] - q @ b['N'].T).min(1)      # >0 inside, = distance to the nearest face
            m = float(d.max())
            if m > best[0]: best = (m, a['name'], b['name'])
    return best
rig = bpy.data.objects['Sentinel_Rig']; sc = bpy.context.scene
acts = sorted(a.name for a in bpy.data.actions if 'bb_length' in a and (not ONLY or a.name in ONLY))
bones = sorted({s['bone'] for s in S})
for act in acts:
    A = bpy.data.actions[act]; rig.animation_data.action = A
    try: rig.animation_data.action_slot = A.slots[0]
    except Exception: pass
    n = int(round(A['bb_length'] * L.FPS)); rep = {'sword>body': (0, 0, '', ''), 'crown>body': (0, 0, '', ''), 'body>crown': (0, 0, '', ''), 'body>sword': (0, 0, '', '')}
    ground = (0, 0); slide = {'L': 0.0, 'R': 0.0}; prevf = {}
    for f in range(0, n + 1):
        sc.frame_set(f); Kc = {b: M4(L.K_now(b)) for b in bones}; Kc['_inv'] = {b: np.linalg.inv(Kc[b]) for b in bones}
        for key, (a, b) in {'sword>body': (SW, BODY), 'body>sword': (BODY, SW), 'crown>body': (CR, [s for s in BODY if s['bone'] != 'head' or f / L.FPS > 5.5]),
                            'body>crown': ([s for s in BODY if s['bone'] != 'head' or f / L.FPS > 5.5], CR)}.items():
            d, na, nb = worst(a, b, Kc)
            if d > rep[key][0]: rep[key] = (d, f / L.FPS, na, nb)
        # ground: lowest non-sword vertex
        for s in S:
            if s['bone'] in ('sword',) or any(k in s['bone'] for k in CLOTH): continue
            K = Kc[s['bone']]; low = float((s['P'] @ K[:3, :3].T + K[:3, 3])[:, 1].min())
            if low < -ground[0] - 1e-6 and low < -0.15: ground = (-low, f / L.FPS)
        for side, bn in (('L', 'left_foot'), ('R', 'right_foot')):
            K = Kc[bn]; sole = np.concatenate([s['P'] for s in S if s['bone'] == bn]) @ K[:3, :3].T + K[:3, 3]
            lo = Vector(sole[sole[:, 1].argmin()])
            if lo.y < 0.08:
                if side in prevf and prevf[side][0] < 0.08:
                    dx = math.hypot(lo.x - prevf[side][1].x, lo.z - prevf[side][1].z)
                    slide[side] = max(slide[side], dx * L.FPS)
            prevf[side] = (lo.y, lo)
    print('QC', act, ' '.join('%s %.2fpx@%.2fs(%s/%s)' % (k, v[0], v[1], v[2], v[3]) for k, v in rep.items()),
          '| below-ground %.2fpx@%.2fs | planted-foot slide L %.1f R %.1f px/s' % (ground[0], ground[1], slide['L'], slide['R']))
