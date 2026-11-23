"""Cape 'cloth': for every sampled frame of every animation, hang each cape strip with gravity and bend it
(upper + lower piece) out of the body, legs, armour, sword and ground. Writes capes.json."""
import sys, json, math, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import animtools as A, model3 as M
from model3 import rot_m

STRIPS = {'cape_mid': 'cape_mid_low', 'cape_left': 'cape_left_low', 'cape_right': 'cape_right_low'}
CAPE_BONES = {'cape', *STRIPS, *STRIPS.values()}
SKIP_MAT = {'cloth', 'drip', 'vine', 'wood', 'socket', 'eye', 'soul', 'edgeglow'}
OBST = [c for c in M.CUBES if c['bone'] not in CAPE_BONES | {'head', 'jaw'} and c['mat'] not in SKIP_MAT and not c['name'].startswith('shaft')]

def cube_local_pts(c, nu=3, nv=7):
    f0 = np.array(c['frm']); s = np.array(c['size']); pts = []
    for u in np.linspace(0.1, 0.9, nu):
        for v in np.linspace(0.05, 0.95, nv):
            if c['name'].endswith('_upper') and v > 0.85: continue      # top edge is sewn to the collar
            
            for w in (0.0, 1.0):
                pts.append(f0 + s * np.array([u, v, w]))
    pts = np.array(pts)
    if c['rot']:
        R = rot_m(c['rot']); p = np.array(c['pivot']); pts = (pts - p) @ R.T + p
    return pts
PTS = {b: np.concatenate([cube_local_pts(c) for c in M.CUBES if c['bone'] == b]) for b in [*STRIPS, *STRIPS.values()]}

def obstacles(W):
    As, cs, lo, hi = [], [], [], []
    for c in OBST:
        Rb, tb = W[c['bone']]
        Rc = rot_m(c['rot']) if c['rot'] else np.eye(3); pc = np.array(c['pivot']) if c['pivot'] else np.zeros(3)
        Ai = Rc.T @ Rb.T; ci = Rc.T @ (-Rb.T @ tb - pc) + pc
        As.append(Ai); cs.append(ci); f0 = np.array(c['frm']); lo.append(f0 + 0.12); hi.append(f0 + np.array(c['size']) - 0.12)
    return np.array(As), np.array(cs), np.array(lo), np.array(hi)

def hits(P, O):
    As, cs, lo, hi = O
    Q = np.einsum('nij,mj->nmi', As, P) + cs[:, None, :]
    inside = np.all((Q > lo[:, None, :] - 0.2) & (Q < hi[:, None, :] + 0.2), axis=2)   # half-unit cloth thickness
    return int(np.any(inside, axis=0).sum()) + int((P[:, 1] < -0.1).sum())

def local_T(bname, ax, az):
    R = rot_m((ax, 0, az)); p = np.array(M._b[bname]['pivot'], float)
    return R, p - R @ p

GRID = np.arange(-70, 71, 4.0)
HGRID = np.arange(-110, 111, 4.0)
def hang_angle(Rp, flare):
    target = np.array([0, -math.cos(math.radians(flare)), math.sin(math.radians(flare))])
    best = min(HGRID, key=lambda a: -((Rp @ np.array([0, -math.cos(math.radians(a)), -math.sin(math.radians(a))])) @ target))
    return float(best)

def solve_frame(pose, flare, prev):
    W = A.fk(pose); O = obstacles(W); Rc, tc = W['cape']; out = {}
    for up, low in STRIPS.items():
        des_u = hang_angle(Rc, flare)
        best = None
        for au in GRID:
            Ru, tu = local_T(up, au, 0); Rw_u, tw_u = Rc @ Ru, Rc @ tu + tc
            hu = hits(PTS[up] @ Rw_u.T + tw_u, O)
            des_l = hang_angle(Rw_u, flare) if True else 0
            for al in np.arange(-100, 101, 6.0):
                Rl, tl = local_T(low, al, 0); Rw_l, tw_l = Rw_u @ Rl, Rw_u @ tl + tw_u
                hl = hits(PTS[low] @ Rw_l.T + tw_l, O)
                pu, pl = prev.get(up, (des_u, 0))
                cost = 12 * (hu + hl) + 0.02 * (au - des_u) ** 2 + 0.02 * (al - des_l) ** 2 + 0.015 * (au - pu) ** 2 + 0.015 * (al - pl) ** 2
                if best is None or cost < best[0]: best = (cost, au, al, hu + hl)
        out[up] = (best[1], best[2]); out[up + '_hits'] = best[3]
    return out

def run(anims, flares, dt=0.1):
    res = {}
    for an in anims:
        bones = {b: ch for b, ch in an['bones'].items() if b not in CAPE_BONES}
        base = dict(an, bones=bones)
        ts = sorted(set([round(x, 3) for x in np.arange(0, an['length'] + 1e-6, dt)] + [k[0] for ch in bones.values() for ks in ch.values() for k in ks]))
        prev = {}; tracks = {b: [] for b in [*STRIPS, *STRIPS.values()]}; worst = 0
        for t in ts:
            fl = flares.get(an['name'], lambda t: 6)(t)
            sol = solve_frame(A.sample(base, t), fl, prev)
            for up, low in STRIPS.items():
                au, al = sol[up]; prev[up] = (au, al)
                tracks[up].append((t, (au, 0.0, 0.0))); tracks[low].append((t, (al, 0.0, 0.0)))
                worst = max(worst, sol[up + '_hits'])
        res[an['name']] = tracks
        print(f"{an['name']:12s} frames {len(ts):3d}  worst remaining contact points {worst}", flush=True)
    return res
