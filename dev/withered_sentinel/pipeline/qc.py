"""Numeric QC of baked Sentinel animations, using the exact Blockbench/GeckoLib maths the game uses."""
import sys, json, math, numpy as np
sys.path.insert(0, '/home/claude/boss')
import animtools as A, model3 as M
BK = json.load(open(sys.argv[1]))
only = sys.argv[2:]
CUBES = M.CUBES
CORN = {i: np.array(list(M.cube_corners_local(c))) for i, c in enumerate(CUBES)}
WALK_V = 14.0
def pose_at(an, k):
    return {b: {'rotation': tuple(tr['rot'][k]), 'position': tuple(tr['pos'][k])} for b, tr in an['bones'].items()}
def world(pose):
    W = A.fk(pose); out = {}
    for i, c in enumerate(CUBES):
        R, t = W[c['bone']]; out[i] = CORN[i] @ R.T + t
    return W, out
SOLE = {s: [i for i, c in enumerate(CUBES) if c['bone'] == f'{s}_foot'] for s in ('right', 'left')}
BODYC = [i for i, c in enumerate(CUBES) if c['bone'] not in ('sword',) and not c['bone'].endswith('_foot') and not c['bone'].startswith('cape')]
KNEEC = [i for i, c in enumerate(CUBES) if c['bone'].endswith('_shin') or c['bone'].endswith('_leg')]
SWORDC = [i for i, c in enumerate(CUBES) if c['bone'] == 'sword']
def rel_angle(Ra, Rb, Ra0, Rb0):
    d = (Ra.T @ Rb) @ (Ra0.T @ Rb0).T
    return math.degrees(math.acos(max(-1, min(1, (np.trace(d) - 1) / 2))))
W0 = A.fk({})
for name, an in BK.items():
    if only and name not in only: continue
    n = len(an['bones']['body']['rot']); rate = an['rate']; walk = name == 'walk'
    rep = dict(ground=(0, 0, ''), knee_ground=(9, 0), slide=(0, 0, ''), wrist=(0, 0, ''), knee_hyper=(999, 0, ''), pop=(0, 0, ''), sword_low=(9, 0))
    prev_contact = {s: None for s in SOLE}
    prevp = None
    for k in range(n):
        t = k / rate; pose = pose_at(an, k); W, P = world(pose)
        gi = min(BODYC, key=lambda i: P[i][:, 1].min()); gy = P[gi][:, 1].min()
        ky = min(P[i][:, 1].min() for i in KNEEC)
        if ky < rep['knee_ground'][0]: rep['knee_ground'] = (round(ky, 2), t)
        if gy < rep['ground'][0]: rep['ground'] = (round(gy, 2), t, CUBES[gi]['name'])
        sy = min(P[i][:, 1].min() for i in SWORDC)
        if sy < rep['sword_low'][0]: rep['sword_low'] = (round(sy, 2), t)
        for s in SOLE:
            pts = np.concatenate([P[i] for i in SOLE[s]]); low = pts[pts[:, 1] < pts[:, 1].min() + 0.4]
            cp = low.mean(0)
            if pts[:, 1].min() < 0.5:
                if prev_contact[s] is not None and prev_contact[s][0] == k - 1:
                    d = cp - prev_contact[s][1]; exp = np.array([0, 0, WALK_V / rate if walk else 0])
                    sl = float(np.hypot(*(d - exp)[[0, 2]])) * rate   # px/s off the expected ground motion
                    if sl > rep['slide'][0]: rep['slide'] = (round(sl, 2), t, s)
                prev_contact[s] = (k, cp)
            else: prev_contact[s] = None
        for s in ('right', 'left'):
            a = rel_angle(W[f'{s}_forearm'][0], W[f'{s}_hand'][0], W0[f'{s}_forearm'][0], W0[f'{s}_hand'][0])
            if a > rep['wrist'][0]: rep['wrist'] = (round(a, 1), t, s)
            hip = W[f'{s}_leg'][0] @ np.array(M._b[f'{s}_leg']['pivot']) + W[f'{s}_leg'][1]
            kn = W[f'{s}_shin'][0] @ np.array(M._b[f'{s}_shin']['pivot']) + W[f'{s}_shin'][1]
            an_ = W[f'{s}_foot'][0] @ np.array(M._b[f'{s}_foot']['pivot']) + W[f'{s}_foot'][1]
            v1, v2 = hip - kn, an_ - kn; ang = math.degrees(math.acos(np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2)))
            if ang < rep['knee_hyper'][0]: rep['knee_hyper'] = (round(ang, 1), t, s)
            if ang > rep.setdefault('knee_straight', (0, 0, ''))[0]: rep['knee_straight'] = (round(ang, 1), t, s)
        if prevp is not None:
            for b in an['bones']:
                if b.startswith('cape'): continue
                d = max(abs(x - y) for x, y in zip(an['bones'][b]['rot'][k], an['bones'][b]['rot'][k - 1])) * rate
                if d > rep['pop'][0]: rep['pop'] = (round(d), t, b)
                Rp = M.rot_m(np.array(M._b[b]['rot']) + an['bones'][b]['rot'][k - 1]); Rc = M.rot_m(np.array(M._b[b]['rot']) + an['bones'][b]['rot'][k])
                ra = math.degrees(math.acos(max(-1, min(1, (np.trace(Rp.T @ Rc) - 1) / 2)))) * rate
                if ra > rep.setdefault('spin', (0, 0, ''))[0]: rep['spin'] = (round(ra), t, b)
        prevp = pose
    seam = ''
    if an['loop'] == 'loop':
        def R_(b, r): return M.rot_m(np.array(M._b[b]['rot']) + np.array(r))
        mx = max(math.degrees(math.acos(max(-1, min(1, (np.trace(R_(b, tr['rot'][0]).T @ R_(b, tr['rot'][-1])) - 1) / 2)))) for b, tr in an['bones'].items())
        seam = f' seam {mx:.2f}deg'
    print(f"{name:13s} ground {rep['ground']} knee {rep['knee_ground']} swordlow {rep['sword_low']} slide {rep['slide']} wrist {rep['wrist']} knee bent/straight {rep['knee_hyper'][0]}/{rep['knee_straight'][0]} euler-rate {rep['pop']} true-rate {rep['spin']}{seam}")
