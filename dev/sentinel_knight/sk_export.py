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
order = sorted(range(len(cubes)), key=lambda i: -max(cubes[i][2].y, cubes[i][2].x, cubes[i][2].z))
for i in order:
    o, cube, size = cubes[i]
    sx, sy, sz = size
    dims = {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}
    for face, (fw, fh) in dims.items():
        w, h = max(2, round(fw * TPX)), max(2, round(fh * TPX))
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


for (o, face, x, y, w, h, mat) in regions:
    t, g = gk_paint(mat, w, h, face)
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
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            Wd = world_delta()
            t = f"{(f - f0) / 20.0:.4f}".rstrip("0").rstrip(".") if f > f0 else "0.0"
            if "." not in t:
                t += ".0"
            for name in order_b:
                pb = rig.pose.bones[name]
                Q = (Wd[pb.parent.name].inverted() @ Wd[name]) if pb.parent else Wd[name].copy()
                loc, quat, scl = Q.decompose()
                D = quat.to_matrix()
                p = heads[name]
                pos = (Q @ p) - p
                ri = M3 @ D @ M3i
                tracks[name]["rotation"][t], prev_e[name] = file_rot_cont(ri, prev_e[name])
                pi = M3 @ pos
                tracks[name]["position"][t] = [R6(-pi.x), R6(pi.y), R6(pi.z)]
                tracks[name]["scale"][t] = [R6(scl.x), R6(scl.z), R6(scl.y)]
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
