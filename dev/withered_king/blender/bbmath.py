"""Blockbench <-> Blender maths shared by the Blender scripts (mathutils only).
bb space: model pixels, y up, front = -z, right = +x.  Blender: metres (1 px = 1/8 m, like the game's
modelSize 2), z up, front = -y, right = -x.  G maps bb -> Blender and is a proper rotation + scale."""
import json, math, os
from mathutils import Matrix, Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
S = 0.125
G = Matrix(((-S, 0, 0, 0), (0, 0, S, 0), (0, S, 0, 0), (0, 0, 0, 1)))
GI = G.inverted()
D = json.load(open(os.path.join(HERE, 'king_data.json')))
BONES = {b['name']: b for b in D['bones']}
ORDER = [b['name'] for b in D['bones']]
WREST = {n: Matrix(b['wrest']) for n, b in BONES.items()}

def gp(p): return (G @ Vector((p[0], p[1], p[2], 1.0))).xyz
def bbp(v): return (GI @ Vector((v[0], v[1], v[2], 1.0))).xyz

def rot_bb(r):
    """bb euler degrees -> 3x3, R = Rz Ry Rx (same as Blender 'XYZ')."""
    return Euler([math.radians(a) for a in r], 'XYZ').to_matrix()

def local_bb(name, add_rot=(0, 0, 0), add_pos=(0, 0, 0)):
    """bb local transform of a bone: p -> piv + R (p - piv) + pos."""
    b = BONES[name]; piv = Vector(b['pivot'])
    R = rot_bb([b['rest'][k] + add_rot[k] for k in range(3)]).to_4x4()
    return Matrix.Translation(piv + Vector(add_pos)) @ R @ Matrix.Translation(-piv)

def frame_from(origin_local, origin_world, axes_local, axes_world):
    """rigid transform taking two local unit axes onto two world axes (Gram-Schmidt) and a local point onto a world point."""
    def basis(a, b):
        a = Vector(a).normalized(); b = Vector(b); b = (b - a * a.dot(b)).normalized(); c = a.cross(b)
        return Matrix((a, b, c)).transposed()
    R = basis(*axes_world) @ basis(*axes_local).inverted()
    t = Vector(origin_world) - R @ Vector(origin_local)
    return Matrix.Translation(t) @ R.to_4x4()
