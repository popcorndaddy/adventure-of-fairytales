"""Withered King post-process: skirt + cape strips solved against the body and ground, spring/pendulum secondary
motion for tabards, mantle drapes, hood drape and banner, wrist despike, key reduction.  Writes the final GeckoLib set.
python3 post.py king_baked.json king_final.json [names...]"""
import sys, json, math, os, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import rig2                                    # v2 skeleton (must come before model3 users)
import animtools as A, model3 as M, capes as CP
from model3 import rot_m
from scipy.optimize import minimize
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

def _pulse(t, a, b, hi, lo, ramp=0.15):
    if t < a - ramp or t > b + ramp: return lo
    if t < a: return lo + (hi - lo) * (t - a + ramp) / ramp
    if t > b: return hi + (lo - hi) * (t - b) / ramp
    return hi
FLARE = {'withered_king_idle': lambda t: 4 + 2 * math.sin(t / 6 * 2 * math.pi),
         'withered_king_walk_drag': lambda t: 9 + 3 * math.sin(t / 2.4 * 4 * math.pi),
         'withered_king_sweep': lambda t: _pulse(t, 0.95, 1.6, 18, 6),
         'withered_king_dash': lambda t: _pulse(t, 0.95, 1.45, 30, 6),
         'withered_king_phase_transition': lambda t: 5, 'withered_king_kneeling': lambda t: 3 + 1.5 * math.sin(t / 3 * 2 * math.pi),
         'withered_king_phase_two_roar': lambda t: _pulse(t, 3.0, 4.6, 20, 4, 0.1),
         'withered_king_hand_shockwave': lambda t: _pulse(t, 0.8, 1.3, 16, 5, 0.08),
         'withered_king_ground_stomp': lambda t: _pulse(t, 1.38, 1.7, 14, 5, 0.08),
         'withered_king_death': lambda t: 6 if t < 1.3 else 3}
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
DESPIKED = []
def despike(an, bones=('right_hand', 'left_hand', 'right_forearm', 'left_forearm', 'right_arm', 'left_arm', 'sword'), lim=85.0, win=4):
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
            DESPIKED.append((b, round(i / rate, 3), round(float(steps[i]), 1)))
    return fixed


# ------------------------------------------------------------------ secondary motion (mass on a rod, spring toward the
# animated hang + part gravity, damped; then pushed out of the legs and the floor)
SEC = {  # bone: (gravity share, natural freq Hz, damping ratio, max swing deg, collide with legs)
    'tabard_front': (0.55, 1.5, 0.30, 55, True), 'tabard_back': (0.55, 1.4, 0.30, 55, True),
    'tabard_left': (0.5, 1.6, 0.32, 45, True), 'tabard_right': (0.5, 1.6, 0.32, 45, True),
    'drape_left': (0.3, 2.6, 0.45, 30, False), 'drape_right': (0.3, 2.6, 0.45, 30, False),
    'hood_drape': (0.25, 2.6, 0.45, 25, False), 'banner': (0.0, 2.6, 0.35, 15, False)}
XLIM = {'drape_left': (-1, 30), 'drape_right': (-1, 30), 'hood_drape': (-25, 1)}   # one-sided: never swing into the chest / neck
G_PX = 78.0                                       # gravity in model px/s^2 (8 px per block)
LEG_BONES = ('right_leg', 'left_leg', 'right_shin', 'left_shin', 'right_foot', 'left_foot')
LEG_OBST = [c for c in M.CUBES if c['bone'] in LEG_BONES]
def leg_O(W):
    As, cs, lo, hi = [], [], [], []
    for c in LEG_OBST:
        Rb, tb = W[c['bone']]; Rc = rot_m(c['rot']) if c['rot'] else np.eye(3); pc = np.array(c['pivot']) if c['pivot'] else np.zeros(3)
        As.append(Rc.T @ Rb.T); cs.append(Rc.T @ (-Rb.T @ tb - pc) + pc); f0 = np.array(c['frm']); lo.append(f0 + 0.1); hi.append(f0 + np.array(c['size']) - 0.1)
    return np.array(As), np.array(cs), np.array(lo), np.array(hi)
SPTS = {b: np.array([p for c in M.CUBES if c['bone'] == b for p in M.cube_corners_local(c)]) for b in SEC}
def rot_to(d0, v, guess):
    f = lambda a: np.sum((rot_m((a[0], 0, a[1])) @ d0 - v) ** 2) + 1e-6 * (a[0] ** 2 + a[1] ** 2)
    r = minimize(f, guess, method='Nelder-Mead', options=dict(xatol=0.05, fatol=1e-9, maxiter=200)); return r.x
def secondary(an):
    n = len(an['bones']['body']['rot']); dt = 1.0 / an['rate']; loop = an['loop'] == 'loop'
    poses = [pose_at(an, k) for k in range(n)]
    for b in SEC:
        for p in poses: p[b] = {'rotation': (0, 0, 0), 'position': (0, 0, 0)}
    Ws = [A.fk(p) for p in poses]
    out = {}; report = {}
    for b, (gw, hz, zeta, lim, col) in SEC.items():
        piv = np.array(M._b[b]['pivot'], float); com = SPTS[b].mean(0); d0 = com - piv; L_ = np.linalg.norm(d0); d0 = d0 / L_
        w = 2 * math.pi * hz; down = np.array([0, -1.0, 0])
        def anchor(k): R, t = Ws[k][b]; return R @ piv + t, R @ d0, R
        cycles = 3 if loop else 1
        P0, D0, _ = anchor(0); x = P0 + L_ * D0; v = np.zeros(3); xs = []
        for c in range(cycles):
            for k in range(n):
                P, D, R = anchor(k)
                tgt = D * (1 - gw) + down * gw
                tgt = P + L_ * tgt / max(1e-6, np.linalg.norm(tgt))
                a = w * w * (tgt - x) - 2 * zeta * w * v
                v = v + a * dt; x = x + v * dt
                r = x - P; x = P + L_ * r / max(1e-6, np.linalg.norm(r)); v = v - np.dot(v, r) / (np.dot(r, r) + 1e-9) * r
                if c == cycles - 1: xs.append(x.copy())
        rots = []; g = np.zeros(2); hits_tot = 0
        for k in range(n):
            P, D, R = anchor(k); u = (xs[k] - P); u /= np.linalg.norm(u)
            g = rot_to(d0, R.T @ u, g); g = np.clip(g, -lim, lim)
            if b in XLIM: g[0] = min(max(g[0], XLIM[b][0]), XLIM[b][1])
            if col:
                W = Ws[k]; O = leg_O(W); Rp, tp = W[M._b[b]['parent']]
                def pts(a): Rl = rot_m((a[0], 0, a[1])); return (SPTS[b] - piv) @ (Rp @ Rl).T + Rp @ piv + tp
                def nh(a): P_ = pts(a); return CP.hits(P_, O) if True else 0
                h = nh(g)
                if h:
                    best = (h, 0.0, g)
                    for rr in range(4, 61, 4):
                        for dx, dz in ((rr, 0), (-rr, 0), (0, rr), (0, -rr), (rr * .7, rr * .7), (-rr * .7, rr * .7), (rr * .7, -rr * .7), (-rr * .7, -rr * .7)):
                            a2 = np.clip(g + (dx, dz), -lim - 25, lim + 25); h2 = nh(a2)
                            if h2 < best[0] or (h2 == best[0] and rr < best[1]): best = (h2, rr, a2)
                        if best[0] == 0: break
                    g = best[2]; hits_tot += best[0]
            rots.append([round(float(g[0]), 2), 0.0, round(float(g[1]), 2)])
        # smooth the collision corrections a touch (3-tap) without touching loop ends
        r = np.array(rots); sm = r.copy(); sm[1:-1] = (r[:-2] + 2 * r[1:-1] + r[2:]) / 4
        if loop: sm[0] = sm[-1] = (r[-2] + 2 * r[0] + r[1]) / 4
        out[b] = sm.round(2).tolist(); report[b] = (round(float(np.abs(sm).max()), 1), hits_tot)
    return out, report

def euler_unwrap(an):
    from scipy.spatial.transform import Rotation as R_
    for b, tr in an['bones'].items():
        if b not in M._b: continue
        rest = np.array(M._b[b]['rot'], float); r = np.array(tr['rot'], float)
        for k in range(1, len(r)):
            if np.abs(r[k] - r[k - 1]).max() > 90:
                r[k] = _euler_near(rot_m(r[k] + rest), r[k - 1] + rest) - rest
        tr['rot'] = r.round(3).tolist()

final = json.load(open(OUT)) if (ONLY and os.path.exists(OUT)) else {}
for name, an in BK.items():
    if ONLY and name not in ONLY: continue
    DESPIKED.clear(); nf = despike(an)
    if DESPIKED: print('  despike', DESPIKED, flush=True)
    sk = solve_skirt(an); an['bones']['skirt']['rot'] = sk
    sec, rep = secondary(an)
    for b, v in sec.items(): an['bones'][b] = {'rot': v, 'pos': [[0, 0, 0]] * len(v)}
    caps, worst = solve_capes(an, name, sk)
    for b, v in caps.items(): an['bones'][b] = {'rot': v, 'pos': [[0, 0, 0]] * len(v)}
    euler_unwrap(an)
    n = len(an['bones']['body']['rot']); rate = an['rate']; times = [k / rate for k in range(n)]
    bones = {}; nkeys = 0
    for b, tr in an['bones'].items():
        ch = {}
        for c, tol in (('rot', 0.12), ('pos', 0.015)):
            v = tr[c]
            if np.abs(np.array(v)).max() < 1e-3: continue
            idx = reduce(times, v, tol); ch['rotation' if c == 'rot' else 'position'] = [(round(times[i], 4), tuple(v[i])) for i in idx]; nkeys += len(idx)
        if ch: bones[b] = ch
    final[name] = dict(name=name, length=an['length'], loop=an['loop'], bones=bones, interp='linear', events=an.get('events', []))
    print(f'{name:32s} despiked {nf}  cape contact pts {worst}  secondary {rep}  keys {nkeys}', flush=True)
    json.dump(final, open(OUT, 'w'))
