"""Pose maths, a right-arm/sword solver and frame-sheet previews for the Withered Sentinel animations."""
import sys, math, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import model3 as M
from model3 import rot_m
from scipy.optimize import minimize

B = {b['name']: b for b in M.BONES}
REST = {n: np.array(b['rot'], float) for n, b in B.items()}

def fk(pose):
    """pose: {bone: {'rotation': xyz, 'position': xyz}} additive. returns {bone: (R, t)} with world = R@p + t"""
    out = {}
    def get(n):
        if n in out: return out[n]
        b = B[n]; pr = pose.get(n, {})
        R = rot_m(REST[n] + np.array(pr.get('rotation', (0, 0, 0)), float))
        piv = np.array(b['pivot'], float); pos = np.array(pr.get('position', (0, 0, 0)), float)
        # local: p -> piv + R(p-piv) + pos
        Rl, tl = R, piv - R @ piv + pos
        if b['parent']:
            Rp, tp = get(b['parent']); Rw, tw = Rp @ Rl, Rp @ tl + tp
        else: Rw, tw = Rl, tl
        out[n] = (Rw, tw); return out[n]
    for n in B: get(n)
    return out

PALM = np.array(B['right_hand']['pivot']) + np.array([0, -2.0, 0])   # grip centre in hand space
def sword_frame(pose):
    W = fk(pose); R, t = W['sword']
    grip = R @ np.array([12.5, B['sword']['pivot'][1], 0]) + t
    blade = R @ np.array([0, 0, -1.0]); flat = R @ np.array([1.0, 0, 0])
    return grip, blade, flat

def solve_arm(pose, grip_t, blade_t, flat_t=None, side='right', x0=None, wflat=0.5):
    """find additive rotations for <side>_arm (xyz), _forearm (x,y), _hand (xyz) so the grip/blade hit the targets"""
    blade_t = np.array(blade_t, float); blade_t /= np.linalg.norm(blade_t)
    if flat_t is not None: flat_t = np.array(flat_t, float); flat_t /= np.linalg.norm(flat_t)
    def mk(x):
        p = {k: dict(v) for k, v in pose.items()}
        p['right_arm'] = {'rotation': x[0:3]}; p['right_forearm'] = {'rotation': (x[3], x[4], 0)}
        p['right_hand'] = {'rotation': x[5:8]}
        return p
    def cost(x):
        g, b, f = sword_frame(mk(x))
        c = np.sum((g - grip_t) ** 2) + 60 * np.sum((b - blade_t) ** 2)
        if flat_t is not None: c += 60 * wflat * np.sum((f - flat_t) ** 2)
        fx = REST['right_forearm'][0] + x[3]
        c += 0.02 * max(0, fx - 140) ** 2 + 0.02 * max(0, -fx) ** 2           # elbow only bends one way
        c += 0.004 * (x[5] ** 2 + x[6] ** 2 + x[7] ** 2) + 0.002 * x[4] ** 2     # wrists prefer to stay straight
        if x0 is not None: c += 0.0015 * np.sum((x - x0) ** 2)                    # stay close to the previous key: smooth in-betweens
        return c
    best = None
    for s0 in ([x0] if x0 is not None else []) + [np.zeros(8), np.array([40, 0, 20, -40, 0, 0, 0, 0]), np.array([-40, 30, 40, -60, 0, 20, 0, 0])]:
        r = minimize(cost, s0, method='Powell', options={'maxiter': 20000, 'xtol': 1e-3, 'ftol': 1e-6})
        if best is None or r.fun < best.fun: best = r
    x = best.x; g, b, f = sword_frame(mk(x))
    return {'right_arm': tuple(np.round(x[0:3], 2)), 'right_forearm': (round(x[3], 2), round(x[4], 2), 0),
            'right_hand': tuple(np.round(x[5:8], 2))}, best.fun, g

def sample(an, t):
    pose = {}
    for bn, chans in an['bones'].items():
        pose[bn] = {}
        for ch, keys in chans.items():
            ks = sorted(keys, key=lambda k: k[0])
            if t <= ks[0][0]: v = ks[0][1]
            elif t >= ks[-1][0]: v = ks[-1][1]
            else:
                for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
                    if t0 <= t <= t1:
                        u = (t - t0) / (t1 - t0); u = u * u * (3 - 2 * u)
                        v = tuple(a + (b - a) * u for a, b in zip(v0, v1)); break
            pose[bn][ch] = v
    return pose

def sheet(an, times, out, yaw=30, pitch=8, scale=4.2, tex='withered_sentinel.png', size=(360, 400), oy=0):
    import build3 as BB, render
    from PIL import Image, ImageDraw
    T = Image.open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', 'blender', 'withered_king.png')).convert('RGBA')
    ims = []
    for t in times:
        im = render.render(BB.M, BB.place, T, pose=sample(an, t), yaw=yaw, pitch=pitch, scale=scale, size=size,
                           out='/tmp/fr.png', bg=(16, 24, 28), oy=oy)
        ImageDraw.Draw(im).text((8, 6), f'{an["name"]} {t:.2f}s', fill=(200, 235, 228)); ims.append(im)
    o = Image.new('RGB', (size[0] * len(ims), size[1]))
    for k, im in enumerate(ims): o.paste(im, (size[0] * k, 0))
    o.save(out); return out

def lowest(pose, bones):
    W = fk(pose); ys = []
    for c in M.CUBES:
        if c['bone'] not in bones: continue
        R, t = W[c['bone']]
        for p in M.cube_corners_local(c): ys.append((R @ p + t)[1])
    return min(ys)
