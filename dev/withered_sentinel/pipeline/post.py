"""Post-process the Blender bake: solve the skirt (tabards/faulds) and the three cape strips against the body and floor,
reduce keys, and write the final GeckoLib animation set (anims_final.json) used by the builder."""
import sys, json, math, numpy as np
sys.path.insert(0, '/home/claude/boss')
import animtools as A, model3 as M, capes as CP
from model3 import rot_m
BK = json.load(open(sys.argv[1])); OUT = sys.argv[2]
ONLY = sys.argv[3:]
CUBES = M.CUBES
SKIRT = [i for i, c in enumerate(CUBES) if c['bone'] == 'skirt']
LEGS = [c for c in CUBES if c['bone'] in ('right_leg', 'left_leg', 'right_shin', 'left_shin')]
CORN = {i: np.array(list(M.cube_corners_local(CUBES[i]))) for i in SKIRT}
def pose_at(an, k, extra=None):
    p = {b: {'rotation': tuple(tr['rot'][k]), 'position': tuple(tr['pos'][k])} for b, tr in an['bones'].items()}
    if extra:
        for b, r in extra.items(): p[b] = {'rotation': tuple(r), 'position': p.get(b, {}).get('position', (0, 0, 0))}
    return p
def leg_obst(W):
    As, cs, lo, hi = [], [], [], []
    for c in LEGS:
        Rb, tb = W[c['bone']]; Rc = rot_m(c['rot']) if c['rot'] else np.eye(3); pc = np.array(c['pivot']) if c['pivot'] else np.zeros(3)
        As.append(Rc.T @ Rb.T); cs.append(Rc.T @ (-Rb.T @ tb - pc) + pc); f0 = np.array(c['frm']); lo.append(f0 + 0.3); hi.append(f0 + np.array(c['size']) - 0.3)
    return np.array(As), np.array(cs), np.array(lo), np.array(hi)
def skirt_cost(W, rx, rz):
    """floor and thigh penetration of the skirt if its additive rotation were (rx, 0, rz)."""
    b = M._b['skirt']; piv = np.array(b['pivot']); Rp, tp = W['body']
    R = rot_m(np.array(b['rot']) + (rx, 0, rz)); Rw = Rp @ R; tw = Rp @ (piv - R @ piv) + tp
    pts = np.concatenate([CORN[i] for i in SKIRT]) @ Rw.T + tw
    floor = np.clip(0.3 - pts[:, 1], 0, None).sum()
    As, cs, lo, hi = leg_obst(W)
    Q = np.einsum('nij,mj->nmi', As, pts) + cs[:, None, :]
    inside = np.all((Q > lo[:, None, :]) & (Q < hi[:, None, :]), axis=2).sum()
    return floor * 3 + inside * 0.6
def solve_skirt(an):
    n = len(an['bones']['body']['rot']); base = an['bones']['skirt']['rot']; out = []; prev = None
    for k in range(n):
        if k % 2 == 1 and k < n - 1: out.append(None); continue
        W = A.fk(pose_at(an, k)); bx, by, bz = base[k]; best = None
        for dx in range(-46, 31, 3):
            for dz in (-6, -3, 0, 3, 6):
                c = skirt_cost(W, bx + dx, bz + dz) + 0.004 * dx * dx + 0.01 * dz * dz
                if prev is not None: c += 0.02 * ((bx + dx - prev[0]) ** 2 + (bz + dz - prev[2]) ** 2)
                if best is None or c < best[0]: best = (c, (bx + dx, by, bz + dz))
        prev = best[1]; out.append(list(best[1]))
    for k in range(n):
        if out[k] is None: out[k] = [(a + b) / 2 for a, b in zip(out[k - 1], out[k + 1])]
    # light smoothing, keep loops seamless
    arr = np.array(out); sm = arr.copy()
    for k in range(n):
        idx = [(k + d) % n if an['loop'] == 'loop' else min(n - 1, max(0, k + d)) for d in (-2, -1, 0, 1, 2)]
        sm[k] = arr[idx].mean(0) * 0.7 + arr[k] * 0.3
    if an['loop'] == 'loop': sm[-1] = sm[0]
    return sm.round(3).tolist()

FLARE = {'walk': lambda t: 10 + 3 * math.sin(t / 2.4 * 4 * math.pi), 'dash': lambda t: 22 if 0.45 <= t <= 0.85 else (12 if 0.3 < t < 1.1 else 6),
         'sweep': lambda t: 16 if 1.15 <= t <= 1.7 else 6, 'idle': lambda t: 5 + 2 * math.sin(t / 6 * 2 * math.pi),
         'idle_combat': lambda t: 5 + 2 * math.sin(t / 3.2 * 2 * math.pi), 'awaken': lambda t: 14 if 2.0 <= t <= 2.9 else 5,
         'push': lambda t: 12 if 0.9 <= t <= 1.3 else 6, 'stomp': lambda t: 12 if 0.85 <= t <= 1.15 else 6, 'death': lambda t: 8 if t < 1 else 4,
         'summon_start': lambda t: 12 if 1.6 <= t <= 1.9 else 6}
def cape_frame(pose, flare, prev):
    W = A.fk(pose); O = CP.obstacles(W); Rc, tc = W['cape']; out = {}
    for up, low in CP.STRIPS.items():
        des_u = CP.hang_angle(Rc, flare)
        def evalc(au, al):
            Ru, tu = CP.local_T(up, au, 0); Rw_u, tw_u = Rc @ Ru, Rc @ tu + tc
            hu = CP.hits(CP.PTS[up] @ Rw_u.T + tw_u, O)
            des_l = CP.hang_angle(Rw_u, flare)
            Rl, tl = CP.local_T(low, al, 0); Rw_l, tw_l = Rw_u @ Rl, Rw_u @ tl + tw_u
            hl = CP.hits(CP.PTS[low] @ Rw_l.T + tw_l, O)
            pu, pl = prev.get(up, (des_u, 0))
            return 12 * (hu + hl) + 0.02 * (au - des_u) ** 2 + 0.02 * (al - des_l) ** 2 + 0.015 * (au - pu) ** 2 + 0.015 * (al - pl) ** 2, hu + hl
        if up in prev:
            pu, pl = prev[up]
            cands = [(pu + du, pl + dl) for du in range(-16, 17, 4) for dl in range(-18, 19, 6)]
        else:
            cands = [(au, al) for au in range(-70, 71, 6) for al in range(-100, 101, 8)]
        best = None
        for au, al in cands:
            c, h = evalc(au, al)
            if best is None or c < best[0]: best = (c, au, al, h)
        if best[3] > 0 and up in prev:     # stuck against something: widen the search once
            for au in range(-70, 71, 6):
                for al in range(-100, 101, 8):
                    c, h = evalc(au, al)
                    if c < best[0]: best = (c, au, al, h)
        out[up] = (best[1], best[2]); out[up + '_hits'] = best[3]
    return out

def solve_capes(an, name, skirt, dt=0.1):
    n = len(an['bones']['body']['rot']); rate = an['rate']; step = max(1, int(round(dt * rate)))
    ks = list(range(0, n, step))
    if ks[-1] != n - 1: ks.append(n - 1)
    prev = {}; tracks = {b: [] for b in [*CP.STRIPS, *CP.STRIPS.values()]}; worst = 0
    for k in ks:
        p = pose_at(an, k, {'skirt': skirt[k]})
        sol = cape_frame(p, FLARE.get(name, lambda t: 6)(k / rate), prev)
        for up, low in CP.STRIPS.items():
            au, al = sol[up]; prev[up] = (au, al); tracks[up].append((k, au)); tracks[low].append((k, al)); worst = max(worst, sol[up + '_hits'])
    full = {}
    for b, tr in tracks.items():
        kk = [k for k, _ in tr]; vv = [v for _, v in tr]
        vals = np.interp(np.arange(n), kk, vv)
        if an['loop'] == 'loop': vals[-1] = vals[0]
        full[b] = [[round(float(v), 2), 0.0, 0.0] for v in vals]
    return full, worst

def reduce(times, vals, tol):
    """Douglas-Peucker on a vector track (linear interpolation)."""
    vals = np.array(vals, float); keep = {0, len(times) - 1}
    def rec(i, j):
        if j <= i + 1: return
        t0, t1 = times[i], times[j]; u = (np.array(times[i + 1:j]) - t0) / (t1 - t0)
        interp = vals[i] + (vals[j] - vals[i]) * u[:, None]; err = np.abs(interp - vals[i + 1:j]).max(1)
        m = int(err.argmax())
        if err[m] > tol: keep.add(i + 1 + m); rec(i, i + 1 + m); rec(i + 1 + m, j)
    rec(0, len(times) - 1)
    return sorted(keep)

from scipy.spatial.transform import Rotation as Rot, Slerp
def _euler_near(R, ref):
    e = Rot.from_matrix(R).as_euler('xyz', degrees=True)
    alts = [e, np.array([e[0] + 180, 180 - e[1], e[2] + 180])]
    best = None
    for a in alts:
        a = ref + (a - ref + 180) % 360 - 180
        d = np.abs(a - ref).sum()
        if best is None or d < best[0]: best = (d, a)
    return best[1]
def despike(an, bones=('right_hand', 'left_hand', 'right_forearm', 'left_forearm', 'right_arm', 'left_arm', 'sword'), lim=40.0, win=4):
    rate = an['rate']; fixed = 0
    for b in bones:
        tr = an['bones'][b]['rot']; n = len(tr); rest = np.array(M._b[b]['rot'])
        Rs = Rot.from_euler('xyz', np.array(tr) + rest, degrees=True)
        steps = np.degrees((Rs[1:] * Rs[:-1].inv()).magnitude())
        bad = np.where(steps > lim)[0]
        if not len(bad): continue
        for i in bad:
            a, c = max(0, i - win), min(n - 1, i + 1 + win)
            key = Slerp([a, c], Rot.concatenate([Rs[a], Rs[c]]))
            for k in range(a + 1, c):
                u = (k - a) / (c - a); w = u * u * (3 - 2 * u)
                Rs_k = key([a + (c - a) * w])[0]
                tr[k] = list(np.round(_euler_near(Rs_k.as_matrix(), np.array(tr[k - 1]) + rest) - rest, 3))
            Rs = Rot.from_euler('xyz', np.array(tr) + rest, degrees=True); fixed += 1
    return fixed

final = json.load(open(OUT)) if (ONLY and __import__('os').path.exists(OUT)) else {}
for name, an in BK.items():
    if ONLY and name not in ONLY: continue
    nf = despike(an)
    sk = solve_skirt(an); an['bones']['skirt']['rot'] = sk
    caps, worst = solve_capes(an, name, sk)
    for b, v in caps.items(): an['bones'][b] = {'rot': v, 'pos': [[0, 0, 0]] * len(v)}
    n = len(an['bones']['body']['rot']); rate = an['rate']; times = [k / rate for k in range(n)]
    bones = {}; nkeys = 0
    for b, tr in an['bones'].items():
        ch = {}
        for c, tol in (('rot', 0.12), ('pos', 0.015)):
            v = tr[c]
            if np.abs(np.array(v)).max() < 1e-3: continue
            idx = reduce(times, v, tol); ch['rotation' if c == 'rot' else 'position'] = [(round(times[i], 4), tuple(v[i])) for i in idx]; nkeys += len(idx)
        if ch: bones[b] = ch
    final[name] = dict(name=name, length=an['length'], loop=an['loop'], bones=bones, interp='linear')
    print(f'{name:13s} despiked {nf}  skirt+capes solved (cape contact pts {worst})  keys {nkeys}', flush=True)
    json.dump(an, open(f'/home/claude/boss/qc/post_{name}.json', 'w'))
json.dump(final, open(OUT, 'w'))
