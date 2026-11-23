"""Range-of-motion test: poses every joint through big but natural angles and reports blocks of one body part that
push into a block of a different part (parts that share a joint are allowed to touch at the joint core)."""
import sys, json, numpy as np, animtools as A, model3 as M
from model3 import rot_m
POSES = {
 'walk_stride': {'right_leg': {'rotation': (35, 0, 0)}, 'right_shin': {'rotation': (-25, 0, 0)}, 'left_leg': {'rotation': (-25, 0, 0)}, 'left_shin': {'rotation': (-45, 0, 0)},
                 'right_arm': {'rotation': (-20, 0, 0)}, 'left_arm': {'rotation': (25, 0, 0)}, 'left_forearm': {'rotation': (30, 0, 0)}, 'chest': {'rotation': (0, 8, 0)}},
 'kneel': {'body': {'rotation': (-5, 0, 0), 'position': (0, -12, 0)}, 'right_leg': {'rotation': (-10, 0, 0)}, 'right_shin': {'rotation': (-95, 0, 0)}, 'right_foot': {'rotation': (40, 0, 0)},
           'left_leg': {'rotation': (85, 0, 0)}, 'left_shin': {'rotation': (-85, 0, 0)}, 'chest': {'rotation': (-15, 0, 0)}, 'waist': {'rotation': (-10, 0, 0)}},
 'arms_forward': {'right_arm': {'rotation': (90, 0, 0)}, 'left_arm': {'rotation': (90, 0, 0)}, 'right_forearm': {'rotation': (30, 0, 0)}, 'left_forearm': {'rotation': (30, 0, 0)}},
 'arms_up': {'right_arm': {'rotation': (150, 0, 0)}, 'left_arm': {'rotation': (150, 0, 0)}, 'right_clavicle': {'rotation': (0, 0, 12)}, 'left_clavicle': {'rotation': (0, 0, -12)}},
 'arms_out': {'right_arm': {'rotation': (0, 0, 70)}, 'left_arm': {'rotation': (0, 0, -70)}, 'right_clavicle': {'rotation': (0, 0, 12)}, 'left_clavicle': {'rotation': (0, 0, -12)}},
 'elbows_flexed': {'right_arm': {'rotation': (20, 0, 0)}, 'right_forearm': {'rotation': (125, 0, 0)}, 'left_arm': {'rotation': (20, 0, 0)}, 'left_forearm': {'rotation': (125, 0, 0)}},
 'arms_across': {'right_arm': {'rotation': (60, 40, 0)}, 'right_forearm': {'rotation': (60, 0, 0)}, 'left_arm': {'rotation': (60, -40, 0)}, 'left_forearm': {'rotation': (60, 0, 0)}},
 'arms_back': {'right_arm': {'rotation': (-40, 0, 10)}, 'left_arm': {'rotation': (-40, 0, -10)}},
 'bow': {'waist': {'rotation': (-15, 0, 0)}, 'chest': {'rotation': (-20, 0, 0)}, 'neck': {'rotation': (-15, 0, 0)}, 'head': {'rotation': (-15, 0, 0)}},
 'twist_look': {'waist': {'rotation': (0, 15, 0)}, 'chest': {'rotation': (0, 25, 0)}, 'neck': {'rotation': (10, 25, 0)}, 'head': {'rotation': (15, 30, 8)}},
 'roar': {'chest': {'rotation': (15, 0, 0)}, 'neck': {'rotation': (15, 0, 0)}, 'head': {'rotation': (25, 0, 0)}, 'jaw': {'rotation': (30, 0, 0)},
          'right_arm': {'rotation': (0, 0, 35)}, 'left_arm': {'rotation': (0, 0, -35)}},
 'stomp_lift': {'left_leg': {'rotation': (80, 0, 0)}, 'left_shin': {'rotation': (-70, 0, 0)}, 'left_foot': {'rotation': (-10, 0, 0)}, 'chest': {'rotation': (8, 0, 0)}},
 'crouch': {'body': {'position': (0, -6, 0), 'rotation': (-10, 0, 0)}, 'right_leg': {'rotation': (55, 0, 0)}, 'right_shin': {'rotation': (-80, 0, 0)}, 'right_foot': {'rotation': (25, 0, 0)},
            'left_leg': {'rotation': (55, 0, 0)}, 'left_shin': {'rotation': (-80, 0, 0)}, 'left_foot': {'rotation': (25, 0, 0)}},
}
CORE = ('_core', 'shoulder_core', 'collar')
def solids(W):
    out = []
    for c in M.CUBES:
        R, t = W[c['bone']]
        Rc = rot_m(c['rot']) if c['rot'] else np.eye(3); pc = np.array(c['pivot']) if c['pivot'] else np.zeros(3)
        f0 = np.array(c['frm']); s = np.array(c['size'])
        out.append((c, R @ Rc, R @ (pc - Rc @ pc) + t, f0, s))
    return out
def chain(b):
    out = set()
    while b: out.add(b); b = M._b[b]['parent']
    return out
def related(a, b):
    """same bone, or parent/child (they meet at a joint)"""
    pa, pb = M._b[a]['parent'], M._b[b]['parent']
    return a == b or pa == b or pb == a
CLOTH = ('cape', 'tabard', 'drape', 'hood_drape', 'banner')
def check(pose, tol=0.25):
    W = A.fk(pose); S = solids(W); worst = []
    pts = []
    for c, R, t, f0, s in S:
        g = np.stack(np.meshgrid(*[np.linspace(0, 1, 3)] * 3, indexing='ij'), -1).reshape(-1, 3)
        pts.append((f0 + g * s) @ R.T + t)
    for i, (ci, Ri, ti, fi, si) in enumerate(S):
        for j, (cj, Rj, tj, fj, sj) in enumerate(S):
            if i == j or related(ci['bone'], cj['bone']): continue
            if any(k in ci['bone'] for k in CLOTH) or any(k in cj['bone'] for k in CLOTH): continue
            q = (pts[i] - tj) @ Rj                          # into j's cube space
            d = np.minimum(q - fj, fj + sj - q).min(1)      # depth inside j (>0 = inside)
            m = d.max()
            if m > tol: worst.append((round(float(m), 2), ci['name'], cj['name']))
    return sorted(worst, reverse=True)
if __name__ == '__main__':
    tot = 0
    for name, pose in POSES.items():
        w = check(pose); tot += len(w)
        print(f'{name:14s} {len(w):3d} contacts', w[:6])
    print('total', tot)
