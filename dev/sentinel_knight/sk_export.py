"""Withered Sentinel (knight) - export the Blender build to GeckoLib: geo.json + painted texture atlas + glowmask,
and (with --anims) every action to animation.json (20 fps = ticks).

Geometry: every block (object with "sk_mat", rigidly parented to a bone) becomes one cube on that bone.
Coordinate conversion is the one proven in game by the Gatekeeper (gk_07_to_geckolib.py):
Blender (x, y, z) -> internal (-x, z, y); file x is the negated internal x; rotations R = Rz*Ry*Rx with file
angles (-x, -y, z).
Texture: each cube face gets its own region (4 texels per model px) painted procedurally for its material:
obsidian plate, gunmetal trim, iron ribs, engraved (non-glowing) runes, blade, grip wrap, the dark void and the
heart. Only the heart, its glow shell, the eyes and the faint inner chest wall are in the glowmask.

blender -b scene.blend --python sk_export.py -- <assets_kubejs_dir> [--anims]"""
import bpy, sys, os, json, math, random
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
ASSETS = os.path.abspath(args[0])
DO_ANIMS = "--anims" in args
NAME = "withered_sentinel"
scene = bpy.context.scene
rig = bpy.data.objects["Sentinel_Rig"]
for d in ("geo/entity", "animations/entity", "textures/entity"):
    os.makedirs(os.path.join(ASSETS, d), exist_ok=True)

M3 = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))
M3i = M3.transposed()
R6 = lambda v: round(v, 4)


def to_int(v):
    return M3 @ Vector(v)


def euler_zyx(R):
    m31 = max(-1.0, min(1.0, R[2][0]))
    ay = math.asin(-m31)
    if abs(m31) < 0.9999999:
        ax = math.atan2(R[2][1], R[2][2]); az = math.atan2(R[1][0], R[0][0])
    else:
        ax = 0.0; az = math.atan2(-R[0][1], R[1][1])
    return ax, ay, az


def file_rot(R_int):
    ax, ay, az = euler_zyx(R_int)
    return [round(-math.degrees(ax), 3), round(-math.degrees(ay), 3), round(math.degrees(az), 3)]


def file_rot_cont(R_int, prev):
    """Like file_rot, but of the equivalent Euler triples (x, y, z) / (x+180, 180-y, z+180), each +-360, it returns
    the one closest to the previous tick. GeckoLib blends Euler numbers between ticks, so a flip between two
    equivalent triples (e.g. 179 -> -179) would spin the bone for a frame even though both ticks are correct."""
    ax, ay, az = euler_zyx(R_int)
    if prev is None:
        e = (ax, ay, az)
    else:
        best = None
        for c in ((ax, ay, az), (ax + math.pi, math.pi - ay, az + math.pi)):
            w = [v + 2 * math.pi * round((p_ - v) / (2 * math.pi)) for v, p_ in zip(c, prev)]
            d = sum((v - p_) ** 2 for v, p_ in zip(w, prev))
            if best is None or d < best[0]:
                best = (d, w)
        e = tuple(best[1])
    return [round(-math.degrees(e[0]), 3), round(-math.degrees(e[1]), 3), round(math.degrees(e[2]), 3)], e


# ------------------------------------------------------------------ rest pose
saved_action = rig.animation_data.action if rig.animation_data else None
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ bones
bones_out = {}
for b in rig.data.bones:
    h = to_int(b.head_local * 16)
    e = {"name": b.name, "pivot": [R6(-h.x), R6(h.y), R6(h.z)]}
    if b.parent:
        e["parent"] = b.parent.name
    bones_out[b.name] = e

# ------------------------------------------------------------------ cubes + atlas allocation
TPX = 8                                     # texels per model pixel (v4: doubled for a high-res look)
SC = TPX // 4                               # scale for pixel-sized details authored at 4 texels/px
W, H = 4096, 2048
blocks = sorted([o for o in bpy.data.objects if "sk_mat" in o], key=lambda o: (o["sk_bone"], o.name))
# face order of the unit-cube mesh built in sk_build: 0 front(-Y) 1 back(+Y) 2 +X 3 -X 4 top 5 bottom
# file faces: north = -z_file = front, south = back, east = file -x side, west = file +x side
cubes = []
for o in blocks:
    M = o.matrix_world
    loc, quat, scl = M.decompose()
    sx, sy_b, sz_b = scl.x * 16, scl.y * 16, scl.z * 16          # Blender local x, y(depth), z(height)
    Rb = quat.to_matrix()
    e1, e2, e3 = Rb.col[0], Rb.col[1], Rb.col[2]
    Xi = -(M3 @ e1); Yi = M3 @ e3; Zi = M3 @ e2
    R = Matrix((Xi, Yi, Zi)).transposed()
    c = to_int(loc * 16)
    size = Vector((sx, sz_b, sy_b))                                  # file x, y(up), z(depth)
    frm = c - size / 2
    cube = {"origin": [R6(-(frm.x + size.x)), R6(frm.y), R6(frm.z)], "size": [R6(size.x), R6(size.y), R6(size.z)], "uv": {}}
    rot = file_rot(R)
    if any(abs(a) > 1e-3 for a in rot):
        cube["pivot"] = [R6(-c.x), R6(c.y), R6(c.z)]
        cube["rotation"] = rot
    cubes.append((o, cube, size))


class Shelf:
    def __init__(self):
        self.x = 0; self.y = 0; self.h = 0

    def alloc(self, w, h):
        if self.x + w > W:
            self.x = 0; self.y += self.h; self.h = 0
        if self.y + h > H:
            raise RuntimeError("atlas full")
        r = (self.x, self.y); self.x += w + 1; self.h = max(self.h, h + 1)
        return r


shelf = Shelf()
regions = []                        # (obj, face, x, y, w, h, mat)
faces_all = []
for o, cube, size in cubes:
    sx, sy, sz = size
    dims = {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}
    for face, (fw, fh) in dims.items():
        w, h = max(2, round(fw * TPX)), max(2, round(fh * TPX))
        faces_all.append((o, cube, face, w, h))
# shelf packing: all faces sorted by height (tallest first), so each shelf is filled with faces of similar height
for o, cube, face, w, h in sorted(faces_all, key=lambda q: (-q[4], -q[3])):
    x, y = shelf.alloc(w, h)
    cube["uv"][face] = {"uv": [x / TPX, y / TPX], "uv_size": [w / TPX, h / TPX]}
    regions.append((o, face, x, y, w, h, o["sk_mat"]))
used_h = shelf.y + shelf.h
print("ATLAS rows used", used_h, "of", H, flush=True)

for o, cube, size in cubes:
    bones_out[o["sk_bone"]].setdefault("cubes", []).append(cube)

# ------------------------------------------------------------------ painter
alb = np.zeros((H, W, 4), dtype=np.float32)
glw = np.zeros((H, W, 4), dtype=np.float32)
rnd = np.random.default_rng(7)
RUNES = [["..#..", ".#.#.", "#.#.#", "..#..", "..#..", "..#..", "..#.."],
         ["#.#.#", "#.#.#", ".###.", "..#..", "..#..", "..#..", "..#.."],
         ["..#..", ".#.#.", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
         ["#...#", "##.##", "#.#.#", "##.##", "#...#", "#...#", "#...#"],
         ["#....", "##...", "#.#..", "#..#.", "#.#..", "##...", "#...."],
         ["#...#", "##.##", "#.#.#", "#.#.#", "#.#.#", "##.##", "#...#"],
         ["....#", "...#.", "..#..", ".###.", "..#..", ".#...", "#...."]]


def noise(h, w, amp):
    return (rnd.random((h, w)) - 0.5) * 2 * amp


def bevel(t, hi, lo):
    t[0, :, :3] = np.minimum(t[0, :, :3] + hi, 1); t[:, 0, :3] = np.minimum(t[:, 0, :3] + hi * 0.6, 1)
    t[-1, :, :3] *= lo; t[:, -1, :3] *= lo


def cracks(t, n, col):
    h, w = t.shape[:2]
    for _ in range(n):
        y, x = rnd.integers(0, h), rnd.integers(0, w)
        for _ in range(rnd.integers(4, max(5, min(h, w)))):
            t[y, x, :3] = col
            y = int(np.clip(y + rnd.integers(-1, 2), 0, h - 1)); x = int(np.clip(x + rnd.integers(-1, 2), 0, w - 1))


def engrave(t, col, scale=1, count=1, vertical=True):
    h, w = t.shape[:2]
    gw, gh = 5 * scale, 7 * scale
    if w < gw + 4 or h < gh + 4:
        return
    n = max(1, min(count, (h - 4) // (gh + 3) if vertical else (w - 4) // (gw + 3)))
    for k in range(n):
        g = RUNES[rnd.integers(0, len(RUNES))]
        if vertical:
            x0 = (w - gw) // 2; y0 = 2 + k * (gh + 3) + ((h - 4) - n * (gh + 3)) // 2
        else:
            y0 = (h - gh) // 2; x0 = 2 + k * (gw + 3) + ((w - 4) - n * (gw + 3)) // 2
        for j, row in enumerate(g):
            for i, ch in enumerate(row):
                if ch == "#":
                    t[y0 + j * scale:y0 + (j + 1) * scale, x0 + i * scale:x0 + (i + 1) * scale, :3] = col
                    # a darker groove under each stroke reads as cut into the metal
                    yy, xx = y0 + (j + 1) * scale, x0 + i * scale
                    if yy < h and t[yy, xx, 0] > col[0] * 0.9:
                        pass
                    elif yy < h:
                        t[yy, xx:xx + scale, :3] *= 0.55


def paint(mat, w, h, face):
    t = np.zeros((h, w, 4), dtype=np.float32); t[..., 3] = 1
    g = np.zeros((h, w, 4), dtype=np.float32)
    if mat in ("obsidian", "rune"):
        base = np.array([0.045, 0.040, 0.062])
        t[..., :3] = base + noise(h, w, 0.012)[..., None]
        tint = (rnd.random((h, w)) < 0.04)
        t[tint, :3] = (0.075, 0.05, 0.105)                                   # deep violet sheen in the glass
        spec = (rnd.random((h, w)) < 0.012)
        t[spec, :3] = (0.17, 0.155, 0.22)                                    # glassy glints
        cracks(t, max(1, (w * h) // 900), (0.018, 0.015, 0.025))
        bevel(t, 0.09, 0.45)
        if mat == "rune" and face in ("north", "south", "east", "west"):
            engrave(t, np.array([0.16, 0.12, 0.22]), 1, count=3)
    elif mat == "gunmetal":
        t[..., :3] = np.array([0.115, 0.115, 0.13]) + noise(h, w, 0.01)[..., None]
        t[..., :3] += (np.sin(np.arange(w) * 1.7)[None, :, None] * 0.008)
        bevel(t, 0.12, 0.5)
        if w >= 10 and h >= 10:
            for (x, y) in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
                t[y, x, :3] = (0.3, 0.3, 0.33); t[y + 1, x, :3] = (0.04, 0.04, 0.05)
    elif mat == "iron":
        t[..., :3] = np.array([0.085, 0.08, 0.095]) + noise(h, w, 0.012)[..., None]
        bevel(t, 0.14, 0.4)
    elif mat == "blade":
        t[..., :3] = np.array([0.095, 0.095, 0.11]) + noise(h, w, 0.01)[..., None]
        if face in ("up", "down") and w >= 8:                                # flat of the blade: sharpened edges + fuller with runes
            t[:, :2, :3] = (0.30, 0.30, 0.34); t[:, -2:, :3] = (0.30, 0.30, 0.34)
            c0, c1 = w // 2 - max(2, w // 8), w // 2 + max(2, w // 8)
            t[:, c0:c1, :3] = (0.05, 0.045, 0.06)
            if c1 - c0 >= 5:
                sub = t[:, c0 - 1:c1 + 1]
                engrave(sub, np.array([0.17, 0.12, 0.24]), 1, count=99, vertical=True)
        cracks(t, max(1, (w * h) // 1500), (0.05, 0.05, 0.06))
    elif mat == "grip":
        yy, xx = np.mgrid[0:h, 0:w]
        band = ((xx + yy) // (3 * SC)) % 2 == 0
        t[..., :3] = np.where(band[..., None], np.array([0.10, 0.065, 0.05]), np.array([0.06, 0.04, 0.03]))
    elif mat == "void":
        t[..., :3] = (0.008, 0.006, 0.012)
    elif mat == "cavity":
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / max(w / 2, 1)) ** 2 + ((yy - h / 2) / max(h / 2, 1)) ** 2)
        k = np.clip(1 - r, 0, 1)[..., None]
        t[..., :3] = np.array([0.03, 0.01, 0.05]) + k * np.array([0.10, 0.02, 0.16])
        g[..., :3] = k * np.array([0.30, 0.06, 0.46]); g[..., 3] = (k[..., 0] > 0.05).astype(np.float32)
    elif mat == "heart":
        yy, xx = np.mgrid[0:h, 0:w]
        vein = ((xx * 3 + yy * 2) % 7 == 0) | ((xx + yy * 3) % 9 == 0)
        t[..., :3] = np.where(vein[..., None], np.array([0.98, 0.62, 1.0]), np.array([0.55, 0.08, 0.62]))
        g[..., :3] = np.where(vein[..., None], np.array([1.0, 0.75, 1.0]), np.array([0.72, 0.16, 0.95])); g[..., 3] = 1
    elif mat == "heart_glow":
        t[..., 3] = 0                                                        # invisible in the base pass
        g[..., :3] = (0.26, 0.05, 0.42); g[..., 3] = 1                       # additive glow volume
    elif mat == "eye":
        t[..., :3] = (0.42, 0.18, 0.7)
        g[..., :3] = (0.5, 0.2, 0.85); g[..., 3] = 1
    return t, g


# ------------------------------------------------------------------ Gatekeeper material set (v3 look)
TEXDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")


def load_tile(name):
    im = bpy.data.images.load(os.path.join(TEXDIR, f"GK_{name}.png"))
    a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(a)
    a = a.reshape(im.size[1], im.size[0], 4)[::-1].copy()
    bpy.data.images.remove(im)
    return a


GK = {k: load_tile(k) for k in ("AncientDarkIron_Albedo", "DarkSteel_Albedo", "WeatheredBronze_Albedo", "RuneStone_Albedo",
                                "RuneStone_Emission", "TatteredCloth_Albedo", "TatteredCloth_Emission", "PurpleEnergy_Albedo")}
MAG = 2 * SC                                # one Gatekeeper texel = half a model pixel (same scale as v3)


def sample(tile, w, h, mag=MAG, ox=None, oy=None):
    """Bilinear, wrapping sample of a 64x64 Gatekeeper tile: smooth instead of blown-up blocks."""
    th, tw = tile.shape[:2]
    ox = rnd.integers(0, tw) if ox is None else ox; oy = rnd.integers(0, th) if oy is None else oy
    fy = (np.arange(h) + 0.5) / mag - 0.5 + oy; fx = (np.arange(w) + 0.5) / mag - 0.5 + ox
    y0 = np.floor(fy).astype(int); x0 = np.floor(fx).astype(int)
    ty = (fy - y0)[:, None, None]; tx = (fx - x0)[None, :, None]
    Y0, Y1 = y0 % th, (y0 + 1) % th; X0, X1 = x0 % tw, (x0 + 1) % tw
    a = tile[Y0][:, X0]; b = tile[Y0][:, X1]; c = tile[Y1][:, X0]; d = tile[Y1][:, X1]
    out = (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty
    return out.astype(np.float32), ox, oy


def mottle(h, w, cell, amp):
    """Soft low-frequency variation (hammered, uneven metal)."""
    ch, cw = h // cell + 3, w // cell + 3
    tile = (rnd.random((ch, cw, 1)) - 0.5) * 2 * amp
    m, _, _ = sample(np.repeat(tile, 4, -1), w, h, mag=cell, ox=0, oy=0)
    return m[..., 0]


def grain(t, amp):
    t[..., :3] += (noise(t.shape[0], t.shape[1], amp))[..., None]


def wear(t, hi, lo, width=None):
    """Bevelled, worn edges: bright rim fading inward on top/left, shadowed bottom/right, chipped specks."""
    h, w = t.shape[:2]
    k = width or 2 * SC
    k = max(1, min(k, h // 3, w // 3))
    for i in range(k):
        f = 1 - i / k
        t[i, :, :3] += hi * f; t[:, i, :3] += hi * 0.6 * f
        t[h - 1 - i, :, :3] *= 1 - (1 - lo) * f; t[:, w - 1 - i, :3] *= 1 - (1 - lo) * f
    chips = rnd.random((h, w)) < 0.012
    edge = np.zeros((h, w), bool); edge[:k + 1] = True; edge[:, :k + 1] = True; edge[-k - 1:] = True; edge[:, -k - 1:] = True
    t[chips & edge, :3] += hi * 0.7


def scratches(t, n, hi, length=(6, 22)):
    """Thin bright scratches with a dark lip, the kind a long war leaves on plate."""
    h, w = t.shape[:2]
    if h < 6 or w < 6:
        return
    for _ in range(n):
        L = rnd.integers(length[0] * SC, length[1] * SC)
        ang = rnd.uniform(0, math.pi); dx, dy = math.cos(ang), math.sin(ang)
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        for s in range(L):
            xi, yi = int(x + dx * s), int(y + dy * s)
            if 0 <= xi < w and 0 <= yi < h:
                t[yi, xi, :3] += hi * (1 - abs(s / L - 0.5))
                if yi + 1 < h:
                    t[yi + 1, xi, :3] *= 0.8


def dents(t, n, depth=0.35):
    h, w = t.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(n):
        r = rnd.uniform(1.5, 4.0) * SC; cx, cy = rnd.uniform(0, w), rnd.uniform(0, h)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        k = np.clip(1 - d, 0, 1)
        lit = np.clip(((xx - cx) + (yy - cy)) / r, -1, 1)                   # light from the top left
        t[..., :3] *= (1 - depth * k * (0.5 + 0.5 * lit))[..., None]


def rivet(t, cx, cy, r, col=(0.30, 0.30, 0.34)):
    h, w = t.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    dome = d < 1
    shade = np.clip(1.15 - 0.9 * np.sqrt(((xx - cx + r * 0.35) ** 2 + (yy - cy + r * 0.35) ** 2)) / r, 0.25, 1.2)
    t[dome, :3] = (np.array(col)[None, :] * shade[dome][:, None])
    ring = (d >= 1) & (d < 1.35)
    t[ring, :3] *= 0.45                                                      # shadow ring


def soft_line_mask(dist, width):
    return np.clip(1 - np.abs(dist) / width, 0, 1)


def gk_paint(mat, w, h, face):
    g = np.zeros((h, w, 4), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    if mat in ("plate", "rune", "emblem"):
        t, ox, oy = sample(GK["AncientDarkIron_Albedo"], w, h)
        t[..., :3] = t[..., :3] * np.array([0.62, 0.6, 0.7]) + np.array([0.004, 0.0, 0.012])    # blackened, faintly violet
        t[..., 3] = 1
        t[..., :3] *= (1 + mottle(h, w, 6 * SC, 0.18))[..., None]
        grain(t, 0.012)
        dents(t, max(0, (w * h) // (900 * SC * SC)))
        scratches(t, max(1, (w * h) // (500 * SC * SC)), 0.07)
        wear(t, 0.11, 0.45)
        if mat == "rune" and face in ("north", "south", "east", "west"):
            em, _, _ = sample(GK["RuneStone_Emission"], w, h, ox=ox, oy=oy)
            v = np.clip((em[..., :3].max(-1) - 0.10) / 0.12, 0, 1)                  # smooth-edged glyph strokes
            t[..., :3] = t[..., :3] * (1 - v[..., None]) + np.array([0.20, 0.10, 0.30]) * v[..., None]
            under = np.roll(v, 1, axis=0) * (1 - v)
            t[..., :3] *= (1 - 0.5 * under)[..., None]                                 # cut-in shadow under each stroke
            g[..., :3] = v[..., None] * np.array([0.22, 0.07, 0.36]); g[..., 3] = (v > 0.02)
        if mat == "emblem" and face in ("north",):
            edge_d = np.minimum.reduce([xx - 1.5 * SC, (w - 1 - 1.5 * SC) - xx, yy - 1.5 * SC, (h - 1 - 1.5 * SC) - yy])
            chev_d = np.abs(xx - (w - 1) / 2) - yy * (w / 2) / max(h, 1) * 0.9
            v = np.maximum(soft_line_mask(edge_d, 0.9 * SC), soft_line_mask(chev_d, 0.9 * SC))
            halo = np.maximum(soft_line_mask(edge_d, 2.6 * SC), soft_line_mask(chev_d, 2.6 * SC))
            t[..., :3] = t[..., :3] * (1 - v[..., None]) + np.array([0.48, 0.2, 0.74]) * v[..., None]
            g[..., :3] = np.clip(v[..., None] * np.array([0.55, 0.2, 0.88]) + halo[..., None] * np.array([0.10, 0.03, 0.18]), 0, 1)
            g[..., 3] = (halo > 0.02)                                                  # glowing purple tracery with a soft halo
    elif mat == "trim":
        t, _, _ = sample(GK["DarkSteel_Albedo"], w, h)
        t[..., :3] *= 0.85; t[..., 3] = 1
        t[..., :3] += (np.sin(xx * 0.9 / SC + yy * 0.15) * 0.008)[..., None]          # brushed
        grain(t, 0.01)
        scratches(t, max(1, (w * h) // (700 * SC * SC)), 0.06, (4, 12))
        wear(t, 0.16, 0.42)
        if w >= 10 * SC and h >= 6 * SC:
            r = 1.1 * SC
            for (x, y) in ((2.5 * SC, 2.5 * SC), (w - 2.5 * SC, 2.5 * SC), (2.5 * SC, h - 2.5 * SC), (w - 2.5 * SC, h - 2.5 * SC)):
                rivet(t, x, y, r, (0.44, 0.44, 0.48))
    elif mat == "bronze":
        t, _, _ = sample(GK["WeatheredBronze_Albedo"], w, h); t[..., 3] = 1
        t[..., :3] *= (1 + mottle(h, w, 4 * SC, 0.2))[..., None]
        patina = mottle(h, w, 5 * SC, 1.0) > 0.45
        t[patina, :3] = t[patina, :3] * 0.6 + np.array([0.10, 0.16, 0.13]) * 0.4    # verdigris in the hollows
        grain(t, 0.015)
        wear(t, 0.16, 0.5)
    elif mat == "cloth":
        t, ox, oy = sample(GK["TatteredCloth_Albedo"], w, h)
        lum = t[..., :3].mean(-1, keepdims=True)
        t[..., :3] = np.array([0.20, 0.06, 0.32]) * (0.55 + 3.5 * lum)          # dyed deep purple
        weave = 0.92 + 0.08 * ((xx // SC + yy // SC) % 2)                         # fine twill
        t[..., :3] *= weave[..., None]
        t[..., :3] *= (1 + mottle(h, w, 5 * SC, 0.22))[..., None]               # folds and stains
        streak = mottle(w, 1, 3 * SC, 1.0)[:, 0] if w > 0 else 0
        t[..., :3] *= (1 - 0.18 * np.clip(streak, 0, 1))[None, :, None]         # threadbare vertical runs
        sp, _, _ = sample(GK["TatteredCloth_Emission"], w, h, ox=ox, oy=oy)
        v = np.clip((sp[..., :3].max(-1) - 0.3) / 0.2, 0, 1) * (rnd.random((h, w)) < 0.5)    # sparse, small glints of thread
        t[..., :3] = t[..., :3] * (1 - 0.6 * v[..., None]) + np.array([0.45, 0.2, 0.66]) * 0.6 * v[..., None]
        grain(t, 0.01)
        t[..., 3] = 1
        hem = 2 * SC
        t[-hem:, :, :3] *= 0.6
        fray = (rnd.random(w) < 0.35)
        t[-hem - SC:-hem, fray, :3] *= 0.7
    elif mat == "blade":
        t, _, _ = sample(GK["DarkSteel_Albedo"], w, h); t[..., 3] = 1
        t[..., :3] *= 1.15
        brush = noise(1, w, 0.03)                                                   # brushed along the length
        t[..., :3] += brush[..., None]
        grain(t, 0.008)
        if face in ("up", "down") and w >= 6:
            e = 2 * SC
            ramp = np.clip(1 - np.minimum(xx, w - 1 - xx) / (e * 1.6), 0, 1)
            t[..., :3] = t[..., :3] * (1 - ramp[..., None]) + np.array([0.66, 0.66, 0.72]) * ramp[..., None]   # honed bevels
            nick = (rnd.random(h) < 0.03)
            t[nick, :e // 2 + 1, :3] *= 0.5; t[nick, -(e // 2 + 1):, :3] *= 0.5
        scratches(t, max(1, (w * h) // (900 * SC * SC)), 0.05, (3, 8))
    elif mat == "energy":
        t, _, _ = sample(GK["PurpleEnergy_Albedo"], w, h); t[..., 3] = 1
        cx = np.abs(xx - (w - 1) / 2) / max(w / 2, 1); cy = np.abs(yy - (h - 1) / 2) / max(h / 2, 1)
        core = np.clip(1 - np.minimum(cx, 1) * 0.8, 0, 1)[..., None] if w <= h else np.clip(1 - np.minimum(cy, 1) * 0.8, 0, 1)[..., None]
        t[..., :3] = np.clip(t[..., :3] * (0.75 + 0.6 * core) + core * np.array([0.12, 0.05, 0.18]), 0, 1)   # hot core
        g[..., :3] = np.clip(t[..., :3] * 1.1, 0, 1); g[..., 3] = 1
    elif mat == "eye":
        t = np.zeros((h, w, 4), dtype=np.float32)
        cx = np.abs(xx - (w - 1) / 2) / max(w / 2, 1); cy = np.abs(yy - (h - 1) / 2) / max(h / 2, 1)
        k = np.clip(1 - np.maximum(cx, cy) * 0.6, 0, 1)[..., None]
        t[..., :3] = np.array([0.62, 0.30, 0.9]) + k * np.array([0.35, 0.3, 0.1]); t[..., 3] = 1
        g[..., :3] = np.clip(np.array([0.75, 0.4, 1.0]) + k * 0.25, 0, 1); g[..., 3] = 1
    else:
        return paint(mat, w, h, face)
    return np.clip(t, 0, 1), g


# ------------------------------------------------------------------ v5 colour scheme: dark purple plate, gold, neon gold
GAUNTLET = ("hand_", "forearm_", "index", "middle", "ring", "thumb")
BOOT = ("foot_", "toe_")
NEON = np.array([1.0, 0.76, 0.22])                     # neon gold (glowmask)
STUD = np.array([0.42, 0.12, 0.66])                    # purple studs


def recolour(t, tint, k0, k1):
    """Keep the tile's light/dark detail, give it a new colour: tint * (k0 + k1 * luminance)."""
    lum = t[..., :3].mean(-1, keepdims=True)
    t[..., :3] = np.array(tint) * (k0 + k1 * lum)


def neon_edges(g, w, h, inset, width, strength=1.0):
    """A thin glowing line running round a face, just inside its edge."""
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.minimum.reduce([xx - inset, (w - 1 - inset) - xx, yy - inset, (h - 1 - inset) - yy])
    v = soft_line_mask(d, width) * strength
    g[..., :3] = np.maximum(g[..., :3], v[..., None] * NEON); g[..., 3] = np.maximum(g[..., 3], (v > 0.02).astype(np.float32))
    return v


def studs(t, g, w, h, step, r):
    """Purple glowing studs spaced round the border of a face."""
    if w < 4 * r or h < 4 * r:
        return
    m = 2.2 * r
    pts = []
    for x in np.arange(m, w - m + 1e-6, step):
        pts += [(x, m), (x, h - 1 - m)]
    for y in np.arange(m + step, h - m - step + 1e-6, step):
        pts += [(m, y), (w - 1 - m, y)]
    yy, xx = np.mgrid[0:h, 0:w]
    for (cx, cy) in pts:
        rivet(t, cx, cy, r, tuple(STUD * 1.6))
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        k = np.clip(1.1 - d, 0, 1)
        g[..., :3] = np.maximum(g[..., :3], k[..., None] * STUD * 1.2); g[..., 3] = np.maximum(g[..., 3], (k > 0.02).astype(np.float32))


def scheme_paint(mat, bone, w, h, face, with_studs=True):
    side = face in ("north", "south", "east", "west")
    gold_piece = bone.startswith(GAUNTLET) or bone.startswith(BOOT)
    if mat in ("plate", "trim") and gold_piece:                          # gauntlets and boots: gold plate, purple studs
        t, _, _ = sample(GK["WeatheredBronze_Albedo"], w, h); t[..., 3] = 1
        recolour(t, (0.95, 0.68, 0.2), 0.35, 1.9 if mat == "plate" else 2.3)
        t[..., :3] *= (1 + mottle(h, w, 5 * SC, 0.14))[..., None]
        grain(t, 0.012); scratches(t, max(1, (w * h) // (700 * SC * SC)), 0.08, (4, 12)); wear(t, 0.18, 0.5)
        g = np.zeros((h, w, 4), dtype=np.float32)
        if with_studs:
            studs(t, g, w, h, 3.0 * TPX, 0.4 * TPX)
        return np.clip(t, 0, 1), g
    t, g = gk_paint(mat, w, h, face)
    if mat in ("plate", "rune", "emblem"):                               # dark purple armour
        recolour(t, (0.30, 0.12, 0.48), 0.25, 1.45)
        if mat == "rune" and side:                                       # carved glyphs now burn gold
            on = g[..., 3] > 0
            t[on, :3] = np.array([0.55, 0.38, 0.1]); g[on, :3] = g[on, :3].max(-1, keepdims=True) * 3.2 * NEON
        if mat == "emblem":                                              # chest tracery in neon gold
            on = g[..., 3] > 0
            t[on, :3] = np.array([0.85, 0.62, 0.2]) * np.clip(g[on, :3].max(-1, keepdims=True) * 1.6, 0.3, 1.0)
            g[on, :3] = g[on, :3].max(-1, keepdims=True) * 1.25 * NEON
    elif mat == "trim":                                                  # gold edging with a neon line
        recolour(t, (0.95, 0.7, 0.22), 0.3, 2.4)
        if side and min(w, h) >= 3 * SC:
            neon_edges(g, w, h, 0.9 * SC, 0.6 * SC, 0.8)
    elif mat == "bronze":                                                # buckles, fittings: bright gold
        recolour(t, (1.0, 0.75, 0.25), 0.35, 2.1)
    elif mat == "cloth":                                                 # cape and scarf: dark gold
        lum = t[..., :3].mean(-1, keepdims=True)
        t[..., :3] = np.array([0.5, 0.34, 0.05]) * (0.42 + 2.2 * lum)                # rich dark gold
        if side or face == "up":                                         # a bright gold thread along the edges
            yy, xx = np.mgrid[0:h, 0:w]
            d = np.minimum.reduce([xx - 1.0 * SC, (w - 1 - 1.0 * SC) - xx, yy - 1.0 * SC])
            v = soft_line_mask(d, 0.7 * SC)
            t[..., :3] = t[..., :3] * (1 - v[..., None]) + np.array([0.95, 0.72, 0.22]) * v[..., None]
    elif mat == "eye":                                                   # dark purple eyes, still glowing
        t[..., :3] = np.array([0.2, 0.03, 0.34]); g[..., :3] = np.array([0.3, 0.04, 0.58]); g[..., 3] = 1
    return np.clip(t, 0, 1), g


# ------------------------------------------------------------------ v6 knight patterns
GOLD = np.array([0.95, 0.7, 0.22]); GOLD_HI = np.array([1.0, 0.88, 0.5]); PURPLE = np.array([0.3, 0.12, 0.48]); DEEP = np.array([0.16, 0.05, 0.27])
FLEUR = ["......#......",
         ".....###.....",
         "....#####....",
         "....#####....",
         ".##..###..##.",
         "#..#.###.#..#",
         "#...#####...#",
         ".#..#####..#.",
         "..##.###.##..",
         "#############",
         "..##.###.##..",
         ".#...###...#.",
         ".....###.....",
         "....#####....",
         ".....###....."]
FLEUR_M = np.array([[c == "#" for c in row] for row in FLEUR], dtype=np.float32)


def stamp(t, g, mask_tpl, cx, cy, height, col, glow=None, outline=True):
    """Stamp a pixel motif (scaled, anti-aliased by supersampling) centred at cx, cy, `height` texels tall."""
    h, w = t.shape[:2]
    th, tw = mask_tpl.shape
    sc = height / th
    yy, xx = np.mgrid[0:h, 0:w]
    acc = np.zeros((h, w), np.float32)
    for oy in (0.25, 0.75):
        for ox in (0.25, 0.75):
            u = ((xx + ox - cx) / sc + tw / 2); v = ((yy + oy - cy) / sc + th / 2)
            ok = (u >= 0) & (u < tw) & (v >= 0) & (v < th)
            ui = np.clip(u.astype(int), 0, tw - 1); vi = np.clip(v.astype(int), 0, th - 1)
            acc += np.where(ok, mask_tpl[vi, ui], 0.0)
    m = acc / 4.0
    if outline:                                                          # a dark engraved edge round the motif
        sh = np.roll(np.roll(m, 1, 0), 1, 1)
        t[..., :3] *= (1 - 0.55 * np.clip(sh - m, 0, 1))[..., None]
    t[..., :3] = t[..., :3] * (1 - m[..., None]) + np.array(col) * m[..., None]
    if glow is not None:
        g[..., :3] = np.maximum(g[..., :3], m[..., None] * np.array(glow)); g[..., 3] = np.maximum(g[..., 3], (m > 0.05).astype(np.float32))
    return m


def fluting(t, w, h, period):
    """Gothic fluted plate: hammered vertical ridges catching the light."""
    xx = np.arange(w)
    ph = 2 * math.pi * xx / period
    t[..., :3] *= (1 + 0.16 * np.cos(ph) + 0.06 * np.cos(2 * ph))[None, :, None]
    groove = (np.abs(((xx + period / 2) % period) - period / 2) < 0.6)
    t[:, groove, :3] *= 0.62


def etched_border(t, g, w, h, inset, width):
    """Gilt etching: a dark band just inside the edge with a gold vine scrolling along it (damascened border)."""
    yy, xx = np.mgrid[0:h, 0:w]
    dx = np.minimum(xx - inset, (w - 1 - inset) - xx); dy = np.minimum(yy - inset, (h - 1 - inset) - yy)
    d = np.minimum(dx, dy)
    band = (d >= 0) & (d <= width)
    t[band, :3] = t[band, :3] * 0.45 + DEEP * 0.55
    per = width * 2.2; amp = width * 0.32
    along = np.where(dx < dy, yy, xx).astype(np.float32)               # run the vine along whichever edge is nearer
    centre = width / 2 + amp * np.sin(2 * math.pi * along / per)
    vine = band & (np.abs(d - centre) < max(0.9, width * 0.13))
    leaf = band & (((along + per / 4) % (per / 2)) < max(1.2, width * 0.18)) & (np.abs(d - width / 2) < width * 0.36)
    edge = (np.abs(d) < 0.8) | (np.abs(d - width) < 0.8)
    gold = vine | leaf | edge
    t[gold, :3] = GOLD * (0.8 + 0.2 * np.sin(along[gold] * 0.7))[:, None]
    g[gold, :3] = np.maximum(g[gold, :3], NEON * 0.28); g[gold, 3] = 1


def lames(t, g, w, h, period, rivet_r):
    """Articulated lames (overlapping bands) with a purple rivet at each end: gauntlets and sabatons."""
    yy = np.arange(h)
    ph = (yy % period) / period
    shade = 1.15 - 0.55 * ph                                             # each lame bright at its top, shadowed under the next
    t[..., :3] *= shade[:, None, None]
    edge = (yy % period) < 1.2
    t[edge, :, :3] = t[edge, :, :3] * 0.35 + GOLD_HI * 0.65
    if w >= 6 * rivet_r:
        for y0 in np.arange(period * 0.55, h - 1, period):
            for x0 in (2.6 * rivet_r, w - 1 - 2.6 * rivet_r):
                rivet(t, x0, y0, rivet_r, tuple(STUD * 1.7))
                yy2, xx2 = np.mgrid[0:h, 0:w]
                k = np.clip(1.15 - np.sqrt((xx2 - x0) ** 2 + (yy2 - y0) ** 2) / rivet_r, 0, 1)
                g[..., :3] = np.maximum(g[..., :3], k[..., None] * STUD); g[..., 3] = np.maximum(g[..., 3], (k > 0.02).astype(np.float32))


def rope(t, w, h, period):
    """Roped (twisted) edging on the gold trim."""
    yy, xx = np.mgrid[0:h, 0:w]
    s_ = ((xx + yy) % period) / period
    t[..., :3] *= (0.72 + 0.5 * np.sin(math.pi * s_))[..., None]


def breaths(t, w, h, slot_w, slot_h, gap):
    """Breathing slots of a great-helm visor."""
    yy, xx = np.mgrid[0:h, 0:w]
    cols = ((xx % (slot_w + gap)) < slot_w) & (xx > gap) & (xx < w - gap)
    rows = ((yy % (slot_h + gap)) < slot_h) & (yy > h * 0.45) & (yy < h - gap)
    hole = cols & rows
    t[hole, :3] = np.array([0.015, 0.008, 0.02])
    lip = np.roll(hole, -1, 0) & ~hole
    t[lip, :3] = t[lip, :3] * 0.5 + GOLD * 0.5


# the largest plate block of these bones carries a heraldic fleur-de-lis on its outer faces
FLEUR_BONES = ("upperarm_L", "upperarm_R", "tasset_F")
_big = {}
for o_ in blocks:
    if o_["sk_mat"] == "plate" and o_["sk_bone"] in FLEUR_BONES:
        vol = o_.matrix_world.to_scale().x * o_.matrix_world.to_scale().y * o_.matrix_world.to_scale().z
        if vol > _big.get(o_["sk_bone"], (0, None))[0]:
            _big[o_["sk_bone"]] = (vol, o_.name)
BIG = {v[1] for v in _big.values()}


def knight_paint(o, mat, w, h, face):
    bone = o["sk_bone"]
    # the breastplate is painted as plate (its fleur replaces the old chevron lines); lames bring their own rivets
    t, g = scheme_paint("plate" if mat == "emblem" else mat, bone, w, h, face, with_studs=False)
    side = face in ("north", "south", "east", "west")
    gold_piece = bone.startswith(GAUNTLET) or bone.startswith(BOOT)
    big = min(w, h) >= 4 * TPX
    if mat in ("plate", "trim") and gold_piece:
        g[...] = 0
        if side and h >= 2.5 * TPX:
            lames(t, g, w, h, 1.6 * TPX, 0.3 * TPX)
        else:
            rope(t, w, h, 1.0 * TPX)
    elif mat in ("plate", "emblem") and side:
        if big and bone not in ("head",):
            fluting(t, w, h, 2.2 * TPX)
        if min(w, h) >= 5 * TPX:
            etched_border(t, g, w, h, 0.5 * TPX, 1.1 * TPX)
        z = o.matrix_world.translation.z * 16
        if bone == "head" and face == "north" and z < 73.5 and w >= 4 * TPX:
            breaths(t, w, h, int(0.45 * TPX), int(0.3 * TPX), int(0.45 * TPX))
        if mat == "emblem" and face == "north":                          # the breastplate: a gold fleur-de-lis
            stamp(t, g, FLEUR_M, w / 2, h * 0.46, min(h * 0.5, w * 0.95), GOLD * 0.9, glow=NEON * 0.22)
        if o.name in BIG and face != "south" and min(w, h) >= 5 * TPX:
            stamp(t, g, FLEUR_M, w / 2, h / 2, min(w, h) * 0.62, GOLD * 0.9, glow=NEON * 0.2)
    elif mat == "trim":
        rope(t, w, h, 1.1 * TPX)
    elif mat == "cloth":
        lum = t[..., :3].mean(-1, keepdims=True)
        if side or face == "up":
            yy, xx = np.mgrid[0:h, 0:w]
            # semé-de-lis: small purple fleurs on a diamond grid over the dark gold
            step = 3.6 * TPX
            for j, cy in enumerate(np.arange(step / 2, h, step * 0.75)):
                for cx in np.arange(step / 2 + (step / 2 if j % 2 else 0), w, step):
                    stamp(t, g, FLEUR_M, cx, cy, 1.7 * TPX, PURPLE * 1.1, outline=False)
            if bone.startswith("cape_") and bone != "cape_root":         # a purple heraldic border down each panel edge
                d = np.minimum(xx, w - 1 - xx).astype(np.float32)
                if bone.endswith("3"):
                    d = np.minimum(d, (h - 1 - yy).astype(np.float32))
                band = d < 1.3 * TPX
                t[band, :3] = DEEP * (0.8 + 1.5 * lum[band])
                line = np.abs(d - 1.3 * TPX) < 0.6
                t[line, :3] = GOLD
    return np.clip(t, 0, 1), g


# ------------------------------------------------------------------ v7 scheme (from the user's reference): black crackled
# plate, thick gold rims, purple glowing vents, deep purple tattered cloth, gold skulls, purple crest and eyes
SKULL = ["...#####...",
         "..#######..",
         ".#########.",
         "###########",
         "##..###..##",
         "#...###...#",
         "##..###..##",
         "###########",
         ".####.####.",
         "..#######..",
         "..#.#.#.#..",
         "..#######..",
         "...#.#.#..."]
SKULL_M = np.array([[c == "#" for c in row] for row in SKULL], dtype=np.float32)
VIOLET = np.array([0.72, 0.28, 1.0])
BLACK_TINT = (0.27, 0.27, 0.31)                       # v9: dark gunmetal grey (was near-black)


def voronoi_cracks(t, w, h, cell):
    """Fine crackle over glossy black plate (thin pale lines with a dark core), like fired enamel."""
    n = max(3, int(w * h / (cell * cell)))
    pts = rnd.random((n, 2)) * np.array([w, h])
    yy, xx = np.mgrid[0:h, 0:w]
    d1 = np.full((h, w), 1e9, np.float32); d2 = np.full((h, w), 1e9, np.float32)
    for (px, py) in pts:
        d = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
        d2 = np.where(d < d1, d1, np.minimum(d2, d)); d1 = np.minimum(d1, d)
    edge = d2 - d1
    line = np.clip(1 - edge / 0.9, 0, 1)
    t[..., :3] = t[..., :3] * (1 - 0.6 * line[..., None]) + np.array([0.07, 0.07, 0.09]) * 0.6 * line[..., None]   # dark etched lines on steel


def black_plate(w, h, face):
    t, _, _ = sample(GK["AncientDarkIron_Albedo"], w, h); t[..., 3] = 1
    recolour(t, BLACK_TINT, 0.45, 1.9)
    if face in ("north", "south", "east", "west"):                       # glossy: a soft sheen across the upper part
        yy = np.arange(h)[:, None]
        t[..., :3] += (0.13 * np.exp(-((yy / max(h, 1) - 0.25) ** 2) / 0.02))[..., None] * np.array([0.9, 0.92, 1.0])   # silver sheen
    voronoi_cracks(t, w, h, 2.6 * TPX)
    grain(t, 0.01)
    wear(t, 0.2, 0.55)                                                   # bright silver on the worn edges
    return t


def gold_metal(w, h, k1=2.1):
    t, _, _ = sample(GK["WeatheredBronze_Albedo"], w, h); t[..., 3] = 1
    recolour(t, (0.86, 0.62, 0.2), 0.3, k1 * 0.88)
    t[..., :3] *= (1 + mottle(h, w, 4 * SC, 0.16))[..., None]
    grain(t, 0.012); wear(t, 0.14, 0.45)
    return t


def gold_rim(t, w, h, width):
    """A thick gold rim round the face with a jagged (chipped, toothed) inner edge."""
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy]).astype(np.float32)
    along = np.where(np.minimum(xx, w - 1 - xx) < np.minimum(yy, h - 1 - yy), yy, xx).astype(np.float32)
    teeth = width * (0.75 + 0.35 * np.abs(((along / (width * 1.6)) % 2) - 1)) + rnd.random((h, w)) * 0.8
    m = d < teeth
    gm = gold_metal(w, h)
    bev = np.clip(1.25 - d / np.maximum(teeth, 1) * 0.6, 0.6, 1.25)        # rounded: brighter at the outer edge
    t[m, :3] = gm[m, :3] * bev[m, None]
    inner = (d >= teeth) & (d < teeth + 1.2)
    t[inner, :3] *= 0.35                                                  # dark seam where the rim meets the plate
    return m


def vents(t, g, w, h, n, horizontal=True):
    """Glowing purple vents / seams."""
    yy, xx = np.mgrid[0:h, 0:w]
    if horizontal:
        for i in range(n):
            cy = h * (0.42 + 0.13 * i); m = (np.abs(yy - cy) < 0.2 * TPX) & (xx > w * 0.18) & (xx < w * 0.82)
            t[m, :3] = VIOLET * 0.55; g[m, :3] = VIOLET * 0.55; g[m, 3] = 1
    else:
        m = (np.abs(xx - w / 2) < 0.28 * TPX) & (yy > h * 0.15) & (yy < h * 0.85)
        t[m, :3] = VIOLET * 0.55; g[m, :3] = VIOLET * 0.6; g[m, 3] = 1
        halo = (np.abs(xx - w / 2) < 0.9 * TPX) & (yy > h * 0.15) & (yy < h * 0.85) & ~m
        g[halo, :3] = np.maximum(g[halo, :3], VIOLET * 0.25); g[halo, 3] = 1


def purple_cloth(w, h, face, bone):
    t, _, _ = sample(GK["TatteredCloth_Albedo"], w, h)
    lum = t[..., :3].mean(-1, keepdims=True)
    t[..., :3] = np.array([0.27, 0.07, 0.4]) * (0.42 + 2.4 * lum)
    t[..., 3] = 1
    yy, xx = np.mgrid[0:h, 0:w]
    t[..., :3] *= (1 - 0.35 * (yy / max(h, 1)) ** 2)[..., None]          # darker towards the hem
    grain(t, 0.01)
    if bone.endswith("3") and face in ("north", "south", "up", "down", "east", "west"):
        # tattered hem: ragged notches cut out of the bottom (alpha 0 = see-through in game)
        cut = (h - 1 - yy) < (1.2 * TPX * (0.5 + 0.5 * np.abs(np.sin(xx * 0.37) * np.cos(xx * 0.13 + 1.0))) + rnd.random(w)[None, :] * 0.9 * TPX)
        t[cut, 3] = 0.0
    return t


SKULL_BONES = {"shin_L", "shin_R"}
_kn = {}
for o_ in blocks:
    if o_["sk_mat"] == "plate" and o_["sk_bone"] in SKULL_BONES:
        z = o_.matrix_world.translation.z
        if z > _kn.get(o_["sk_bone"], (-1e9, None))[0]:
            _kn[o_["sk_bone"]] = (z, o_.name)                             # the top plate of the shin is the kneepad
KNEES = {v[1] for v in _kn.values()}
_sc = [o_ for o_ in blocks if o_["sk_mat"] == "cloth" and o_["sk_bone"] == "chest"]
SCARF = max(_sc, key=lambda o_: o_.matrix_world.to_scale().x * o_.matrix_world.to_scale().z).name if _sc else None


RIM_BONES = ("upperarm_L", "upperarm_R", "chest", "shin_L", "shin_R", "tasset_F", "tasset_L", "tasset_R", "tasset_B")


def scorch(t, w, h, reach, strength=0.7, bottom=1.6):
    """Burnt ends: soot creeping in from the edges (heaviest along the bottom), charred brown at the very rim."""
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.minimum.reduce([xx, w - 1 - xx, yy * 1.0, (h - 1 - yy) / bottom]).astype(np.float32)
    soot = np.exp(-d / reach) * (0.55 + 0.45 * mottle(h, w, max(2, int(reach)), 1.0).clip(-1, 1) * 0.5 + 0.45)
    soot = np.clip(soot, 0, 1)
    t[..., :3] *= (1 - strength * soot)[..., None]
    rim = np.exp(-d / (reach * 0.25))
    t[..., :3] = t[..., :3] * (1 - 0.35 * rim[..., None]) + np.array([0.16, 0.07, 0.03]) * 0.35 * rim[..., None]


def gouges(t, w, h, n_sets=1):
    """Deep parallel gouges from a blade or claw: a dark cut with a bright, scraped lip."""
    if min(w, h) < 3 * TPX:
        return
    for _ in range(n_sets):
        ang = rnd.uniform(0.5, 1.1) * (1 if rnd.random() < 0.5 else -1)
        dx, dy = math.cos(ang), math.sin(ang)
        x0, y0 = rnd.uniform(0.15 * w, 0.5 * w), rnd.uniform(0.2 * h, 0.6 * h)
        L = int(min(w, h) * rnd.uniform(0.55, 0.9))
        for k in range(3):
            ox, oy = -dy * k * 0.55 * TPX, dx * k * 0.55 * TPX
            for s_ in range(L):
                x, y = int(x0 + ox + dx * s_), int(y0 + oy + dy * s_)
                if 1 <= x < w - 1 and 1 <= y < h - 1:
                    t[y, x, :3] *= 0.25
                    t[y - 1, x, :3] = np.minimum(t[y - 1, x, :3] + 0.22, 1.0)


def helm_paint(o, mat, w, h, face):
    """The war helm: dark purple-black, light purple accents, dented, scratched, gouged and scorched by old fights."""
    g = np.zeros((h, w, 4), dtype=np.float32)
    t, _, _ = sample(GK["AncientDarkIron_Albedo"], w, h); t[..., 3] = 1
    if mat == "accent":
        recolour(t, (0.62, 0.42, 0.88), 0.5, 1.5)
    else:
        recolour(t, (0.2, 0.11, 0.29), 0.5, 2.0)
        if face in ("north", "south", "east", "west", "up"):
            yy = np.arange(h)[:, None]
            t[..., :3] += (0.05 * np.exp(-((yy / max(h, 1) - 0.2) ** 2) / 0.02))[..., None] * np.array([0.8, 0.7, 1.0])
    if o.name == "Grille":                                                # rebreather grille: vertical slots
        xx = np.arange(w)
        slot = ((xx % int(0.6 * TPX)) < int(0.3 * TPX))
        t[:, slot, :3] = np.array([0.02, 0.01, 0.03])
        t[:, ~slot, :3] = np.array([0.45, 0.3, 0.6]) * 0.7
        return np.clip(t, 0, 1), g
    dents(t, max(1, (w * h) // (500 * SC * SC)), 0.45)
    scratches(t, max(3, (w * h) // (110 * SC * SC)), 0.32, (3, 18))
    if face in ("north", "east", "west", "up"):
        gouges(t, w, h, 1 if min(w, h) < 6 * TPX else 2)
    scorch(t, w, h, 1.4 * TPX, 0.75)
    grain(t, 0.012)
    return np.clip(t, 0, 1), g


def marine_paint(o, mat, w, h, face):
    bone = o["sk_bone"]
    g = np.zeros((h, w, 4), dtype=np.float32)
    side = face in ("north", "south", "east", "west")
    big = min(w, h) >= 4 * TPX
    zc = o.matrix_world.translation.z * 16
    if o.name.startswith("Crest"):                                         # the crest: a stiff light purple plume
        t = purple_cloth(w, h, face, "x"); t[..., :3] = t[..., :3] * 1.9 + np.array([0.12, 0.08, 0.16])
        xx = np.arange(w)
        t[..., :3] *= (0.75 + 0.35 * np.abs(np.sin(xx * 1.3)))[None, :, None]
        return np.clip(t, 0, 1), g
    if bone == "head" and mat in ("plate", "trim", "accent", "iron"):
        return helm_paint(o, mat, w, h, face)
    if mat in ("plate", "emblem"):
        t = black_plate(w, h, face)
        if bone == "tasset_F" and o.name in BIG and face == "north":         # the front tabard: purple cloth, gold skull
            t = purple_cloth(w, h, face, "tasset_3")
            stamp(t, g, SKULL_M, w / 2, h * 0.42, min(w * 0.55, h * 0.3), GOLD * 0.95)
            return np.clip(t, 0, 1), g
        if side and big and bone in RIM_BONES:
            gold_rim(t, w, h, 0.55 * TPX)
        if mat == "emblem" and face == "north":                          # chest: vents and a gold skull
            vents(t, g, w, h, 3)
        if bone.startswith(("forearm", "shin")) and side and big and o.name not in KNEES:
            vents(t, g, w, h, 1, horizontal=False)
        if o.name.startswith("Knee_") and o.name.endswith("_2") and face == "up":   # knee dome: gold ring and skull
            yy, xx = np.mgrid[0:h, 0:w]
            r = np.sqrt((xx - w / 2) ** 2 + (yy - h / 2) ** 2); R0 = min(w, h) * 0.38
            ring = np.abs(r - R0) < 0.45 * TPX
            t[ring, :3] = GOLD
            stamp(t, g, SKULL_M, w / 2, h / 2, R0 * 1.15, GOLD * 0.95)
        if bone.startswith(("hand_",) + BOOT) and side and h >= 2.5 * TPX:  # articulated lames, gold-edged
            lames(t, g, w, h, 1.6 * TPX, 0.3 * TPX)
        return np.clip(t, 0, 1), g
    if mat == "rune":
        t = black_plate(w, h, face)
        if side:
            vents(t, g, w, h, 2)
        return np.clip(t, 0, 1), g
    if mat == "trim":
        t = gold_metal(w, h, 2.3)
        return np.clip(t, 0, 1), g
    if mat == "bronze":                                                  # belt buckle and fittings: gold, skull on the buckle
        t = gold_metal(w, h, 2.0)
        if o.name == "Buckle" and face == "up" and min(w, h) >= 2 * TPX:
            stamp(t, g, SKULL_M, w / 2, h / 2, min(w, h) * 0.8, np.array([0.35, 0.25, 0.08]))
        return np.clip(t, 0, 1), g
    if mat == "cloth":
        t = purple_cloth(w, h, face, bone)
        if o.name == SCARF and face == "north" and min(w, h) >= 3 * TPX:  # the scarf over his chest: one gold skull
            stamp(t, g, SKULL_M, w / 2, h * 0.5, min(w * 0.7, h * 0.75), GOLD * 0.95)
        if bone == "cape_M2" and face == "south":                           # the banner on his back: a gold skull
            stamp(t, g, SKULL_M, w / 2, h * 0.45, min(w * 0.6, h * 0.4), GOLD * 0.95)
        return np.clip(t, 0, 1), g
    if mat == "blade":                                                   # dark steel burning purple at the edges
        t, _, _ = sample(GK["DarkSteel_Albedo"], w, h); t[..., 3] = 1
        recolour(t, (0.22, 0.2, 0.28), 0.5, 1.6)
        yy, xx = np.mgrid[0:h, 0:w]
        e = np.minimum(xx, w - 1 - xx).astype(np.float32) / max(1.0, 0.9 * TPX)
        edge = np.clip(1.25 - e, 0, 1)                                    # glowing honed edges
        flame = np.clip(np.sin(yy * 0.21 + np.sin(yy * 0.05) * 3 + xx * 0.4) * 0.5 + 0.5, 0, 1) ** 4 * 0.45
        k = np.clip(edge + flame * (face in ("up", "down")), 0, 1)
        t[..., :3] = t[..., :3] * (1 - 0.6 * k[..., None]) + VIOLET * 0.75 * k[..., None]
        g[..., :3] = k[..., None] * VIOLET * 0.85; g[..., 3] = (k > 0.03).astype(np.float32)
        return np.clip(t, 0, 1), g
    if mat == "energy" and bone == "sword":                              # white-hot core of the blade
        t = np.zeros((h, w, 4), np.float32); t[..., 3] = 1
        xx = np.arange(w)[None, :]
        c = np.clip(1 - np.abs(xx - (w - 1) / 2) / max(w / 2, 1), 0, 1)
        t[..., :3] = (np.array([0.62, 0.36, 0.95]) + c[..., None] * np.array([0.38, 0.5, 0.05])).clip(0, 1)
        g[..., :3] = t[..., :3]; g[..., 3] = 1
        return np.clip(t, 0, 1), g
    if mat == "eye":
        t = np.zeros((h, w, 4), np.float32); t[..., :3] = (0.42, 0.1, 0.72); t[..., 3] = 1
        g[..., :3] = (0.5, 0.12, 0.92); g[..., 3] = 1
        return t, g
    return gk_paint(mat, w, h, face)


for (o, face, x, y, w, h, mat) in regions:
    t, g = marine_paint(o, mat, w, h, face)
    alb[y:y + h, x:x + w] = t
    glw[y:y + h, x:x + w] = g


def save(arr, path):
    img = bpy.data.images.new(os.path.basename(path), W, H, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).ravel())
    img.filepath_raw = path; img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)


save(alb, os.path.join(ASSETS, "textures/entity", f"{NAME}.png"))
save(glw, os.path.join(ASSETS, "textures/entity", f"{NAME}_glowmask.png"))
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": f"geometry.{NAME}", "texture_width": W // TPX, "texture_height": H // TPX,
                    "visible_bounds_width": 8, "visible_bounds_height": 8, "visible_bounds_offset": [0, 3.5, 0]},
    "bones": list(bones_out.values())}]}
json.dump(geo, open(os.path.join(ASSETS, "geo/entity", f"{NAME}.geo.json"), "w"), indent=1)
print("GEO_OK cubes", len(cubes), "bones", len(bones_out), flush=True)

# ------------------------------------------------------------------ animations
if DO_ANIMS:
    S = Matrix.Scale(16, 4); Si = Matrix.Scale(1 / 16, 4)
    order_b = [b.name for b in rig.data.bones]
    heads = {b.name: b.head_local * 16 for b in rig.data.bones}

    def world_delta():
        out = {}
        for pb in rig.pose.bones:
            Wm = pb.matrix @ pb.bone.matrix_local.inverted()
            out[pb.name] = S @ Wm @ Si
        return out

    anims = {}
    sampled = {}
    for act in sorted(bpy.data.actions, key=lambda a: a.name):
        if not act.get("sk_export", False):
            continue
        rig.animation_data_create(); rig.animation_data.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        tracks = {b: {"rotation": {}, "position": {}, "scale": {}} for b in order_b}
        prev_e = {b: None for b in order_b}
        def sample(fr, sub=0.0):
            """Pose of every bone at frame fr (+ subframe): (file rotation, prev euler), position, scale per bone."""
            scene.frame_set(fr, subframe=sub)
            Wd = world_delta(); out = {}
            for name in order_b:
                pb = rig.pose.bones[name]
                Q = (Wd[pb.parent.name].inverted() @ Wd[name]) if pb.parent else Wd[name].copy()
                loc, quat, scl = Q.decompose()
                p = heads[name]
                pos = (Q @ p) - p
                pi = M3 @ pos
                out[name] = (M3 @ quat.to_matrix() @ M3i, [R6(-pi.x), R6(pi.y), R6(pi.z)], [R6(scl.x), R6(scl.z), R6(scl.y)])
            return out

        def tkey(x):
            t = f"{x / 20.0:.5f}".rstrip("0").rstrip(".") if x > 0 else "0.0"
            return t if "." in t else t + ".0"

        n_mid = [0]

        def sample_t(t):
            fl = math.floor(t + 1e-9)
            return sample(int(fl), t - fl)

        def write(t, vals):
            for name in order_b:
                r_, pos_, scl_ = vals[name]
                tracks[name]["rotation"][tkey(t - f0)], prev_e[name] = file_rot_cont(r_, prev_e[name])
                tracks[name]["position"][tkey(t - f0)] = pos_
                tracks[name]["scale"][tkey(t - f0)] = scl_

        def span(ta, tb, depth=0):
            """Write keys from ta (already written) to tb. Where Euler numbers swing far (fast turns, or near gimbal
            lock) GeckoLib's straight blend between keys drifts from the true rotation, so such intervals are split
            in half (down to 1/8 tick) with keys sampled from the real, quaternion-interpolated motion."""
            vb = sample_t(tb)
            if depth < 3:
                trial = {n: file_rot_cont(vb[n][0], prev_e[n])[0] for n in order_b}
                last = {n: tracks[n]["rotation"][tkey(ta - f0)] for n in order_b}
                if max(max(abs(a_ - b_) for a_, b_ in zip(trial[n], last[n])) for n in order_b) > 25.0:
                    n_mid[0] += 1
                    tm = (ta + tb) / 2
                    span(ta, tm, depth + 1)
                    span(tm, tb, depth + 1)
                    return
            write(tb, vb)

        write(f0, sample(f0))
        for f in range(f0 + 1, f1 + 1):
            span(f - 1, f)
        if n_mid[0]:
            print("  sub-tick splits", act.name, n_mid[0], flush=True)
        lp = act.get("sk_loop", "false")
        sampled[act.name] = (tracks, (f1 - f0) / 20.0, lp)
    # a channel used by a bone in ANY animation is written in EVERY animation (even if it rests there), so no clip
    # ever inherits another clip's leftover pose (e.g. the dropped sword of death, the toes of the walk)
    used = set()
    for tracks, _, _ in sampled.values():
        for name, ch in tracks.items():
            for cname, keys in ch.items():
                ident = [1, 1, 1] if cname == "scale" else [0, 0, 0]
                if not all(all(abs(a - b) < 1e-3 for a, b in zip(v, ident)) for v in keys.values()):
                    used.add((name, cname))
    for an, (tracks, length, lp) in sampled.items():
        bones = {}
        for name, ch in tracks.items():
            o = {c: keys for c, keys in ch.items() if (name, c) in used}
            if o:
                bones[name] = o
        a = {"animation_length": round(length, 4), "bones": bones}
        if lp == "true":
            a["loop"] = True
        elif lp == "hold":
            a["loop"] = "hold_on_last_frame"
        anims[f"animation.{NAME}.{an}"] = a
        print("ANIM", an, a["animation_length"], "s", len(bones), "bones", flush=True)
    json.dump({"format_version": "1.8.0", "animations": anims},
              open(os.path.join(ASSETS, "animations/entity", f"{NAME}.animation.json"), "w"), separators=(",", ":"))
    print("ANIMS_OK", len(anims), flush=True)
if saved_action and rig.animation_data:
    rig.animation_data.action = saved_action
print("EXPORT_OK")
