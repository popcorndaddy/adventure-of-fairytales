import json, math, uuid, base64, io, random, sys, os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
sys.path.insert(0, '/home/claude/wk2/py')
import model3 as M
import importlib
try:
    A = importlib.import_module(os.environ.get('WS_ANIMS', 'anims4'))
except ImportError:
    A = None

NAME = 'withered_sentinel'
D = 3                                   # texels per model unit
rng = random.Random(11)
nrng = np.random.default_rng(11)
OUT = os.environ.get('WS_OUT', '/home/claude/wk2/out'); os.makedirs(OUT, exist_ok=True)

GLOW_P1 = (38, 112, 106); GLOW_P2 = (96, 255, 232); GLOW_MASK = (120, 255, 240)
EYE_P1 = (92, 220, 206); EYE_P2 = (196, 255, 250)

FACES = ['north', 'east', 'south', 'west', 'up', 'down']
def face_dims(c, f):
    sx, sy, sz = [max(1, int(round(v * D))) for v in c['size']]
    return {'north': (sx, sy), 'south': (sx, sy), 'east': (sz, sy), 'west': (sz, sy), 'up': (sx, sz), 'down': (sx, sz)}[f]

items = []
for i, c in enumerate(M.CUBES):
    for f in FACES:
        w, h = face_dims(c, f); items.append((w, h, i, f))
items.sort(key=lambda t: (-t[1], -t[0]))
TW = 1024
x = y = shelf = 0; place = {}
for w, h, i, f in items:
    if x + w > TW: x = 0; y += shelf; shelf = 0
    place[(i, f)] = (x, y, w, h); x += w; shelf = max(shelf, h)
TH = 1
while TH < y + shelf: TH *= 2
print('atlas', TW, TH, 'rows used', y + shelf)

base = np.zeros((TH, TW, 4), np.uint8)
glow = np.zeros((TH, TW), bool); trim = np.zeros((TH, TW), bool); eyes = np.zeros((TH, TW), bool)

def smooth(h, w, sigma):
    n = gaussian_filter(nrng.random((h + 8, w + 8)), sigma)[4:-4, 4:-4]
    n -= n.min(); m = n.max()
    return n / m if m > 0 else n

def mix(img, mask, col, k=1.0):
    m = (mask * k)[..., None]
    img[:] = img * (1 - m) + np.array(col, float) * m

def edges(img, dark, light, w, h, side=True):
    if w < 3 or h < 3: return
    img[:, 0] = img[:, 0] * 0.8 + np.array(dark) * 0.2
    img[:, -1] = img[:, -1] * 0.8 + np.array(dark) * 0.2
    img[-1, :] = img[-1, :] * 0.7 + np.array(dark) * 0.3
    img[0, :] = img[0, :] * 0.8 + np.array(light) * 0.2
    if h > 6 and w > 6:
        img[1, 1:-1] = img[1, 1:-1] * 0.8 + np.array(light) * 0.2
        img[-2, 1:-1] *= 0.85

def crack_path(mask, w, h, length):
    x, y = rng.randrange(w), rng.randrange(max(1, h // 3))
    for _ in range(length):
        if 0 <= x < w and 0 <= y < h: mask[y, x] = True
        y += rng.choice((1, 1, 0)); x += rng.choice((-1, 0, 1))


_SIL = {}
def blade_sil(c):
    """battle-worn silhouette of a blade cube: S[z, y] with z=0 at the guard, y=0 at the low edge"""
    key = c['name']
    if key in _SIL: return _SIL[key]
    L = max(1, int(round(c['size'][2] * D))); W = max(1, int(round(c['size'][1] * D)))
    r = random.Random(77); S = np.ones((L, W), bool)
    zz, yy = np.mgrid[0:L, 0:W]
    # point: the last 16% tapers to a slightly off-centre tip
    t0 = int(L * 0.84)
    for z in range(t0, L):
        k = (L - 1 - z) / (L - 1 - t0)
        lo = int(round((W / 2 - 1) * (1 - k) * 1.05)); hi = W - int(round((W / 2 + 1) * (1 - k) * 0.95))
        S[z, :max(0, lo)] = False; S[z, min(W, hi):] = False
    # a snapped-off corner at the very point
    S[L - 3:, :] = False
    def notch(edge, zc, width, depth):
        for z in range(max(0, zc - width), min(L, zc + width + 1)):
            d = int(round(depth * (1 - abs(z - zc) / (width + 0.6)) + r.uniform(-0.6, 0.6)))
            if d <= 0: continue
            if edge == 0: S[z, :d] = False
            else: S[z, W - d:] = False
    for edge in (0, 1):
        z = r.randrange(6, 14)
        while z < t0 - 2:                                   # small chips all along both edges
            notch(edge, z, r.randrange(1, 4), r.uniform(1.2, 3.2)); z += r.randrange(6, 16)
    notch(1, int(L * 0.38), 5, 7.5)                        # two big bites taken out by heavy blows
    notch(0, int(L * 0.63), 4, 6)
    notch(0, int(L * 0.22), 2, 4)
    _SIL[key] = S
    return S

def paint(c, f, rect):
    X, Y, w, h = rect
    mat = c['mat']; fl = c['flags']; side = f in ('north', 'south', 'east', 'west')
    img = np.zeros((h, w, 3), float); alpha = np.full((h, w), 255, np.uint8)
    gl = np.zeros((h, w), bool); tr = np.zeros((h, w), bool); ey = np.zeros((h, w), bool)
    fine = nrng.normal(0, 1, (h, w, 1))
    if mat in ('patina', 'blade', 'barnacle'):
        if mat == 'patina':
            img += np.array((54, 58, 62), float) + fine * 5
            v = smooth(h, w, 3.0)
            mix(img, np.clip((v - 0.48) * 2.0, 0, 1), (58, 104, 98), 0.7)
            v2 = smooth(h, w, 1.4)
            mix(img, np.clip((v2 - 0.68) * 3, 0, 1), (96, 140, 124), 0.55)
            r = smooth(h, w, 1.4)
            mix(img, np.clip((r - 0.8) * 5, 0, 1), (120, 80, 52), 0.75)
            if side:                                          # verdigris drips
                for _ in range(max(1, w // 6)):
                    cx = rng.randrange(w); cy = rng.randrange(max(1, h // 2)); L = rng.randrange(3, max(4, h // 2))
                    for k in range(L):
                        if cy + k < h: img[cy + k, cx] = img[cy + k, cx] * 0.5 + np.array((90, 150, 130)) * 0.5 * (1 - k / L)
        elif mat == 'blade':
            img += np.array((86, 94, 98), float) + fine * 2.5
            v = smooth(h, w, 4.0)
            mix(img, np.clip((v - 0.45) * 2.0, 0, 1), (58, 108, 100), 0.7)
            r = smooth(h, w, 3.0)
            mix(img, np.clip((r - 0.78) * 4, 0, 1), (92, 70, 54), 0.55)
            if f in ('east', 'west'):                     # bright honed edges, darker toward the fuller
                prof = 1.12 - 0.22 * np.sin(np.linspace(0, math.pi, h))
                img *= prof[:, None, None]
        else:
            img += np.array((150, 144, 126), float) + fine * 6
        if mat != 'blade': edges(img, (24, 30, 32), (150, 170, 160), w, h)
        if side and h > 2: img *= (1.08 - 0.2 * np.linspace(0, 1, h))[:, None, None]
        if f == 'down': img *= 0.62
        if f == 'up': img *= 1.06
    elif mat in ('bone', 'skull', 'jaw', 'skull_small', 'bone_skull', 'bone_dark', 'teeth', 'skull_low'):
        img += np.array((180, 170, 146), float) + fine * 5
        v = smooth(h, w, 1.8)
        mix(img, np.clip((v - 0.55) * 2.5, 0, 1), (168, 152, 112), 0.6)
        img *= (0.9 + 0.12 * smooth(h, w, 3))[..., None]
        if side and w > 2:                                  # rounded look: darker toward both sides
            prof = 0.78 + 0.22 * np.sin(np.linspace(0.15, math.pi - 0.15, w))
            img *= prof[None, :, None]
        if f == 'down': img *= 0.62
        for _ in range(max(1, w * h // 160)):
            m = np.zeros((h, w), bool); crack_path(m, w, h, rng.randrange(3, 8)); img[m] *= 0.62
    elif mat == 'cloth':
        img += np.array((46, 46, 86), float) + fine * 4
        if side:
            ph = rng.random() * 6
            folds = 0.82 + 0.18 * np.sin(np.linspace(ph, ph + w / (2.2 * D) * math.pi, w))
            img *= folds[None, :, None]
            img *= (1.04 - 0.24 * np.linspace(0, 1, h))[:, None, None]
        v = smooth(h, w, 2)
        mix(img, np.clip((v - 0.6) * 2.5, 0, 1), (66, 56, 108), 0.6)
        if f == 'down': img *= 0.55
        if 'ragged' in fl and side:
            col = 0
            while col < w:
                run = rng.randrange(1, 4); depth = rng.randrange(0, max(1, int(h * 0.28)))
                if depth: alpha[h - depth:, col:col + run] = 0
                col += run
        if 'holes' in fl and f in ('north', 'south'):
            for _ in range(max(1, w * h // 220)):
                hx, hy = rng.randrange(1, max(2, w - 2)), rng.randrange(2, max(3, h - 6))
                alpha[hy:hy + rng.randrange(1, 4), hx:hx + rng.randrange(1, 3)] = 0
    elif mat == 'leather':
        img += np.array((82, 58, 42), float) + fine * 6
        if 'wrap' in fl:
            for yy in range(h):
                for xx in range(w):
                    if (xx + yy) % 4 == 0: img[yy, xx] *= 0.7
        if 'studs' in fl and side:
            for sx in range(2, w - 1, 5): img[h // 2, sx] = (110, 120, 118)
        edges(img, (40, 28, 20), (110, 82, 60), w, h)
    elif mat == 'claw':
        img += np.array((92, 82, 66), float) + fine * 5
        img *= (1.0 - 0.35 * np.linspace(0, 1, h))[:, None, None]
    elif mat == 'wood':
        img += np.array((76, 56, 38), float) + fine * 5
        for xx in range(0, w, 2): img[:, xx] *= 0.82
        edges(img, (34, 24, 16), (100, 76, 52), w, h)
    elif mat == 'vine':
        img += np.array((70, 92, 36), float) + fine * 10
        img[nrng.random((h, w)) < 0.25] = (104, 126, 48)
    elif mat == 'socket':
        img += np.array((10, 9, 11), float) + fine * 2
    elif mat == 'eye':
        img += np.array((60, 160, 150), float); ey[:] = True
    elif mat in ('drip', 'edgeglow'):
        img += np.array((24, 60, 58), float); gl[:] = True
    elif mat == 'soul':
        img += np.array((60, 160, 150), float); ey[:] = True
    # --- decorations
    if 'moss' in fl:
        mc = [(84, 102, 40), (112, 128, 50), (66, 84, 34)]
        if side:
            for _ in range(max(1, w // 4)):
                cx = rng.randrange(w); L = rng.randrange(2, max(3, int(h * 0.45)))
                for k in range(L):
                    if k < h: img[k, cx] = mc[rng.randrange(3)]
                    if rng.random() < 0.25 and cx + 1 < w and k < h: img[k, cx + 1] = mc[0]
        elif f == 'up':
            v = smooth(h, w, 1.5); m = v > 0.62
            img[m] = np.array(mc[1]) * 0.7 + img[m] * 0.3
    if 'barnacles' in fl and f in ('north', 'up', 'east', 'west', 'south'):
        for _ in range(1 if rng.random() < 0.6 else 0):
            bx, by = rng.randrange(w), rng.randrange(h)
            for _ in range(rng.randrange(3, 7)):
                x0, y0 = bx + rng.randrange(-3, 4), by + rng.randrange(-3, 4)
                for dx in (0, 1):
                    for dy in (0, 1):
                        if 0 <= x0 + dx < w and 0 <= y0 + dy < h: img[y0 + dy, x0 + dx] = img[y0 + dy, x0 + dx] * 0.4 + np.array((176, 170, 150)) * 0.6
                if 0 <= x0 < w and 0 <= y0 < h: img[y0, x0] = (70, 66, 58)
    if mat == 'barnacle':
        for _ in range(w * h // 5):
            x0, y0 = rng.randrange(w), rng.randrange(h)
            img[y0, x0] = (214, 208, 188) if rng.random() < 0.6 else (60, 56, 50)
    if 'trim' in fl and f in ('north', 'east', 'west', 'south', 'up') and w >= 5 and h >= 5:
        xx = 0
        while xx < w:
            run = rng.randrange(2, 7)
            if rng.random() < 0.6: tr[0, xx:xx + run] = True
            xx += run + rng.randrange(1, 4)
        if f != 'up' and h >= 8:
            for _ in range(rng.randrange(1, 3)):
                x, y = rng.randrange(1, w - 1), 0
                for _ in range(rng.randrange(h // 3, h)):
                    if 0 <= x < w and y < h: tr[y, x] = True
                    y += 1; x += rng.choice((-1, 0, 0, 1))
    if 'glow_eyes' in fl and f == 'north' and w >= 6 and h >= 6:
        img[:h // 3] *= 0.78
        for sd in (0, 1):
            for k in range(max(2, w // 4)):
                x = int(w * 0.16) + k if sd == 0 else w - 1 - int(w * 0.16) - k
                y = int(h * 0.36) + k // 2
                img[y - 1:y + 2, x] = (14, 12, 14); gl[y, x] = True
        img[int(h * 0.62):int(h * 0.74), w // 2 - 1:w // 2 + 1] = (20, 16, 16)
        for xx in range(1, w - 1):
            if xx % 2: img[int(h * 0.82):, xx] *= 0.4
    if 'cracks_glow' in fl and f in ('north', 'east', 'west', 'south', 'up'):
        n = 2 if mat != 'blade' else 0
        for _ in range(n): crack_path(gl, w, h, rng.randrange(h // 2 + 2, h + 4))
    if mat == 'blade' and f in ('east', 'west'):
        mid = h // 2
        for xx in range(D, w - D):                       # fuller and its glowing runes
            img[mid - 1:mid + 2, xx] *= 0.55
            if (xx // D) % 4 in (0, 1): gl[mid, xx] = True
    if 'battleworn' in fl:
        S = blade_sil(c); L, W = S.shape
        if f in ('east', 'west'):
            sil = np.zeros((h, w), bool)
            for ty in range(h):
                for tx in range(w):
                    z = tx if f == 'east' else w - 1 - tx
                    sil[ty, tx] = S[min(L - 1, z), min(W - 1, h - 1 - ty)]
            alpha[~sil] = 0
            # honed bright rim one pixel in from every edge, including inside the chips
            inner = sil.copy(); inner[1:, :] &= sil[:-1, :]; inner[:-1, :] &= sil[1:, :]
            inner[:, 1:] &= sil[:, :-1]; inner[:, :-1] &= sil[:, 1:]
            rim = sil & ~inner
            img[rim] = img[rim] * 0.45 + np.array((176, 186, 182)) * 0.55
            tr[rim] = True
            rim2 = inner.copy(); rim2[1:, :] &= inner[:-1, :]; rim2[:-1, :] &= inner[1:, :]
            img[inner & ~rim2] *= 1.08
            gl[:] = False
            mid = h // 2                                    # fuller with glowing runes
            for xx in range(w):
                if not sil[mid, xx]: continue
                img[mid - 2:mid + 3, xx] *= 0.72; img[mid - 1:mid + 2, xx] *= 0.85
                z = xx if f == 'east' else w - 1 - xx
                if 6 < z < L * 0.7 and (z // 3) % 3 != 2: gl[mid, xx] = True
            for _ in range(3):                              # hairline cracks running in from the chips
                m = np.zeros((h, w), bool); crack_path(m, w, h, rng.randrange(4, 9)); img[m & sil] *= 0.55
        elif f in ('up', 'down'):
            yi = W - 1 if f == 'up' else 0
            for ty in range(h):
                z = ty if f == 'up' else h - 1 - ty
                if not S[min(L - 1, z), yi]: alpha[ty, :] = 0
            img[:] = img * 0.5 + np.array((170, 180, 176)) * 0.5
        elif f == 'north':
            for ty in range(h):
                if not S[L - 1, min(W - 1, h - 1 - ty)]: alpha[ty, :] = 0
    if 'chipped' in fl and f in ('east', 'west'):
        for edge_row in (0, h - 1):
            col = 0
            while col < w:
                run = rng.randrange(2, 6)
                if rng.random() < 0.18:
                    depth = rng.randrange(1, 3)
                    if edge_row == 0: alpha[:depth, col:col + run] = 0
                    else: alpha[h - depth:, col:col + run] = 0
                col += run
    if mat == 'bone_dark': img *= 0.55
    if mat == 'skull' and f in ('east', 'west'):         # sunken temples and cheeks on the sides of the face
        yy_, xx_ = np.mgrid[0:h, 0:w]; u = (xx_ + 0.5) / w; v = (yy_ + 0.5) / h
        img[(v > 0.55)] *= 0.72
        img[(np.abs(u - 0.5) < 0.3) & (v > 0.15) & (v < 0.55)] *= 0.82
    if mat == 'bone_skull' and f in ('up', 'east', 'west', 'south'):
        for _ in range(2):
            m = np.zeros((h, w), bool); crack_path(m, w, h, max(h, w)); img[m] *= 0.72
    if mat == 'skull_low' and f == 'north':
        yy_, xx_ = np.mgrid[0:h, 0:w]; u = (xx_ + 0.5) / w; v = (yy_ + 0.5) / h
        img[(np.abs(u - 0.5) < 0.12 * (1 - v)) & (v < 0.55)] = (16, 12, 12)            # bottom of the nasal cavity
        img[np.abs(u - 0.5) > 0.36] *= 0.6
    if mat == 'skull_low' and f != 'north': img *= 0.7
    if mat == 'teeth' and f == 'north':
        img[:] *= 0.9
        for x in range(w):
            img[:, x] = (200, 190, 162) if x % 2 else (26, 20, 18)
        img[-1, :] *= 0.5
    if mat == 'skull' and f == 'north':
        yy_, xx_ = np.mgrid[0:h, 0:w]; u = (xx_ + 0.5) / w; v = (yy_ + 0.5) / h
        img *= (0.78 + 0.22 * np.sin(np.clip(u, 0.02, 0.98) * math.pi))[..., None]       # rounded
        img[v < 0.3] *= (0.7 + 0.3 * v[v < 0.3] / 0.3)[:, None]                         # heavy brow shadow
        for sd in (0, 1):
            uu = u if sd == 0 else 1 - u
            top = 0.12 + 0.18 * np.clip((uu - 0.06) / 0.38, 0, 1)                       # slants down to the nose: angry
            sock = (uu > 0.06) & (uu < 0.41) & (v > top) & (v < 0.58 - 0.08 * np.clip((0.18 - uu) / 0.12, 0, 1))
            ring = (uu > 0.03) & (uu < 0.44) & (v > top - 0.06) & (v < 0.64) & ~sock
            img[ring] *= 0.62; img[sock] = (12, 10, 12)
            cx = int(w * (0.29 if sd == 0 else 0.71)) + (1 if sd == 1 else 0); cy = int(h * 0.42)
            ey[cy:cy + 2, cx - 1:cx + 1] = True
        nose = (np.abs(u - 0.5) < 0.12 * np.clip((v - 0.56) / 0.3, 0, 1) + 0.02) & (v > 0.6)
        img[nose] = (16, 12, 12)
        for cxk in (0.1, 0.9):                                                            # cheek hollows
            m = (np.abs(u - cxk) < 0.1) & (v > 0.66); img[m] *= 0.55
    if mat == 'jaw' and f == 'north':
        for xx in range(1, w - 1):
            img[0:int(h * 0.45), xx] = (176, 166, 138) if xx % 2 else (26, 22, 20)
            img[int(h * 0.45):, xx] *= 0.8
    if mat == 'skull_small' and side and 'glow_eyes' not in fl:
        img[h // 3:h // 3 + 2, 1:3] = (20, 20, 20); img[h // 3:h // 3 + 2, w - 3:w - 1] = (20, 20, 20)
    out = np.clip(img, 0, 255).astype(np.uint8)
    base[Y:Y + h, X:X + w, :3] = out; base[Y:Y + h, X:X + w, 3] = alpha
    glow[Y:Y + h, X:X + w] |= gl & (alpha > 0); trim[Y:Y + h, X:X + w] |= tr & (alpha > 0); eyes[Y:Y + h, X:X + w] |= ey

for i, c in enumerate(M.CUBES):
    for f in FACES: paint(c, f, place[(i, f)])

def with_glow(rune, eye, trim_col):
    t = base.copy()
    if trim_col is None: t[trim, :3] = (t[trim, :3] * 0.62).astype(np.uint8)
    else: t[trim, :3] = trim_col
    t[glow, :3] = rune; t[eyes, :3] = eye; return t
tex_p1 = with_glow(GLOW_P1, EYE_P1, None); tex_p2 = with_glow(GLOW_P2, EYE_P2, GLOW_P2)
mask = np.zeros_like(base); mask[glow | trim] = (*GLOW_MASK, 255); mask[eyes] = (*EYE_P2, 255)
Image.fromarray(tex_p1, 'RGBA').save(f'{OUT}/{NAME}.png')
Image.fromarray(tex_p2, 'RGBA').save(f'{OUT}/{NAME}_awakened.png')
Image.fromarray(mask, 'RGBA').save(f'{OUT}/{NAME}_awakened_glowmask.png')
eyemask = np.zeros_like(base); eyemask[eyes] = (*EYE_P1, 255)
Image.fromarray(eyemask, 'RGBA').save(f'{OUT}/{NAME}_glowmask.png')

# ---------------------------------------------------------------- bbmodel
def uid(): return str(uuid.UUID(int=rng.getrandbits(128)))
bone_uuid = {b['name']: uid() for b in M.BONES}
elements = []; cube_uuids = {b['name']: [] for b in M.BONES}
for i, c in enumerate(M.CUBES):
    frm = c['frm']; to = [frm[k] + c['size'][k] for k in range(3)]
    faces = {}
    for f in FACES:
        X, Y, w, h = place[(i, f)]
        faces[f] = {'uv': [X, Y, X + w, Y + h], 'texture': 0}
    piv = c['pivot'] or [(frm[k] + to[k]) / 2 for k in range(3)]
    e = {'name': c['name'], 'box_uv': False, 'rescale': False, 'locked': False, 'render_order': 'default',
         'allow_mirror_modeling': True, 'from': frm, 'to': to, 'autouv': 0, 'color': 0, 'origin': list(piv),
         'faces': faces, 'type': 'cube', 'uuid': uid()}
    if c['rot']: e['rotation'] = list(c['rot'])
    elements.append(e); cube_uuids[c['bone']].append(e['uuid'])

def group(b):
    kids = [group(x) for x in M.BONES if x['parent'] == b['name']]
    g = {'name': b['name'], 'origin': b['pivot'], 'color': 0, 'uuid': bone_uuid[b['name']], 'export': True,
         'mirror_uv': False, 'isOpen': True, 'locked': False, 'visibility': True, 'autouv': 0,
         'children': cube_uuids[b['name']] + kids}
    if any(b['rot']): g['rotation'] = b['rot']
    return g
outliner = [group(b) for b in M.BONES if b['parent'] is None]

def png_b64(arr):
    bio = io.BytesIO(); Image.fromarray(arr, 'RGBA').save(bio, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(bio.getvalue()).decode()
textures = [{'path': '', 'name': f'{NAME}.png', 'folder': '', 'namespace': '', 'id': '0', 'width': TW, 'height': TH,
             'uv_width': TW, 'uv_height': TH, 'particle': False, 'render_mode': 'default', 'render_sides': 'auto',
             'frame_time': 1, 'frame_order_type': 'loop', 'frame_order': '', 'frame_interpolate': False,
             'visible': True, 'internal': True, 'saved': False, 'uuid': uid(), 'source': png_b64(tex_p1)}]

animations = []; anim_json = {'format_version': '1.8.0', 'animations': {}}
if A:
    for an in A.ANIMS:
        animators = {}; bones_out = {}
        for bname, chans in an['bones'].items():
            kfs = []; bo = {}
            for ch, keys in chans.items():
                vals = {}
                smooth_ = an.get('interp', 'catmullrom') == 'catmullrom' and len(keys) > 2
                for t, v in keys:
                    if ch == 'rotation': ev = [round(-v[0], 3), round(-v[1], 3), round(v[2], 3)]
                    elif ch == 'position': ev = [round(-v[0], 3), round(v[1], 3), round(v[2], 3)]
                    else: ev = [round(x, 3) for x in v]
                    kfs.append({'channel': ch, 'data_points': [{'x': str(ev[0]), 'y': str(ev[1]), 'z': str(ev[2])}],
                                'uuid': uid(), 'time': t, 'color': -1, 'interpolation': 'catmullrom' if smooth_ else 'linear'})
                    vals[f'{t:g}'] = {'post': ev, 'lerp_mode': 'catmullrom'} if smooth_ else ev
                bo[ch] = vals
            animators[bone_uuid[bname]] = {'name': bname, 'type': 'bone', 'keyframes': kfs}
            bones_out[bname] = bo
        animations.append({'uuid': uid(), 'name': f'animation.{NAME}.{an["name"]}', 'loop': an['loop'],
                           'override': False, 'length': an['length'], 'snapping': 20, 'selected': False,
                           'anim_time_update': '', 'blend_weight': '', 'start_delay': '', 'loop_delay': '',
                           'animators': animators})
        aj = {'animation_length': an['length'], 'bones': bones_out}
        if an['loop'] == 'loop': aj['loop'] = True
        elif an['loop'] == 'hold': aj['loop'] = 'hold_on_last_frame'
        anim_json['animations'][f'animation.{NAME}.{an["name"]}'] = aj

bb = {'meta': {'format_version': '4.5', 'model_format': 'bedrock', 'box_uv': False}, 'name': NAME,
      'model_identifier': NAME, 'visible_box': [5, 9.5, 4.5], 'variable_placeholders': '',
      'variable_placeholder_buttons': [], 'timeline_setups': [], 'unhandled_root_fields': {},
      'resolution': {'width': TW, 'height': TH}, 'elements': elements, 'outliner': outliner,
      'textures': textures, 'animations': animations}
json.dump(bb, open(f'{OUT}/{NAME}.bbmodel', 'w'))

# ---------------------------------------------------------------- geo.json (GeckoLib / bedrock)
geo_bones = []
for b in M.BONES:
    gb = {'name': b['name'], 'pivot': [-b['pivot'][0], b['pivot'][1], b['pivot'][2]]}
    if b['parent']: gb['parent'] = b['parent']
    if any(b['rot']): gb['rotation'] = [-b['rot'][0], -b['rot'][1], b['rot'][2]]
    cubes = []
    for i, c in enumerate(M.CUBES):
        if c['bone'] != b['name']: continue
        frm = c['frm']; size = c['size']
        gc = {'origin': [-(frm[0] + size[0]), frm[1], frm[2]], 'size': size, 'uv': {}}
        if c['rot']:
            piv = c['pivot']
            gc['pivot'] = [-piv[0], piv[1], piv[2]]
            gc['rotation'] = [-c['rot'][0], -c['rot'][1], c['rot'][2]]
        for f in FACES:
            X, Y, w, h = place[(i, f)]
            if f in ('up', 'down'): gc['uv'][f] = {'uv': [X + w, Y + h], 'uv_size': [-w, -h]}
            else: gc['uv'][f] = {'uv': [X, Y], 'uv_size': [w, h]}
        cubes.append(gc)
    if cubes: gb['cubes'] = cubes
    geo_bones.append(gb)
geo = {'format_version': '1.12.0', 'minecraft:geometry': [{'description': {
    'identifier': f'geometry.{NAME}', 'texture_width': TW, 'texture_height': TH,
    'visible_bounds_width': 6, 'visible_bounds_height': 10, 'visible_bounds_offset': [0, 4.5, 0]},
    'bones': geo_bones}]}
json.dump(geo, open(f'{OUT}/{NAME}.geo.json', 'w'), indent=1)
json.dump(anim_json, open(f'{OUT}/{NAME}.animation.json', 'w'), indent=1)
print('cubes', len(M.CUBES), 'bones', len(M.BONES), 'anims', len(animations))
