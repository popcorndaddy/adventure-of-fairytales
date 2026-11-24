# The Withered Sentinel built from the user's own 3D model (meshy/user_glb/model.glb, decimated to work.blend):
# the mesh is split into the parts each bone carries, scaled onto the skeleton (S), turned into solid boxes (voxels
# merged greedily, hidden faces dropped) and later painted by projecting the model's own texture (sk_export.py).
# Executed inside sk_build.py after the armature exists (block/rig/COLS/GRIP available); replaces every armour block.
import numpy as np
from mathutils import Matrix, Vector

GLB_WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meshy", "user_glb", "work.blend")
K_RAW = 92.0 / 1.905                 # GLB units -> raw px (feet at 0, crest at 92)
Z_OFF = 0.953
S = 0.87                             # raw px -> skeleton px (joints line up: knee, elbow, wrist, belt, neck)
ARM_SHIFT, LEG_SHIFT = 1.4, 2.2      # the model's arms/legs stand a little wider than the skeleton: pull them in
VOX = 0.75                           # box grid, px (v16: finer, smoother surfaces)


def _glb_raw():
    with bpy.data.libraries.load(GLB_WORK) as (src, dst):
        dst.meshes = list(src.meshes)
    me = [m for m in bpy.data.meshes if len(m.vertices) > 100000][0]
    n = len(me.vertices); co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co)
    P = co.reshape(-1, 3) * K_RAW; P[:, 2] += Z_OFF * K_RAW
    me.calc_loop_triangles()
    tri = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
    return me, P, tri.reshape(-1, 3)


me_glb, P_raw, TRI = _glb_raw()
V = P_raw[TRI]                       # (T, 3, 3) raw px
C = V.mean(1)                        # centroids
x, y, z = C[:, 0], C[:, 1], C[:, 2]

# ---- the sword: the blade's main axis (PCA of the blade points), the grip where it meets the fist
bl = P_raw[(P_raw[:, 1] < -15) & (P_raw[:, 2] < 42) & (P_raw[:, 0] < -15)]
c0 = bl.mean(0); _, _, vt = np.linalg.svd(bl - c0); d_up = vt[0] * (1 if vt[0][2] > 0 else -1); n_flat = vt[2]
t_bl = (bl - c0) @ d_up
TIP = c0 + d_up * t_bl.min()
G_RAW = c0 + d_up * (t_bl.max() + 5.0)                      # grip: a fist's width above the top of the blade
rel = C - c0; along = rel @ d_up; dist = np.linalg.norm(rel - np.outer(along, d_up), axis=1)
zc = C[:, 2]
sword = (dist < np.where((zc > 34) & (zc < 47), 8.0, 9.0)) & (zc < 47) & ((x < -22) | (y < -14)) & (along < t_bl.max() + 9)

# ---- the cape: everything well behind the body, plus the rags flaring out at the sides
cape = (~sword) & (((y > 9.5) & (z < 74)) | ((y > 6.0) & (z < 45) & (np.abs(x) > 3)) | ((np.abs(x) > 23.5) & (z < 36)))

assign = np.full(len(C), "", dtype=object)
zs = z * S
for i in np.nonzero(sword)[0]:
    assign[i] = "sword"
for i in np.nonzero(cape)[0]:
    sd = "L" if x[i] * S > 5.5 else ("R" if x[i] * S < -5.5 else "M")
    seg = "root" if zs[i] > 61 else ("1" if zs[i] > 43.5 else ("2" if zs[i] > 24.5 else "3"))
    assign[i] = "cape_root" if seg == "root" else f"cape_{sd}{seg}"
rest = np.nonzero(assign == "")[0]
for i in rest:
    xi, yi, zi = x[i], y[i], z[i]; Sd = "L" if xi > 0 else "R"; zz = zi * S
    if zi > 73 and abs(xi) < 10.5:
        b = "head"
    elif abs(xi) > 10.5 and zi > 56:
        b = f"upperarm_{Sd}"
    elif (xi < -16.5 and 30 < zi <= 56) or (xi > 16.5 and 33 < zi <= 56 and yi < 6):
        b = f"upperarm_{Sd}" if zz > 47 else (f"forearm_{Sd}" if zz > 35 else f"hand_{Sd}")
    elif zi < 44:
        if abs(xi) < 4.5 and yi < -4:
            b = "tasset_F"                                       # the tabard hanging between the legs
        else:
            if zz > 22:
                b = f"thigh_{Sd}"
            elif zz > 6:
                b = f"shin_{Sd}"
            else:
                b = f"toe_{Sd}" if yi * S < -6.5 else f"foot_{Sd}"
    else:
        b = "pelvis" if zz < 44 else ("spine" if zz < 52 else ("chest" if zz < 64 else ("neck" if zz < 68 else "head")))
    assign[i] = b


def bone_map(b):
    """Affine (A, t) taking raw px to skeleton rest px for the parts bone b carries."""
    if b == "sword":
        # rigid: the model's grip -> the sword bone's head, blade -> -Y (rest), flat -> +Z
        fwd = Vector(tuple(-d_up)); nf = Vector(tuple(n_flat)); nf = (nf - fwd * nf.dot(fwd)).normalized()
        Bm = Matrix((fwd, nf, fwd.cross(nf))).transposed()
        Br = Matrix((Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, -1, 0)).cross(Vector((0, 0, 1))))).transposed()
        R = Br @ Bm.inverted()
        A = R * S
        t = Vector(GRIP) - A @ Vector(tuple(G_RAW))
        return A, t
    A = Matrix.Identity(3) * S
    t = Vector((0, 0, 0))
    return A, t


def shift_for(b, xs):
    if b.startswith(("upperarm", "forearm", "hand")):
        return np.where(xs < 0, ARM_SHIFT, -ARM_SHIFT)
    if b.startswith(("thigh", "shin", "foot", "toe")):
        return np.where(xs < 0, LEG_SHIFT, -LEG_SHIFT)
    return np.zeros_like(xs)


# ---- remove the hand-built armour; keep bones, FX anchors and collision helpers
for o in [o for o in bpy.data.objects if "sk_mat" in o]:
    bpy.data.objects.remove(o, do_unlink=True)

rng = np.random.default_rng(3)
N_BOX = 0
FACE_OF = {(0, -1): "east", (0, 1): "west", (1, -1): "north", (1, 1): "south", (2, -1): "down", (2, 1): "up"}
for b in sorted(set(assign)):
    idx = np.nonzero(assign == b)[0]
    A, t = bone_map(b)
    An = np.array(A); tn = np.array(t)
    W = V[idx] @ An.T + tn                                       # (n, 3, 3) rest px
    if b != "sword":
        W[:, :, 0] += shift_for(b, V[idx][:, :, 0])
    # surface samples: vertices + random points so every voxel the surface crosses is hit
    e1 = W[:, 1] - W[:, 0]; e2 = W[:, 2] - W[:, 0]
    area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
    k = np.minimum(np.ceil(area / (0.18 * VOX * VOX)).astype(int) + 1, 400)
    rep = np.repeat(np.arange(len(W)), k)
    u = rng.random(len(rep)); v = rng.random(len(rep)); flip = u + v > 1; u[flip] = 1 - u[flip]; v[flip] = 1 - v[flip]
    pts = np.concatenate([W[rep, 0] + e1[rep] * u[:, None] + e2[rep] * v[:, None], W.reshape(-1, 3)])
    lo = np.floor(pts.min(0) / VOX).astype(int) - 1
    ijk = np.floor(pts / VOX).astype(int) - lo
    dims = ijk.max(0) + 2
    occ = np.zeros(dims, bool); occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    # fill enclosed cavities: flood the outside, everything not outside is solid
    out = np.zeros_like(occ); out[0, :, :] = out[-1, :, :] = out[:, 0, :] = out[:, -1, :] = out[:, :, 0] = out[:, :, -1] = True
    out &= ~occ
    while True:
        g = out.copy()
        g[1:] |= out[:-1]; g[:-1] |= out[1:]; g[:, 1:] |= out[:, :-1]; g[:, :-1] |= out[:, 1:]; g[:, :, 1:] |= out[:, :, :-1]; g[:, :, :-1] |= out[:, :, 1:]
        g &= ~occ
        if (g == out).all():
            break
        out = g
    solid = ~out
    # smooth: drop lone bumps and fill pinholes (a 3x3x3 majority vote), keeping thin parts (cape, blade) intact
    if b not in ("sword",) and not b.startswith("cape"):
        pad = np.pad(solid, 1).astype(np.int16); cnt = np.zeros_like(solid, np.int16)
        for dx in (0, 1, 2):
            for dy in (0, 1, 2):
                for dz in (0, 1, 2):
                    cnt += pad[dx:dx + dims[0], dy:dy + dims[1], dz:dz + dims[2]]
        solid = (solid & (cnt >= 8)) | (~solid & (cnt >= 19))
    # greedy merge into boxes
    todo = solid.copy()
    Ainv = np.array(A.inverted()).ravel().tolist()
    for (i0, j0, k0) in zip(*np.nonzero(solid)):
        if not todo[i0, j0, k0]:
            continue
        i1 = i0 + 1
        while i1 < dims[0] and todo[i1, j0, k0]:
            i1 += 1
        j1 = j0 + 1
        while j1 < dims[1] and todo[i0:i1, j1, k0].all():
            j1 += 1
        k1 = k0 + 1
        while k1 < dims[2] and todo[i0:i1, j0:j1, k1].all():
            k1 += 1
        todo[i0:i1, j0:j1, k0:k1] = False
        hide = []
        for ax, lo_i, hi_i in ((0, i0, i1), (1, j0, j1), (2, k0, k1)):
            for sgn, edge in ((-1, lo_i - 1), (1, hi_i)):
                if edge < 0 or edge >= dims[ax]:
                    continue
                sl = [slice(i0, i1), slice(j0, j1), slice(k0, k1)]; sl[ax] = edge
                if solid[tuple(sl)].all():
                    hide.append(FACE_OF[(ax, sgn)])
        if len(hide) == 6:
            continue
        mn = (np.array([i0, j0, k0]) + lo) * VOX; mx = (np.array([i1, j1, k1]) + lo) * VOX
        o = block(b, tuple((mn + mx) / 2), tuple(mx - mn), "glb", coll="Sentinel_Weapon" if b == "sword" else "Sentinel_Armor")
        o["sk_hide"] = hide
        o["sk_Ainv"] = Ainv
        o["sk_t"] = list(t)
        o["sk_shift"] = float(shift_for(b, np.array([o.matrix_world.translation.x]))[0]) if b != "sword" else 0.0
        N_BOX += 1
    print("GLB bone", b, "tris", len(idx), "boxes so far", N_BOX, flush=True)

# the sword's length from the grip, for the animation checks; the off hand a fist below the grip
SWORD_LEN = float(S * np.linalg.norm(G_RAW - TIP))
GRIP_L_S = -5.0
print("GLB_OK boxes", N_BOX, "sword len", round(SWORD_LEN, 1), flush=True)
