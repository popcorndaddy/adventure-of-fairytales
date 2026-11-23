"""Export the Withered Sentinel rig (bones, rest transforms, textured cubes) to JSON for the Blender build."""
import sys, json, numpy as np
sys.path.insert(0, '/home/claude/wk2/py')
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import build3 as BB
import model3 as M, animtools as A
from model3 import rot_m

W0 = A.fk({})                                     # rest world transforms (bb px space): world = R p + t
def m4(R, t):
    m = np.eye(4); m[:3, :3] = R; m[:3, 3] = t; return m.round(6).tolist()

bones = []
for b in M.BONES:
    R, t = W0[b['name']]
    bones.append(dict(name=b['name'], parent=b['parent'], pivot=[float(v) for v in b['pivot']], rest=[float(v) for v in b['rot']],
                      wrest=m4(R, t), head=[float(v) for v in (R @ np.array(b['pivot'], float) + t)]))

def faces_of(c):
    f0 = np.array(c['frm'], float); s = np.array(c['size'], float); x0, y0, z0 = f0; x1, y1, z1 = f0 + s
    return {'north': [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
            'south': [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
            'east':  [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
            'west':  [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
            'up':    [(x1, y1, z1), (x0, y1, z1), (x0, y1, z0), (x1, y1, z0)],
            'down':  [(x1, y0, z0), (x0, y0, z0), (x0, y0, z1), (x1, y0, z1)]}
cubes = []
for i, c in enumerate(M.CUBES):
    R, t = W0[c['bone']]
    crot = rot_m(c['rot']) if c['rot'] else None; cp = np.array(c['pivot'], float) if c['pivot'] else None
    fs = []
    for fname, cs in faces_of(c).items():
        X, Y, w, h = BB.place[(i, fname)]
        pts = []
        for q in cs:
            p = np.array(q, float)
            if crot is not None: p = cp + crot @ (p - cp)
            pts.append([round(float(v), 5) for v in (R @ p + t)])
        uv = [(X, Y), (X + w, Y), (X + w, Y + h), (X, Y + h)]
        fs.append(dict(f=fname, p=pts, uv=uv))
    cubes.append(dict(name=c['name'], bone=c['bone'], mat=c['mat'], faces=fs))

# useful landmarks in bone-local (model) space
foot = {}
for side in ('right', 'left'):
    pts = np.array([p for c in M.CUBES if c['bone'] == f'{side}_foot' for p in M.cube_corners_local(c)])
    sole = pts[pts[:, 1] < pts[:, 1].min() + 0.35]          # the points that actually touch the floor
    foot[side] = dict(toe=[float(pts[:, 0].mean()), float(sole[:, 1].min()), float(sole[:, 2].min())],
                      heel=[float(pts[:, 0].mean()), float(sole[:, 1].min()), float(sole[:, 2].max())])
sw = np.array([p for c in M.CUBES if c['bone'] == 'sword' for p in M.cube_corners_local(c)])
tipc = sw[sw[:, 1] > -1e9]
data = dict(tex_w=BB.TW, tex_h=BB.TH, bones=bones, cubes=cubes, foot=foot,
            sword=dict(grip=[float(v) for v in M._b['sword']['pivot']]),
            materials=sorted(set(c['mat'] for c in M.CUBES)))
json.dump(data, open('/home/claude/wk2/bl/king_data.json', 'w'))
print('bones', len(bones), 'cubes', len(cubes), 'tex', BB.TW, BB.TH, foot)
# sword extent in sword-local space, along its blade axis
print('sword local min/max', sw.min(0).round(2), sw.max(0).round(2))
