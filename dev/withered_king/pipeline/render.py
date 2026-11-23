"""Tiny software renderer for the model: orthographic, textured, painter's algorithm."""
import math, json, sys
import numpy as np
from PIL import Image, ImageDraw

def rot_m(r):
    rx, ry, rz = [math.radians(a) for a in r]
    X = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Y = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Z = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return Z @ Y @ X

def render(M, place, tex, pose=None, yaw=30, pitch=12, scale=6, size=(900, 1100), out='view.png', bg=(30, 30, 36), oy=0, ox=0):
    """pose: {bone: {'rotation': [x,y,z], 'position': [x,y,z]}} added on top of the rest pose."""
    pose = pose or {}
    bones = {b['name']: b for b in M.BONES}
    def bone_apply(bname, p):
        while bname:
            b = bones[bname]
            pr = pose.get(bname, {})
            r = [b['rot'][k] + pr.get('rotation', (0, 0, 0))[k] for k in range(3)]
            piv = np.array(b['pivot'], float)
            p = piv + rot_m(r) @ (p - piv)
            p = p + np.array(pr.get('position', (0, 0, 0)), float)
            bname = b['parent']
        return p
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    # camera looks at the model's front (-z side) from yaw degrees to its right, slightly above
    def view(p):
        x, y, z = p
        x2 = x * cy + z * sy; z2 = -x * sy + z * cy
        y2 = y * cp + z2 * sp; z3 = -y * sp + z2 * cp
        return np.array([x2, y2, z3])
    W, H = size
    img = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(img)
    quads = []
    T = np.asarray(tex)
    for i, c in enumerate(M.CUBES):
        f0 = np.array(c['frm'], float); s = np.array(c['size'], float); f1 = f0 + s
        crot = rot_m(c['rot']) if c['rot'] else None
        cpiv = np.array(c['pivot'], float) if c['pivot'] else None
        def P(x, y, z):
            p = np.array([x, y, z], float)
            if crot is not None: p = cpiv + crot @ (p - cpiv)
            return view(bone_apply(c['bone'], p))
        # face definitions: corners (top-left, top-right, bottom-right, bottom-left) as seen from outside
        x0, y0, z0 = f0; x1, y1, z1 = f1
        faces = {
            'north': [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
            'south': [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
            'east':  [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
            'west':  [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
            'up':    [(x1, y1, z1), (x0, y1, z1), (x0, y1, z0), (x1, y1, z0)],
            'down':  [(x1, y0, z0), (x0, y0, z0), (x0, y0, z1), (x1, y0, z1)],
        }
        for fname, cs in faces.items():
            pts = [P(*q) for q in cs]
            n = np.cross(pts[1] - pts[0], pts[3] - pts[0])
            if n[2] <= 0: continue        # facing away (camera looks toward -z in view space? toward +z)
            X, Y, w, h = place[(i, fname)]
            quads.append((np.mean([p[2] for p in pts]), pts, (X, Y, w, h), fname))
    quads.sort(key=lambda q: -q[0])
    shade = {'north': 1.0, 'south': 0.8, 'east': 0.88, 'west': 0.88, 'up': 1.1, 'down': 0.6}
    def scr(p): return (W / 2 - (p[0] - ox) * scale, H - 40 - (p[1] - oy) * scale)
    for depth, pts, (X, Y, w, h), fname in quads:
        a, b, cc, dd = [np.array(p) for p in pts]
        for ty in range(h):
            for tx in range(w):
                col = T[Y + ty, X + tx]
                if col[3] < 128: continue
                u0, u1, v0, v1 = tx / w, (tx + 1) / w, ty / h, (ty + 1) / h
                def L(u, v):
                    top = a + (b - a) * u; bot = dd + (cc - dd) * u
                    return top + (bot - top) * v
                poly = [scr(L(u0, v0)), scr(L(u1, v0)), scr(L(u1, v1)), scr(L(u0, v1))]
                k = shade[fname]
                d.polygon(poly, fill=tuple(int(min(255, col[j] * k)) for j in range(3)))
    img.save(out)
    return img
