"""The Withered King - all 10 actions, authored from scratch against the brief.
Run in Blender on withered_king_rig.blend:  blender -b withered_king_rig.blend --python anims.py [-- name ...]
Units: Blockbench pixels (8 px = 1 block, he is ~8.6 blocks tall), degrees on top of his rest pose, seconds.
Conventions: body/torso rot x+ = lean back, y+ = turn to HIS left, z+ = lean to his left; head x+ = look up; jaw x+ = open.
Every stage boundary from the brief is marked; event() calls become the timing/event table used by the game script."""
import bpy, sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import anim_lib as L
from anim_lib import fk, feet, sword, sword_dense, grip, hands, fingers, pole, begin, finish, event, eval_at, K_now, norm, smooth
ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def want(n): return not ONLY or n in ONLY
Z = (0, 0, 0); sin, cos, pi = math.sin, math.cos, math.pi
V = Vector

# ================================================================== shared poses
BLADE = 41.8
def drag(grip_pt, heading, ground=-0.4, mode='cane', roll=0.0):
    """sword held at grip_pt with the tip resting on the ground at `heading` degrees around him (0 = ahead, + = his right)."""
    h = math.radians(heading); dy = ground - grip_pt[1]; hl = math.sqrt(max(1.0, BLADE * BLADE - dy * dy))
    tip = (grip_pt[0] + sin(h) * hl, ground, grip_pt[2] - cos(h) * hl)
    return dict(grip=grip_pt, tip=tip, mode=mode, roll=roll)
def ride_pt(space, p): return tuple((K_now(space) @ V((*p, 1))).xyz)

# combat neutral: hunched, sword hanging in the right hand with the point dragging the ground behind him
STAND = dict(body=((-2, 0, -2.5), (0.6, -1.6, 0.3)), waist=((-4, 0, 0), Z), chest=((-6, -2, -3), Z), neck=((-5, 0, 1), Z),
             head=((7, 2, 1), Z), jaw=((3, 0, 0), Z), right_clavicle=((0, 2, -7), Z), left_clavicle=((0, 0, 2), Z))
DRAG_GRIP = (16.4, 26.0, 4.0); DRAG_HEAD = 166
STAND_SWORD = drag(DRAG_GRIP, DRAG_HEAD)
def st(n, t, d=Z, p=Z, e='smooth'):
    r, ps = STAND[n]; return (t, L.add3(r, d), L.add3(ps, p), e)
def stand_all(t, e='smooth', skip=()):
    for n in STAND:
        if n not in skip: fk(n, [st(n, t, e=e)])
LEFT_RELAX = {'off': ((0.5, 1.5, -1.0), (-6, 0, -4)), 'space': 'chest'}

# ================================================================== 01 idle (6.0 s loop)
if want('withered_king_idle'):
    begin('withered_king_idle', 6.0, 'loop')
    # the same stance every attack starts and ends in (sword point resting on the ground at his side), so idle, walk and
    # attacks blend into each other without the sword jumping; the breathing/looking is layered on top of it
    IB = {'body': ((-1, 0, 0), (0, -0.6, 0)), 'waist': ((-3, 0, 0), Z), 'chest': ((-7, 0, 0), Z), 'neck': ((-4, 0, 0), Z), 'head': ((6, 0, 0), Z),
          'jaw': ((2, 0, 0), Z), 'right_clavicle': ((0, 0, -3), Z), 'left_clavicle': ((0, 0, 1), Z)}
    def fk_i(n, keys):
        out = []
        for k in keys:
            r = L.add3(STAND[n][0], tuple(x - y for x, y in zip(k[1], IB[n][0])))
            p = L.add3(STAND[n][1], tuple(x - y for x, y in zip(k[2] if len(k) > 2 and k[2] else Z, IB[n][1])))
            out.append((k[0], r, p, k[3] if len(k) > 3 else 'smooth'))
        fk(n, out)
    # labored breathing: a long rattling inhale, a held top, a slow collapse - then one shallower breath
    fk_i('body', [(0, (-1, 0, 0), (0, -0.6, 0)), (1.6, (-1, -0.5, 0.4), (0.45, -0.75, 0)), (3.0, (-1, -0.7, 0.5), (0.55, -0.8, 0)),
                (4.6, (-1, 0.3, -0.3), (-0.25, -0.6, 0)), (6.0, (-1, 0, 0), (0, -0.6, 0))])
    fk_i('waist', [(0, (-3, 0, 0)), (1.4, (-2.4, 0, 0)), (2.9, (-3.3, 0, 0)), (4.3, (-2.7, 0, 0)), (6.0, (-3, 0, 0))])
    fk_i('chest', [(0, (-7, 0, 0), Z), (1.3, (-5.2, 0.4, 0), (0, 0.4, 0.1)), (1.75, (-5.0, 0.4, 0), (0, 0.45, 0.1)), (3.2, (-7.6, 0, 0), (0, -0.05, 0)),
                 (4.35, (-5.9, -0.3, 0), (0, 0.3, 0.1)), (5.1, (-6.8, -0.2, 0), (0, 0.05, 0)), (6.0, (-7, 0, 0), Z)])
    fk_i('right_clavicle', [(0, (0, 0, -3)), (1.4, (0, 0.6, -1.6)), (3.2, (0, 0, -3.4)), (4.0, (0, -1.2, -2.0), None, 'inout'), (4.4, (0, 0, -3)), (6.0, (0, 0, -3))])
    fk_i('left_clavicle', [(0, (0, 0, 1)), (1.4, (0, 0, -0.6)), (3.2, (0, 0, 1.4)), (6.0, (0, 0, 1))])
    # watching: a slow turn toward the player, then stillness; a neck twitch; a slow cock of the head
    fk_i('neck', [(0, (-4, 0, 0)), (0.8, (-4, 0, 0)), (1.8, (-4.5, -5, 0), None, 'out'), (3.55, (-4.5, -5, 0)), (3.62, (-4.0, -6.2, 1.2), None, 'out'),
                (3.8, (-4.5, -5, 0)), (5.3, (-4, -1, 0), None, 'inout'), (6.0, (-4, 0, 0))])
    fk_i('head', [(0, (6, 0, 0)), (0.9, (6, 0, 0)), (1.9, (5.5, -5, -1), None, 'out'), (3.9, (5.5, -5.5, -1)), (4.5, (6.5, -4, 4.5), None, 'inout'),
                (5.2, (6.5, -3, 4)), (5.8, (6, -0.5, 0.5), None, 'inout'), (6.0, (6, 0, 0))])
    fk_i('jaw', [(0, (2, 0, 0)), (1.3, (4.5, 0, 0)), (2.0, (4, 0, 0)), (3.0, (1.5, 0, 0)), (4.4, (3.5, 0, 0)), (6.0, (2, 0, 0))])
    feet('L', [(0, dict(d=Z), 'smooth'), (6.0, dict(d=Z), 'smooth')]); feet('R', [(0, dict(d=Z), 'smooth'), (6.0, dict(d=Z), 'smooth')])
    # the greatsword stands planted at his side; his fist rests on the hilt and re-settles its grip
    sword([(0, STAND_SWORD, 'smooth'), (6.0, STAND_SWORD, 'smooth')])
    grip('R', [(0, 'cane', 0)]); grip('L', [(0, 'free', 0)])
    fingers('R', [(0, 0, 0, 'smooth'), (2.2, 0, 0, 'smooth'), (2.45, -12, 0, 'out'), (2.75, 6, 0, 'inout'), (3.0, 0, 0, 'smooth'), (6.0, 0, 0, 'smooth')])
    hands('L', [(0, LEFT_RELAX, 'smooth'), (2.0, {'off': ((0.5, 1.7, -1.0), (-6, 0, 1)), 'space': 'chest'}, 'smooth'),
                (4.85, {'off': ((0.5, 1.6, -1.0), (-6, 0, -2)), 'space': 'chest'}, 'in'), (4.95, {'off': ((0.8, 1.9, -1.3), (-10, 0, 6)), 'space': 'chest'}, 'out'),
                (5.4, {'off': ((0.6, 1.6, -1.1), (-7, 0, -2)), 'space': 'chest'}, 'smooth'), (6.0, LEFT_RELAX, 'smooth')])
    fingers('L', [(0, 22, 0, 'smooth'), (2.0, 34, 2, 'smooth'), (3.6, 28, 0, 'smooth'), (4.85, 26, 0, 'in'), (4.95, 46, 4, 'out'), (5.4, 30, 0, 'smooth'), (6.0, 22, 0, 'smooth')])
    finish()

# ================================================================== 02 walk with sword drag (2.4 s loop = 14 px/s = speed 0.20)
WALK_T = 2.4; WALK_V = 14.0
if want('withered_king_walk_drag'):
    T = WALK_T; ST = 0.62; STRIDE = WALK_V * T; ZC = -10.4
    begin('withered_king_walk_drag', T, 'loop')
    def smoother(u): return u * u * u * (u * (u * 6 - 15) + 10)
    def hermite(p0, p1, m0, m1, u):
        return (2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * m0 + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * m1
    def foot_at(ph, side):
        ph %= 1.0; x = -1.4 if side == 'R' else 1.4; yaw = -8 if side == 'R' else 8
        if ph < ST:
            z = ZC + STRIDE * ph
            pit = 15 * (1 - smoother(ph / 0.09)) if ph < 0.09 else (0 if ph < 0.45 else -30 * smoother((ph - 0.45) / (ST - 0.45)))
            return dict(d=(x, 0, z), yaw=yaw, pitch=pit, pivot='heel' if pit > 0 else 'toe')
        u = (ph - ST) / (1 - ST)
        z = hermite(ZC + STRIDE * ST, ZC, 4.0, 6.0, u)
        y = 6.2 * math.sin(pi * min(1.0, u ** 0.7)) ** 1.1
        pit = -30 + 45 * smoother(min(1.0, u / 0.92))
        return dict(d=(x, y, z), yaw=yaw, pitch=pit, pivot='heel' if pit > 0 else 'toe')
    N = 48
    feet('R', [(T * k / N, foot_at(k / N, 'R'), 'linear') for k in range(N + 1)])
    feet('L', [(T * k / N, foot_at(k / N + 0.5, 'L'), 'linear') for k in range(N + 1)])
    for side, t0 in (('R', 0.0), ('L', T / 2)): event(t0, 'footstep', side=side)
    def torso(ph):
        s = ph % 0.5 / 0.5
        dip = -0.6 * math.exp(-((s - 0.1) / 0.07) ** 2)                     # the weight lands just after each heel strike
        bob = 0.4 * -cos(2 * pi * s) + dip
        sway = 1.2 * sin(2 * pi * ph - 0.25)
        yaw = 4.5 * cos(2 * pi * ph)                                         # hips swing with the leg
        return dict(body=((-3 + 1.2 * dip, yaw, -2.5 + 2.0 * sin(2 * pi * ph - 0.3)), (sway + 0.5, -2.2 + bob, 0)),
                    waist=((-3 + 0.6 * dip, -1.6 * cos(2 * pi * ph - 0.2), -0.6 * sin(2 * pi * ph)), Z),
                    chest=((-5 + 2.4 * dip, -6.0 * cos(2 * pi * ph - 0.35) - 2, -3 - 2.2 * sin(2 * pi * ph - 0.4)), Z),
                    neck=((-5 + 1.0 * dip, 2.5 * cos(2 * pi * ph - 0.5), 1.0 * sin(2 * pi * ph - 0.5)), Z),
                    head=((7 + 1.6 * dip, 3.5 * cos(2 * pi * ph - 0.55) + 2, 1 + 1.2 * sin(2 * pi * ph - 0.55)), Z),
                    jaw=((3 - 5 * dip, 0, 0), Z),
                    right_clavicle=((0, 2 + 1.5 * cos(2 * pi * ph - 0.6), -7 + 1.5 * dip), Z),
                    left_clavicle=((0, -1.5 * cos(2 * pi * ph - 0.6), 2 - 1.0 * dip), Z))
    M = 24
    for n in ('body', 'waist', 'chest', 'neck', 'head', 'jaw', 'right_clavicle', 'left_clavicle'):
        fk(n, [(T * k / M, *torso(k / M)[n], 'smooth') for k in range(M + 1)])
    # the blade: carried at his side, point gouging the ground behind; it trails the body, and once a cycle it
    # catches on the ground - the arm is pulled back and the shoulder jerks - then it tears free
    CATCH0, CATCH1 = 0.30, 0.44
    def drag_at(t):
        ph = t / T % 1.0
        surge = 0.8 * sin(2 * pi * (ph * 2) - 1.0)                           # the blade lags each surge of the body
        catch = 0.0
        if CATCH0 <= ph < CATCH1: catch = WALK_V * (ph - CATCH0) * T                  # stuck: the ground drags it back
        elif CATCH1 <= ph < CATCH1 + 0.12: catch = WALK_V * (CATCH1 - CATCH0) * T * (1 - smooth((ph - CATCH1) / 0.12)) - 0.6 * sin(pi * (ph - CATCH1) / 0.12)
        g = ride_pt('right_clavicle', (DRAG_GRIP[0], DRAG_GRIP[1], DRAG_GRIP[2] + 0.4 * surge + 0.25 * catch))
        heading = DRAG_HEAD + 2.5 * sin(2 * pi * ph - 0.8)
        spec = drag(g, heading)
        tip = list(spec['tip']); tip[2] += surge * 0.6 + catch
        spec['tip'] = tuple(tip); return spec
    sword_dense(drag_at, 0.0, T)
    event(0.0, 'drag_contact_loop'); event(CATCH0 * T, 'drag_catch'); event(CATCH1 * T, 'drag_release')
    grip('R', [(0, 'cane', 0)]); grip('L', [(0, 'free', 0)])
    def swing(ph):
        a = cos(2 * pi * (ph - 0.08))
        return {'off': ((0.4 * a, 1.6 + 0.6 * (1 - a * a), -4.0 * a), (-11 * a - 4, 0, -4 - 3 * abs(a))), 'space': 'chest'}
    hands('L', [(T * k / M, swing(k / M), 'smooth') for k in range(M + 1)])
    fingers('L', [(0, 24, 0, 'smooth'), (1.2, 30, 0, 'smooth'), (2.4, 24, 0, 'smooth')])
    fingers('R', [(0, 4, 0, 'smooth'), (CATCH0 * T, 4, 0, 'in'), (CATCH1 * T, 10, 0, 'out'), (2.4, 4, 0, 'smooth')])
    finish()

# ================================================================== 03 sweep (2.85 s) - anticipation 0-0.8, swing 0.8-1.25,
#                                                                      follow-through 1.25-1.9, recovery 1.9-2.85
C0 = V((1.0, 0.0, 0.0))
def arc_sword(a, gh, rg, tip_y, ga_off):
    """blade with its tip skimming the ground at angle a around him; grip at height gh, radius rg, angle a+ga_off."""
    ga = math.radians(a + ga_off); g = V((C0.x + rg * sin(ga), gh, C0.z - rg * cos(ga)))
    ar = math.radians(a); u = V((sin(ar), 0, -cos(ar)))
    dy = tip_y - gh; hl = math.sqrt(max(1.0, BLADE * BLADE - dy * dy))
    # tip on the ray from the grip toward angle a, at horizontal distance hl from the grip
    rel = V((g.x - C0.x, 0, g.z - C0.z)); bq = 2 * rel.dot(u); cq = rel.length_squared - hl * hl
    R = (-bq + math.sqrt(max(0.0, bq * bq - 4 * cq))) / 2
    tip = V((C0.x, tip_y, C0.z)) + u * R
    return dict(grip=tuple(g), tip=tuple(tip), mode='cane')
if want('withered_king_sweep'):
    begin('withered_king_sweep', 2.85, 'once')
    event(0.0, 'windup_begin'); event(0.15, 'warning'); event(0.3, 'scrape', note='blade dragged into the windup')
    fk('body', [st('body', 0), st('body', 0.25, d=(0, -4, 0), p=(0.6, -0.4, 0.4), e='inout'), st('body', 0.72, d=(2, -15, 1), p=(1.8, -2.4, 1.2), e='inout'),
                st('body', 0.8, d=(2, -16, 1), p=(1.9, -2.5, 1.3), e='in'), st('body', 1.02, d=(-3, 8, -1), p=(0.4, -3.2, -0.4), e='linear'),
                st('body', 1.2, d=(-4, 22, -2), p=(-1.8, -3.4, -1.2), e='out'), st('body', 1.45, d=(-4, 23, -2), p=(-2.4, -3.6, -1.4), e='smooth'),
                st('body', 1.9, d=(-3, 20, -1), p=(-1.8, -3.0, -1.0), e='inout'), st('body', 2.5, d=(0, 2, 0), p=(0.2, -0.3, 0.1), e='inout'), st('body', 2.85)])
    fk('waist', [st('waist', 0), st('waist', 0.75, d=(1, -10, 0), e='inout'), st('waist', 0.84, d=(1, -11, 0), e='in'), st('waist', 1.24, d=(-3, 12, 0), e='out'),
                 st('waist', 1.5, d=(-3, 14, 0)), st('waist', 2.0, d=(-2, 8, 0), e='inout'), st('waist', 2.85)])
    fk('chest', [st('chest', 0), st('chest', 0.3, d=(1, -3, 0)), st('chest', 0.78, d=(4, -16, -3), e='inout'), st('chest', 0.88, d=(4, -17, -3), e='in'),
                 st('chest', 1.28, d=(-6, 16, 3), e='out'), st('chest', 1.55, d=(-7, 15, 3)), st('chest', 2.05, d=(-4, 10, 2), e='inout'), st('chest', 2.85)])
    fk('neck', [st('neck', 0), st('neck', 0.8, d=(0, 10, 0), e='inout'), st('neck', 0.95, d=(0, 10, 0), e='in'), st('neck', 1.35, d=(-2, -10, 0), e='out'), st('neck', 2.2, d=(0, -5, 0)), st('neck', 2.85)])
    fk('head', [st('head', 0), st('head', 0.8, d=(-3, 18, 2), e='inout'), st('head', 0.98, d=(-3, 19, 2), e='in'), st('head', 1.4, d=(-4, -16, -2), e='out'),
                st('head', 1.8, d=(-3, -22, -2)), st('head', 2.4, d=(0, -4, 0), e='inout'), st('head', 2.85)])
    fk('jaw', [st('jaw', 0), st('jaw', 0.8, d=(-2, 0, 0)), st('jaw', 1.0, d=(-2, 0, 0), e='in'), st('jaw', 1.15, d=(20, 0, 0), e='out'), st('jaw', 1.6, d=(12, 0, 0)), st('jaw', 2.3, d=(2, 0, 0)), st('jaw', 2.85)])
    fk('right_clavicle', [st('right_clavicle', 0), st('right_clavicle', 0.8, d=(0, -4, -2)), st('right_clavicle', 1.15, d=(0, 8, 2), e='out'), st('right_clavicle', 1.6, d=(0, 10, 3)), st('right_clavicle', 2.85)])
    fk('left_clavicle', [st('left_clavicle', 0), st('left_clavicle', 0.8, d=(0, -8, 0)), st('left_clavicle', 1.15, d=(0, 4, -2), e='out'), st('left_clavicle', 1.6, d=(0, 6, -3)), st('left_clavicle', 2.85)])
    # feet: the left foot plants a wider step during the windup; the back foot pivots on its toes as the hips fire;
    # the left foot steps out again to catch the momentum; both return in the recovery
    FL0, FR0 = dict(d=Z), dict(d=Z)
    FL1 = dict(d=(-2.0, 0, -5.5), yaw=10); FL2 = dict(d=(-4.5, 0, -3.5), yaw=22)
    feet('L', [(0, FL0, 'smooth'), (0.08, FL0, 'out'), (0.22, dict(d=(-1.0, 3.2, -3.0), pitch=6, pivot='ankle'), 'smooth'), (0.36, FL1, 'smooth'),
               (1.28, FL1, 'out'), (1.4, dict(FL1, d=(-3.5, 2.6, -4.6), pitch=5, pivot='ankle'), 'smooth'), (1.52, FL2, 'smooth'), (2.15, FL2, 'out'),
               (2.3, dict(d=(-2.0, 2.6, -1.5), yaw=10, pitch=4, pivot='ankle'), 'smooth'), (2.45, FL0, 'smooth'), (2.85, FL0, 'smooth')])
    feet('R', [(0, FR0, 'smooth'), (0.95, FR0, 'in'), (1.2, dict(d=Z, yaw=24, pitch=-16, pivot='toe'), 'out'), (1.65, dict(d=Z, yaw=30, pitch=-18, pivot='toe'), 'smooth'),
               (2.3, dict(d=Z, yaw=6, pitch=-3, pivot='toe'), 'inout'), (2.6, FR0, 'smooth'), (2.85, FR0, 'smooth')])
    # the blade path.  The grip travels on an arc in front of his hips while the blade's heading (seen from the grip)
    # swings round with it; the point stays on, or skims just over, the ground the whole way.
    GA0 = math.degrees(math.atan2(DRAG_GRIP[0] - C0.x, -(DRAG_GRIP[2] - C0.z))); RG0 = math.hypot(DRAG_GRIP[0] - C0.x, DRAG_GRIP[2] - C0.z)
    def sw_spec(ga, heading, gh, tip_y, rg):
        g = (C0.x + rg * sin(math.radians(ga)), gh, C0.z - rg * cos(math.radians(ga)))
        return drag(g, heading, ground=tip_y)
    def sweep_sword(t):
        if t <= 0.8:              # windup: hips turn away, the point is scraped round from behind to his right-back
            u = smooth(t / 0.8)
            return sw_spec(GA0 + (112 - GA0) * u, DRAG_HEAD + (128 - DRAG_HEAD) * u, 25.5 - 1.5 * u, -0.3 + 0.5 * u, RG0 + (14.0 - RG0) * u)
        if t <= 1.25:             # swing: accelerating; the blade trails the hands, then whips past them
            u = (t - 0.8) / 0.45; w = 0.55 * (u * u * (3 - 2 * u)) + 0.45 * u ** 1.6
            ga = 112 + (-78 - 112) * w
            heading = 128 + (-100 - 128) * w - 16 * sin(pi * u) * 0 + 14 * sin(pi * min(1, u * 1.4)) * (1 - u)
            return sw_spec(ga, heading, 24 - 3 * sin(pi * u), 0.2 + 1.6 * sin(pi * u), 14 + 2 * sin(pi * u))
        if t <= 1.9:              # follow-through: momentum carries the blade on round to his left and it slows
            u = smooth((t - 1.25) / 0.65)
            return sw_spec(-78 + (-90 + 78) * u, -100 + (-124 + 100) * u, 24 + 1.0 * u, 0.2 - 0.5 * u, 14 - 1.2 * u)
        u = smooth((t - 1.9) / 0.95)                         # recovery: lifted a little, carried back across to his side
        lift = 5.0 * sin(pi * u)
        return sw_spec(-90 + (GA0 + 90) * u, -124 + (DRAG_HEAD + 124) * u, 25.0 + 0.5 * u + 2.5 * sin(pi * u), -0.3 + lift, 12.8 + (RG0 - 12.8) * u)
    sword_dense(sweep_sword, 0.0, 2.85)
    event(0.8, 'swing_begin'); event(0.9, 'sound', id='whoosh'); event(1.25, 'follow_through_begin'); event(1.9, 'recovery_begin'); event(2.85, 'recovery_end')
    grip('R', [(0, 'cane', 0)])
    grip('L', [(0, 'free', 0), (0.25, 'cane', 0.45), (2.25, 'free', 0.4)])
    hands('L', [(0, LEFT_RELAX, 'smooth'), (0.3, {'off': ((4, 4, -8), (-30, 0, -10)), 'space': 'chest'}, 'smooth'),
                (2.25, {'off': ((4, 2, -6), (-20, 0, -8)), 'space': 'chest'}, 'smooth'), (2.85, LEFT_RELAX, 'smooth')])
    fingers('L', [(0, 22, 0, 'smooth'), (0.3, 20, 6, 'smooth'), (0.6, 72, 0, 'out'), (2.25, 72, 0, 'smooth'), (2.5, 26, 2, 'smooth'), (2.85, 22, 0, 'smooth')])
    fingers('R', [(0, 0, 0, 'smooth'), (0.75, 6, 0, 'smooth'), (2.85, 0, 0, 'smooth')])
    finish()

# ================================================================== 04 dash (2.5 s) - preparation 0-0.9, dash 0.9-1.45, recovery 1.45-2.5
DASH = dict(start=0.9, stop=1.5, vmax=128.0)     # px/s: ~16 blocks/s at full stride; the server uses the same curve
def dash_speed(t):
    s, e, vm = DASH['start'], DASH['stop'], DASH['vmax']
    if t < s or t > e: return 0.0
    u = (t - s) / (e - s)
    return vm * (smooth(u / 0.25) if u < 0.25 else (1.0 if u < 0.78 else 1 - smooth((u - 0.78) / 0.22) * 0.55))
if want('withered_king_dash'):
    begin('withered_king_dash', 2.5, 'once')
    event(0.0, 'windup_begin'); event(0.1, 'warning'); event(0.9, 'dash_launch'); event(1.5, 'dash_stop')
    THRUST_G = (4.0, 25.0, -18.0); THRUST_B = norm((-0.04, -0.26, -1.0))     # low two-handed charge: point at the target's chest
    fk('body', [st('body', 0), st('body', 0.35, d=(-2, -6, 0), p=(0, -2.6, 2.0), e='inout'), st('body', 0.72, d=(-8, -10, 0), p=(0, -5.4, 3.0), e='inout'),
                st('body', 0.9, d=(-9, -10, 0), p=(0, -5.8, 3.2), e='expo_out'), st('body', 1.02, d=(-20, -4, 0), p=(0, -3.0, -3.0)),
                st('body', 1.4, d=(-22, -4, 0), p=(0, -3.4, -3.4), e='in'), st('body', 1.52, d=(-16, -2, 0), p=(0, -5.6, -4.6), e='out'),
                st('body', 1.7, d=(-6, 0, 0), p=(0, -4.0, -1.2)), st('body', 2.1, d=(-2, 0, 0), p=(0, -1.0, 0), e='inout'), st('body', 2.5)])
    fk('waist', [st('waist', 0), st('waist', 0.8, d=(-4, -4, 0)), st('waist', 1.1, d=(-8, 0, 0)), st('waist', 1.55, d=(-10, 0, 0), e='out'), st('waist', 2.5)])
    fk('chest', [st('chest', 0), st('chest', 0.7, d=(-6, -4, 3)), st('chest', 0.9, d=(-7, -4, 3)), st('chest', 1.1, d=(-10, 0, 3)), st('chest', 1.45, d=(-12, 0, 3), e='in'),
                 st('chest', 1.56, d=(-18, 2, 2), e='out'), st('chest', 1.72, d=(-4, 0, 1)), st('chest', 2.5)])
    fk('neck', [st('neck', 0), st('neck', 0.8, d=(6, 5, 0)), st('neck', 1.2, d=(12, 4, 0)), st('neck', 1.6, d=(6, 0, 0)), st('neck', 2.5)])
    fk('head', [st('head', 0), st('head', 0.8, d=(8, 6, -1)), st('head', 1.2, d=(14, 4, 0)), st('head', 1.58, d=(4, 0, 0), e='out'), st('head', 2.5)])
    fk('jaw', [st('jaw', 0), st('jaw', 0.85, d=(4, 0, 0)), st('jaw', 0.95, d=(26, 0, 0), e='out'), st('jaw', 1.4, d=(20, 0, 0)), st('jaw', 1.8, d=(6, 0, 0)), st('jaw', 2.5)])
    fk('right_clavicle', [st('right_clavicle', 0), st('right_clavicle', 0.7, d=(0, 2, 7)), st('right_clavicle', 0.9, d=(0, 2, 8)), st('right_clavicle', 1.35, d=(0, 8, 6)),
                          st('right_clavicle', 1.7, d=(0, 2, 4)), st('right_clavicle', 2.5)])
    fk('left_clavicle', [st('left_clavicle', 0), st('left_clavicle', 0.7, d=(0, 4, -4)), st('left_clavicle', 1.35, d=(0, 8, -2)), st('left_clavicle', 2.5)])
    # preparation: the right foot plants behind him
    FR1 = dict(d=(0.5, 0, 7.5), yaw=-14); FL1 = dict(d=(0, 0, -2.0), yaw=6)
    # charge: three driving strides, each foot planted while the ground rushes back under it (entity speed = dash_speed)
    def ground_shift(t0, t1):
        n = 20; s = 0.0
        for i in range(n):
            ta = t0 + (t1 - t0) * (i + 0.5) / n; s += dash_speed(ta) * (t1 - t0) / n
        return s
    def run_foot(side, t):
        # contacts: R push-off until 0.98, L 1.08-1.16, R 1.24-1.32, L brake from 1.44
        if side == 'R':
            if t <= 0.9: return FR1
            if t <= 0.98: return dict(FR1, d=(0.5, 0, 7.5 + ground_shift(0.9, t)), pitch=-30 * smooth((t - 0.9) / 0.08), pivot='toe')
            if t < 1.24:
                u = (t - 0.98) / 0.26; zs = 7.5 + ground_shift(0.9, 0.98); ze = -6.0
                return dict(d=(0.0, 6.5 * sin(pi * u), zs + (ze - zs) * smooth(u)), yaw=-6, pitch=-30 + 42 * smooth(u), pivot=None)
            if t <= 1.32: return dict(d=(0.0, 0, -6.0 + ground_shift(1.24, t)), yaw=-6, pitch=0)
            if t < 1.62:
                u = (t - 1.32) / 0.30; zs = -6.0 + ground_shift(1.24, 1.32); ze = FR1['d'][2] - 4
                return dict(d=(0.3, 5.0 * sin(pi * u), zs + (ze - zs) * smooth(u)), yaw=-10, pitch=-20 + 20 * smooth(u), pivot=None)
            return dict(FR1, d=(0.5, 0, FR1['d'][2] - 4))
        else:
            if t <= 0.95: return FL1
            if t < 1.08:
                u = (t - 0.95) / 0.13; zs = -2.0 + ground_shift(0.9, 0.95); ze = -9.0
                return dict(d=(0, 5.5 * sin(pi * u), zs + (ze - zs) * smooth(u)), yaw=6, pitch=-20 + 30 * smooth(u), pivot=None)
            if t <= 1.16: return dict(d=(0, 0, -9.0 + ground_shift(1.08, t)), yaw=6, pitch=0)
            if t < 1.44:
                u = (t - 1.16) / 0.28; zs = -9.0 + ground_shift(1.08, 1.16); ze = -10.0
                return dict(d=(0, 6.0 * sin(pi * u), zs + (ze - zs) * smooth(u)), yaw=6, pitch=-25 + 37 * smooth(u), pivot=None)
            if t <= 1.5:      # the brake: heel slams in and skids the last of the momentum away
                return dict(d=(0, 0, -10.0 + ground_shift(1.44, t)), yaw=6, pitch=12 * (1 - smooth((t - 1.44) / 0.06)), pivot='heel')
            zf = -10.0 + ground_shift(1.44, 1.5)
            if t < 2.05: return dict(d=(0, 0, zf), yaw=6)
            if t < 2.3:
                u = (t - 2.05) / 0.25; return dict(d=(0, 3.0 * sin(pi * u), zf + (0 - zf) * smooth(u)), yaw=6 * (1 - smooth(u)), pitch=4 * sin(pi * u), pivot='ankle')
            return dict(d=Z)
    def prep_R(t):
        if t < 0.12: return dict(d=Z)
        if t < 0.38:
            u = (t - 0.12) / 0.26; return dict(d=(0.5 * smooth(u), 3.5 * sin(pi * u), 7.5 * smooth(u)), yaw=-14 * smooth(u), pitch=-6 * sin(pi * u), pivot='ankle')
        return run_foot('R', t)
    def end_R(t):
        if t < 2.0: return prep_R(t)
        if t < 2.3:
            u = (t - 2.0) / 0.3; z0 = FR1['d'][2] - 4
            return dict(d=(0.5 * (1 - smooth(u)), 3.0 * sin(pi * u), z0 * (1 - smooth(u))), yaw=-14 * (1 - smooth(u)), pitch=3 * sin(pi * u), pivot='ankle')
        return dict(d=Z)
    NN = 100
    feet('R', [(2.5 * k / NN, end_R(2.5 * k / NN), 'linear') for k in range(NN + 1)])
    feet('L', [(2.5 * k / NN, run_foot('L', 2.5 * k / NN), 'linear') for k in range(NN + 1)])
    for tt, sd in ((0.38, 'R'), (1.08, 'L'), (1.24, 'R'), (1.44, 'L')): event(tt, 'footstep', side=sd)
    # sword: lifted off the ground, carried round his right side (never under him) to point at the target; the left
    # hand joins the grip for the charge; afterwards it is swung back round the same way and set down to drag again
    SIDE = norm((1.0, -0.35, 0.05)); P0 = V(STAND_SWORD['grip']); B0 = (V(STAND_SWORD['tip']) - P0).normalized()
    PREP = V(THRUST_G) + V((3.0, 1.5, 8.0))
    def via(b0, b1, u):
        m = V(SIDE)
        return b0.slerp(m, min(1.0, u * 2)) if u < 0.5 else m.slerp(b1, (u - 0.5) * 2)
    def dash_sword(t):
        if t <= 0.15: return STAND_SWORD
        if t <= 0.75:
            u = smooth((t - 0.15) / 0.6)
            return dict(grip=tuple(P0.lerp(PREP, u) + V((2.0, 7.0, 0)) * sin(pi * u)), blade=tuple(via(B0, V(THRUST_B), u)), mode='cane')
        if t <= 0.9:                                                    # the coiled pause; the point trembles
            jit = 0.25 * sin(t * 90)
            return dict(grip=tuple(PREP + V((0, jit, 0))), blade=THRUST_B, mode='cane')
        if t <= 1.45:                                                   # driven ahead of the charge
            u = smooth((t - 0.9) / 0.55)
            return dict(grip=tuple(PREP.lerp(V(THRUST_G), u)), blade=THRUST_B, mode='cane')
        DIP = V(norm((0.08, -0.55, -0.83)))
        if t <= 1.75:                                                   # brakes: the point dips toward the ground
            u = smooth((t - 1.45) / 0.3)
            return dict(grip=tuple(V(THRUST_G) + V((1.0, -1.0, 2.0)) * u), blade=tuple(V(THRUST_B).slerp(DIP, u)), mode='cane')
        u = smooth((t - 1.75) / 0.65)                                   # back round to the drag at his side
        if u >= 1: return STAND_SWORD
        g0 = V(THRUST_G) + V((1.0, -1.0, 2.0))
        return dict(grip=tuple(g0.lerp(P0, u) + V((2.0, 6.0, 0)) * sin(pi * u)), blade=tuple(via(DIP, B0, u)), mode='cane')
    sword_dense(dash_sword, 0.0, 2.5)
    grip('R', [(0, 'cane', 0)])
    grip('L', [(0, 'free', 0), (0.3, 'cane', 0.35), (2.0, 'free', 0.35)])
    hands('L', [(0, LEFT_RELAX, 'smooth'), (0.3, {'off': ((4, 2, -8), (-30, 0, -10)), 'space': 'chest'}, 'smooth'),
                (2.0, {'off': ((4, 2, -6), (-16, 0, -8)), 'space': 'chest'}, 'smooth'), (2.5, LEFT_RELAX, 'smooth')])
    fingers('L', [(0, 22, 0, 'smooth'), (0.35, 18, 6, 'smooth'), (0.65, 74, 0, 'out'), (2.0, 74, 0, 'smooth'), (2.3, 24, 2, 'smooth'), (2.5, 22, 0, 'smooth')])
    fingers('R', [(0, 0, 0, 'smooth'), (0.6, 10, 0, 'smooth'), (1.5, 12, 0, 'smooth'), (2.5, 0, 0, 'smooth')])
    event(1.45, 'recovery_begin'); event(2.5, 'recovery_end')
    finish()

# ================================================================== 05 phase transition (4.5 s) - faltering 0-1.25, planting 1.25-2.55,
#                                                                      kneeling 2.55-4.5   (then 06 kneeling loops)
KNEEL = dict(body=((-4, -2, 0), (0.5, -12.6, -0.6)), waist=((-5, 0, 0), Z), chest=((-9, 0, -1), Z), neck=((-5, 0, 0), Z), head=((-3, 0, 0), Z),
             jaw=((10, 0, 0), Z), right_clavicle=((0, 4, -6), Z), left_clavicle=((0, -4, 6), Z),
             footL=dict(d=(2.0, 0, -9.0), yaw=6), footR=dict(d=(-1.5, 2.6, 13.0), yaw=-6, pitch=-62, pivot='toe'))
PLANT = dict(grip=(4.5, 34.0, -22.5), tip=(4.3, -8.0, -23.2), mode='cane')
KPOLE_R = (8, 6, -32)
def kn(n, t, d=Z, p=Z, e='smooth'):
    r, ps = KNEEL[n]; return (t, L.add3(r, d), L.add3(ps, p), e)
if want('withered_king_phase_transition'):
    begin('withered_king_phase_transition', 4.5, 'once')
    event(0.0, 'falter'); event(1.25, 'plant_begin'); event(2.35, 'sword_impact'); event(2.55, 'kneel_begin'); event(4.5, 'kneeling_reached')
    fk('body', [st('body', 0), st('body', 0.25, d=(-6, 4, 3), p=(0.4, -2.6, -0.6), e='out'), st('body', 0.6, d=(-3, 0, -2), p=(0.8, -2.0, 0.8), e='inout'),
                st('body', 0.9, d=(-7, 2, 1), p=(0.4, -3.2, -0.2), e='inout'), st('body', 1.25, d=(-5, 0, 0), p=(0.5, -2.8, 0.4)),
                (1.95, (-1, 0, 0), (0.5, -1.4, 0.6), 'inout'), (2.25, (-1, 0, 0), (0.5, -1.2, 0.6), 'in'), (2.38, (-6, 0, 0), (0.5, -3.6, -0.2), 'out'),
                (2.55, (-5, 0, 0), (0.5, -3.0, 0.0), 'inout'), (3.4, (-7, -1, 0), (0.5, -8.0, -0.8), 'inout'), (4.0, kn('body', 0)[1], L.add3(KNEEL['body'][1], (0, 0.4, 0)), 'out'),
                kn('body', 4.5)])
    fk('waist', [st('waist', 0), st('waist', 0.3, d=(-6, 0, 0), e='out'), st('waist', 0.9, d=(-7, 0, 0)), (1.9, (-2, 0, 0)), (2.4, (-6, 0, 0), None, 'out'), (3.4, (-6, 0, 0)), kn('waist', 4.5)])
    fk('chest', [st('chest', 0), st('chest', 0.25, d=(-8, 3, 2), e='out'), st('chest', 0.6, d=(-4, -2, -1)), st('chest', 0.95, d=(-10, 0, 1)), st('chest', 1.25, d=(-8, 0, 0)),
                 (1.9, (2, 0, 0), (0, 0.4, 0), 'inout'), (2.25, (3, 0, 0), (0, 0.5, 0), 'in'), (2.4, (-12, 0, 0), Z, 'out'), (3.4, (-12, 0, 0)), (4.1, (-17, 0, -1), Z, 'out'), kn('chest', 4.5)])
    fk('neck', [st('neck', 0), st('neck', 0.3, d=(-6, 0, 0)), st('neck', 1.2, d=(-4, 0, 0)), (1.9, (2, 0, 0)), (2.4, (-8, 0, 0), None, 'out'), kn('neck', 4.5)])
    fk('head', [st('head', 0), st('head', 0.25, d=(-10, 4, 4), e='out'), st('head', 0.65, d=(-4, -2, -2)), st('head', 1.2, d=(-8, 0, 0)), (1.9, (6, 0, 0)), (2.25, (8, 0, 0), None, 'in'),
                (2.42, (-12, 0, 0), None, 'out'), (3.4, (-8, 0, 0)), (4.3, (-15, 0, 2)), kn('head', 4.5)])
    fk('jaw', [st('jaw', 0), st('jaw', 0.25, d=(14, 0, 0), e='out'), st('jaw', 1.0, d=(6, 0, 0)), (2.3, (4, 0, 0)), (2.42, (22, 0, 0), None, 'out'), (3.0, (12, 0, 0)), kn('jaw', 4.5)])
    fk('right_clavicle', [st('right_clavicle', 0), st('right_clavicle', 0.3, d=(0, 0, -5)), st('right_clavicle', 1.2, d=(0, 0, -6)), (2.25, (0, 4, 4)), (2.4, (0, 4, -4), None, 'out'), kn('right_clavicle', 4.5)])
    fk('left_clavicle', [st('left_clavicle', 0), st('left_clavicle', 0.3, d=(0, 0, 3)), (2.25, (0, -4, -4)), (2.4, (0, -4, 4), None, 'out'), kn('left_clavicle', 4.5)])
    # feet: a stumble back with the left foot; the knee goes down slowly onto the right
    feet('L', [(0, dict(d=Z), 'smooth'), (0.42, dict(d=Z), 'out'), (0.6, dict(d=(0.5, 3.0, 2.0), pitch=6, pivot='ankle'), 'smooth'), (0.78, dict(d=(1.0, 0, 3.5), yaw=4), 'smooth'),
               (2.55, dict(d=(1.0, 0, 3.5), yaw=4), 'out'), (2.85, dict(d=(1.8, 3.6, -3.0), yaw=6, pitch=6, pivot='ankle'), 'smooth'), (3.1, KNEEL['footL'], 'smooth'), (4.5, KNEEL['footL'], 'smooth')])
    feet('R', [(0, dict(d=Z), 'smooth'), (3.1, dict(d=Z), 'out'), (3.3, dict(d=(-0.5, 2.0, 2.5), yaw=-4), 'smooth'), (3.7, dict(d=(-1.2, 3.8, 9.0), yaw=-6, pitch=-35, pivot='toe'), 'smooth'),
               (4.2, KNEEL['footR'], 'smooth'), (4.5, KNEEL['footR'], 'smooth')])
    pole('POLE_knee.R', [(0, (8.14, 19.12, -33.86), 'smooth'), (3.2, (8.14, 19.12, -33.86), 'smooth'), (4.0, KPOLE_R, 'smooth'), (4.5, KPOLE_R, 'smooth')])
    # sword: lowered and dragged as he falters, swung round to stand point-down before him, driven into the ground
    def pt_sword(t):
        if t <= 1.25:
            u = smooth(t / 1.25); g = V(DRAG_GRIP) + V((0.5, -3.0, 1.5)) * sin(pi * min(1, u * 1.4)) * 0.8
            return drag(tuple(g), DRAG_HEAD + 6 * u)
        if t <= 1.95:            # swung up in front, rotating to vertical, point down
            u = smooth((t - 1.25) / 0.7)
            s0 = drag(tuple(V(DRAG_GRIP) + V((0.4, -2.4, 1.2))), DRAG_HEAD + 6)
            g0 = V(s0['grip']); b0 = (V(s0['tip']) - g0).normalized()
            g1 = V(PLANT['grip']) + V((0.5, 14.0, 1.0)); b1 = V(norm((0.0, -1, -0.04)))
            mid = V(norm((0.75, -0.25, -0.6)))
            b = b0.slerp(mid, min(1, u * 2)) if u < 0.5 else mid.slerp(b1, (u - 0.5) * 2)
            return dict(grip=tuple(g0.lerp(g1, u) + V((3.0, 3.0, -4.0)) * sin(pi * u)), blade=tuple(b), mode='cane')
        if t <= 2.25:            # raised: gathered strength
            u = smooth((t - 1.95) / 0.3); g = V(PLANT['grip']) + V((0.5, 14.0 + 2.0 * u, 1.0))
            return dict(grip=tuple(g), blade=norm((0.0, -1, -0.04)), mode='cane')
        if t <= 2.35:            # driven down
            u = ((t - 2.25) / 0.1) ** 2; g = V(PLANT['grip']) + V((0.5, 16.0, 1.0)).lerp(V((0, 0, 0)), u)
            return dict(grip=tuple(g), blade=norm((0.0, -1, -0.04)), mode='cane')
        return dict(grip=PLANT['grip'], blade=norm((0.0, -1, -0.04)), mode='cane')
    sword_dense(pt_sword, 0.0, 4.5)
    grip('R', [(0, 'cane', 0)])
    grip('L', [(0, 'free', 0), (1.5, 'cane', 0.45)])
    hands('L', [(0, LEFT_RELAX, 'smooth'), (0.3, {'off': ((1.5, -1.0, 0.5), (6, 0, 2)), 'space': 'chest'}, 'out'), (1.3, {'off': ((3, 3, -6), (-24, 0, -8)), 'space': 'chest'}, 'smooth'),
                (4.5, {'off': ((3, 3, -6), (-24, 0, -8)), 'space': 'chest'}, 'smooth')])
    fingers('L', [(0, 22, 0, 'smooth'), (0.3, 14, 4, 'out'), (1.6, 20, 6, 'smooth'), (1.9, 76, 0, 'out'), (4.5, 80, 0, 'smooth')])
    fingers('R', [(0, 0, 0, 'smooth'), (2.2, 6, 0, 'smooth'), (2.4, 10, 0, 'out'), (4.5, 8, 0, 'smooth')])
    finish()

# ================================================================== 06 kneeling (3.0 s loop) - invulnerable while the minions live
if want('withered_king_kneeling'):
    begin('withered_king_kneeling', 3.0, 'loop')
    fk('body', [kn('body', 0), kn('body', 1.2, d=(0.8, 0, 0), p=(0, 0.35, 0)), kn('body', 2.1, d=(-0.3, 0, 0), p=(0, -0.15, 0)), kn('body', 3.0)])
    fk('waist', [kn('waist', 0), kn('waist', 1.3, d=(1, 0, 0)), kn('waist', 3.0)])
    fk('chest', [kn('chest', 0), kn('chest', 1.1, d=(3.2, 0.8, 0), p=(0, 0.5, 0)), kn('chest', 1.5, d=(3.0, 0.8, 0), p=(0, 0.45, 0)), kn('chest', 2.3, d=(-0.6, -0.4, 0)), kn('chest', 3.0)])
    fk('neck', [kn('neck', 0), kn('neck', 1.4, d=(2, 2, 0)), kn('neck', 3.0)])
    fk('head', [kn('head', 0), kn('head', 0.8, d=(-2, 4, -3)), kn('head', 1.6, d=(1, 0, 0)), kn('head', 2.4, d=(-2, -4, 3)), kn('head', 3.0)])
    fk('jaw', [kn('jaw', 0), kn('jaw', 0.4, d=(5, 0, 0)), kn('jaw', 0.7, d=(-2, 0, 0)), kn('jaw', 1.2, d=(8, 0, 0)), kn('jaw', 1.7, d=(0, 0, 0)), kn('jaw', 2.3, d=(6, 0, 0)), kn('jaw', 3.0)])
    # shoulders: a faint, uneven tremble of strain
    tr = [(round(t, 2), (0, 0, KNEEL['right_clavicle'][0][2] + 0.6 * sin(t * 23) + 0.4 * sin(t * 37))) for t in [k * 0.15 for k in range(21)]]
    fk('right_clavicle', [(t, (0, 4, z[2])) for t, z in tr[:-1]] + [(3.0, KNEEL['right_clavicle'][0])])
    fk('left_clavicle', [(t, (0, -4, 6 - 0.5 * sin(t * 29))) for t, z in tr[:-1]] + [(3.0, KNEEL['left_clavicle'][0])])
    feet('L', [(0, KNEEL['footL'], 'smooth'), (3.0, KNEEL['footL'], 'smooth')]); feet('R', [(0, KNEEL['footR'], 'smooth'), (3.0, KNEEL['footR'], 'smooth')])
    pole('POLE_knee.R', [(0, KPOLE_R, 'smooth'), (3.0, KPOLE_R, 'smooth')])
    sword([(0, PLANT, 'smooth'), (3.0, PLANT, 'smooth')])
    grip('R', [(0, 'cane', 0)]); grip('L', [(0, 'cane', 0)])
    fingers('L', [(0, 80, 0, 'smooth'), (1.5, 84, 0, 'smooth'), (3.0, 80, 0, 'smooth')]); fingers('R', [(0, 8, 0, 'smooth'), (1.5, 11, 0, 'smooth'), (3.0, 8, 0, 'smooth')])
    event(0.0, 'summon_aura_loop')
    finish()

# ================================================================== 07 phase-two roar (5.2 s) - awakening 0-1.0, rising 1.0-2.9, howl 2.9-5.2
if want('withered_king_phase_two_roar'):
    begin('withered_king_phase_two_roar', 5.2, 'once')
    event(0.1, 'rumble'); event(1.0, 'rise_begin'); event(2.6, 'sword_pulled_free'); event(2.9, 'howl_begin'); event(3.05, 'howl_burst'); event(5.2, 'damageable')
    fk('body', [kn('body', 0), kn('body', 1.0, d=(0.5, 0, 0)), kn('body', 1.4, d=(-4, 0, 0), p=(0, 0.8, -0.8), e='inout'), (2.2, (-6, 0, 0), (0.4, -5.0, -0.4), 'inout'),
                (2.75, (-2, 0, 0), (0.4, -1.4, 0.2), 'out'), (2.95, (1, 0, 0), (0.2, -0.6, 0.6), 'inout'), (3.2, (4, 0, 0), (0, 0.3, 1.0), 'out'), (4.5, (3, 0, 0), (0, 0.2, 0.9)),
                st('body', 5.2)])
    fk('waist', [kn('waist', 0), kn('waist', 1.4, d=(-2, 0, 0)), (2.4, (-3, 0, 0)), (3.2, (5, 0, 0), None, 'out'), (4.5, (4, 0, 0)), st('waist', 5.2)])
    fk('chest', [kn('chest', 0), kn('chest', 0.9, d=(3, 0, 0)), kn('chest', 1.4, d=(6, 0, 0), p=(0, 0.6, 0)), (2.2, (-8, 0, 0)), (2.8, (-2, 0, 0)), (3.1, (14, 0, 0), (0, 1.2, 0.3), 'out'),
                (4.5, (12, 0, 0), (0, 1.0, 0.3)), st('chest', 5.2)])
    fk('neck', [kn('neck', 0), kn('neck', 1.0, d=(6, 0, 0)), (2.6, (-2, 0, 0)), (3.1, (14, 0, 0), None, 'out'), (4.5, (12, 0, 0)), st('neck', 5.2)])
    fk('head', [kn('head', 0), kn('head', 0.3, d=(-1, 0, 0)), kn('head', 1.0, d=(14, 0, 0), e='inout'), (2.6, (2, 0, 0)), (3.12, (26, 0, 0), None, 'out')] +
               [(3.2 + 0.1 * k, (25 + (1.2 if k % 2 else -1.2), 0.8 * ((-1) ** k), 0), None, 'linear') for k in range(13)] + [(4.6, (22, 0, 0)), st('head', 5.2)])
    fk('jaw', [kn('jaw', 0), (0.8, (14, 0, 0)), (2.7, (6, 0, 0)), (2.9, (2, 0, 0), None, 'in'), (3.12, (36, 0, 0), None, 'out'), (4.4, (33, 0, 0)), (4.8, (10, 0, 0)), st('jaw', 5.2)])
    # shoulders tremble, then draw back as the chest swells
    rc = [(0, KNEEL['right_clavicle'][0])] + [(0.3 + 0.07 * k, (0, 4, -6 + (1.5 if k % 2 else -0.5))) for k in range(10)] + [(1.4, (0, 2, 4)), (2.6, (0, 0, 2)), (3.1, (0, -10, 6), None, 'out'), (4.6, (0, -8, 5))]
    lc = [(0, KNEEL['left_clavicle'][0])] + [(0.3 + 0.07 * k, (0, -4, 6 - (1.5 if k % 2 else -0.5))) for k in range(10)] + [(1.4, (0, -2, -4)), (2.6, (0, 0, -2)), (3.1, (0, 10, -6), None, 'out'), (4.6, (0, 8, -5))]
    fk('right_clavicle', rc + [st('right_clavicle', 5.2)]); fk('left_clavicle', lc + [st('left_clavicle', 5.2)])
    # rising: the planted left foot drives, the knee lifts, the right foot comes forward under him
    feet('L', [(0, KNEEL['footL'], 'smooth'), (2.3, KNEEL['footL'], 'out'), (2.55, dict(d=(1.0, 2.6, -4.0), yaw=3, pitch=5, pivot='ankle'), 'smooth'), (2.8, dict(d=Z), 'smooth'), (5.2, dict(d=Z), 'smooth')])
    feet('R', [(0, KNEEL['footR'], 'smooth'), (1.55, KNEEL['footR'], 'out'), (1.85, dict(d=(-1.0, 4.0, 6.0), yaw=-4, pitch=-20, pivot='ankle'), 'smooth'), (2.15, dict(d=(0, 0, 1.0)), 'smooth'), (5.2, dict(d=Z), 'smooth')])
    pole('POLE_knee.R', [(0, KPOLE_R, 'smooth'), (1.5, KPOLE_R, 'smooth'), (2.2, (8.14, 19.12, -33.86), 'smooth'), (5.2, (8.14, 19.12, -33.86), 'smooth')])
    def roar_sword(t):
        if t <= 2.45: return dict(PLANT)
        if t <= 2.9:                                             # wrenched up out of the earth
            u = smooth((t - 2.45) / 0.45); g = V(PLANT['grip']) + V((6.0 * u, 12.0 * u - 2.0 * sin(pi * u), 6.0 * u))
            return dict(grip=tuple(g), blade=norm((0.15 * u, -1, -0.04 + 0.1 * u)), mode='cane')
        g2 = V(PLANT['grip']) + V((6.0, 12.0, 6.0))
        if t <= 3.15:                                            # lowered to his side as the howl begins: point down, arm spread
            u = smooth((t - 2.9) / 0.25); g3 = V((20.0, 31.0, -3.0)); return dict(grip=tuple(g2.lerp(g3, u)), blade=norm((0.25 * u + 0.15 * (1 - u), -1, 0.05)), mode='cane')
        if t <= 4.6: return dict(grip=(20.0, 31.0, -3.0), blade=norm((0.25, -1, 0.05)), mode='cane')
        u = smooth((t - 4.6) / 0.6); s1 = STAND_SWORD; g = V((20.0, 31.0, -3.0)).lerp(V(s1['grip']), u)
        b = V(norm((0.25, -1, 0.05))).slerp((V(s1['tip']) - V(s1['grip'])).normalized(), u)
        return dict(grip=tuple(g), blade=tuple(b), mode='cane')
    sword_dense(roar_sword, 0.0, 5.2)
    grip('R', [(0, 'cane', 0)]); grip('L', [(0, 'cane', 0), (2.7, 'free', 0.4)])
    hands('L', [(0, {'off': ((3, 3, -6), (-24, 0, -8)), 'space': 'chest'}, 'smooth'), (2.75, {'off': ((3, 3, -6), (-24, 0, -8)), 'space': 'chest'}, 'smooth'),
                (3.15, {'off': ((-6.0, 6.0, 1.0), (10, 0, -38)), 'space': 'chest'}, 'out'), (4.6, {'off': ((-6.5, 6.5, 1.0), (10, 0, -40)), 'space': 'chest'}, 'smooth'), (5.2, LEFT_RELAX, 'smooth')])
    fingers('L', [(0, 80, 0, 'smooth'), (0.4, 92, 0, 'smooth'), (2.7, 92, 0, 'smooth'), (3.1, -10, 14, 'out'), (4.6, -6, 12, 'smooth'), (5.2, 22, 0, 'smooth')])
    fingers('R', [(0, 8, 0, 'smooth'), (0.4, 16, 0, 'smooth'), (2.9, 12, 0, 'smooth'), (5.2, 0, 0, 'smooth')])
    finish()

# ================================================================== 08 hand shockwave (2.2 s) - anticipation 0-0.65, release 0.65-0.95, recovery 0.95-2.2
if want('withered_king_hand_shockwave'):
    begin('withered_king_hand_shockwave', 2.2, 'once')
    event(0.0, 'windup_begin'); event(0.2, 'palm_charge'); event(0.65, 'release_begin'); event(0.82, 'shockwave'); event(0.95, 'recovery_begin'); event(2.2, 'recovery_end')
    fk('body', [st('body', 0), st('body', 0.6, d=(2, 12, 0), p=(-0.6, -1.0, 1.6), e='inout'), st('body', 0.68, d=(2, 13, 0), p=(-0.6, -1.1, 1.8), e='in'),
                st('body', 0.86, d=(-5, -10, 0), p=(0.2, -2.0, -2.6), e='out'), st('body', 1.25, d=(-6, -12, 0), p=(0.3, -2.2, -3.0)), st('body', 1.9, d=(-1, -2, 0), p=(0, -0.3, -0.4), e='inout'), st('body', 2.2)])
    fk('waist', [st('waist', 0), st('waist', 0.62, d=(1, 6, 0), e='inout'), st('waist', 0.9, d=(-4, -6, 0), e='out'), st('waist', 1.3, d=(-4, -7, 0)), st('waist', 2.2)])
    fk('chest', [st('chest', 0), st('chest', 0.62, d=(4, 16, 0), e='inout'), st('chest', 0.7, d=(5, 17, 0), e='in'), st('chest', 0.9, d=(-9, -16, 0), e='out'),
                 st('chest', 1.3, d=(-10, -18, 0)), st('chest', 1.95, d=(-2, -3, 0), e='inout'), st('chest', 2.2)])
    fk('neck', [st('neck', 0), st('neck', 0.65, d=(-2, -12, 0)), st('neck', 0.92, d=(-2, 12, 0), e='out'), st('neck', 1.4, d=(-2, 13, 0)), st('neck', 2.2)])
    fk('head', [st('head', 0), st('head', 0.65, d=(-4, -14, 0)), st('head', 0.92, d=(-3, 14, 0), e='out'), st('head', 1.4, d=(-2, 15, 0)), st('head', 2.2)])
    fk('jaw', [st('jaw', 0), st('jaw', 0.65, d=(2, 0, 0)), st('jaw', 0.85, d=(28, 0, 0), e='out'), st('jaw', 1.3, d=(18, 0, 0)), st('jaw', 2.2)])
    fk('left_clavicle', [st('left_clavicle', 0), st('left_clavicle', 0.65, d=(0, 10, -4)), st('left_clavicle', 0.88, d=(0, -14, -2), e='out'), st('left_clavicle', 1.3, d=(0, -15, -2)), st('left_clavicle', 2.2)])
    fk('right_clavicle', [st('right_clavicle', 0), st('right_clavicle', 0.65, d=(0, 0, 4)), st('right_clavicle', 2.2)])
    FL = dict(d=(1.0, 0, -4.0), yaw=6)
    feet('L', [(0, dict(d=Z), 'smooth'), (0.05, dict(d=Z), 'out'), (0.2, dict(d=(0.5, 2.8, -2.0), pitch=5, pivot='ankle'), 'smooth'), (0.34, FL, 'smooth'),
               (1.7, FL, 'out'), (1.85, dict(d=(0.5, 2.4, -2.0), pitch=4, pivot='ankle'), 'smooth'), (2.0, dict(d=Z), 'smooth'), (2.2, dict(d=Z), 'smooth')])
    feet('R', [(0, dict(d=Z), 'smooth'), (2.2, dict(d=Z), 'smooth')])
    # the sword is stood point-down beside him to steady him through the blast
    STEADY = dict(grip=(19.0, 32.0, -9.5), tip=(21.0, -0.6, -7.5), mode='cane')
    def sw_sword(t):
        if t <= 0.35:
            u = smooth(t / 0.35); g = V(STAND_SWORD['grip']).lerp(V(STEADY['grip']), u)
            b = (V(STAND_SWORD['tip']) - V(STAND_SWORD['grip'])).normalized().slerp((V(STEADY['tip']) - V(STEADY['grip'])).normalized(), u)
            return dict(grip=tuple(g), blade=tuple(b), mode='cane')
        if t <= 1.8: return STEADY
        u = smooth((t - 1.8) / 0.4); g = V(STEADY['grip']).lerp(V(STAND_SWORD['grip']), u)
        b = (V(STEADY['tip']) - V(STEADY['grip'])).normalized().slerp((V(STAND_SWORD['tip']) - V(STAND_SWORD['grip'])).normalized(), u)
        return dict(grip=tuple(g), blade=tuple(b), mode='cane')
    sword_dense(sw_sword, 0.0, 2.2)
    grip('R', [(0, 'cane', 0)]); grip('L', [(0, 'free', 0)])
    PUP = norm((0.06, 1, 0.12)); PFW = (0, 0, -1)
    hands('L', [(0, LEFT_RELAX, 'smooth'), (0.62, {'palm': ((-20, 52, 5), PUP, PFW)}, 'inout'), (0.7, {'palm': ((-20, 52.5, 6), PUP, PFW)}, 'in'),
                (0.86, {'palm': ((-10, 49, -33), PUP, PFW)}, 'out'), (1.25, {'palm': ((-10, 49.5, -34), PUP, PFW)}, 'smooth'),
                (1.6, {'palm': ((-15, 42, -22), norm((0, 0.4, -0.9)), norm((0.4, 0.2, -0.9)))}, 'inout'), (2.2, LEFT_RELAX, 'smooth')])
    fingers('L', [(0, 22, 0, 'smooth'), (0.5, -18, 16, 'out'), (0.7, -20, 18, 'smooth'), (0.86, -24, 20, 'out'), (1.3, -22, 18, 'smooth'), (1.8, 20, 4, 'smooth'), (2.2, 22, 0, 'smooth')])
    fingers('R', [(0, 0, 0, 'smooth'), (0.4, 10, 0, 'smooth'), (1.8, 10, 0, 'smooth'), (2.2, 0, 0, 'smooth')])
    finish()

# ================================================================== 09 ground stomp (2.7 s) - anticipation 0-1.15, stomp 1.15-1.42 (impact 1.38), recovery 1.42-2.7
if want('withered_king_ground_stomp'):
    begin('withered_king_ground_stomp', 2.7, 'once')
    event(0.0, 'windup_begin'); event(0.4, 'warning'); event(1.15, 'stomp_begin'); event(1.38, 'impact'); event(1.42, 'recovery_begin'); event(2.7, 'recovery_end')
    fk('body', [st('body', 0), st('body', 0.4, d=(0, 0, -4), p=(3.2, -2.6, 0.4), e='inout'), st('body', 0.95, d=(5, 2, -5), p=(3.6, -0.6, 1.0), e='out'),
                st('body', 1.15, d=(6, 2, -5), p=(3.6, -0.5, 1.1), e='expo_in'), st('body', 1.38, d=(-7, 0, 1), p=(0.8, -5.4, -0.6), e='out'),
                st('body', 1.5, d=(-8, 0, 1), p=(0.7, -6.0, -0.7)), st('body', 1.68, d=(-4, 0, 0.5), p=(0.5, -4.0, -0.3), e='inout'), st('body', 2.7)])
    fk('waist', [st('waist', 0), st('waist', 0.95, d=(3, 0, 3)), st('waist', 1.15, d=(3.5, 0, 3), e='expo_in'), st('waist', 1.4, d=(-6, 0, 0), e='out'), st('waist', 1.7, d=(-3, 0, 0)), st('waist', 2.7)])
    fk('chest', [st('chest', 0), st('chest', 0.95, d=(8, 4, 6)), st('chest', 1.15, d=(9, 4, 6), e='expo_in'), st('chest', 1.41, d=(-15, 0, -1), e='out'),
                 st('chest', 1.52, d=(-17, 0, -1)), st('chest', 1.75, d=(-6, 0, 0), e='inout'), st('chest', 2.7)])
    fk('neck', [st('neck', 0), st('neck', 0.95, d=(-4, 0, -2)), st('neck', 1.42, d=(-4, 0, 0), e='out'), st('neck', 1.5, d=(-10, 0, 1)), st('neck', 1.65, d=(-2, 0, 0)), st('neck', 2.7)])
    fk('head', [st('head', 0), st('head', 0.95, d=(-4, 0, -3)), st('head', 1.42, d=(-2, 0, 0), e='out'), st('head', 1.5, d=(-8, 0, 2)), st('head', 1.66, d=(0, 0, -1)), st('head', 2.7)])
    fk('jaw', [st('jaw', 0), st('jaw', 1.0, d=(6, 0, 0)), st('jaw', 1.38, d=(4, 0, 0)), st('jaw', 1.46, d=(28, 0, 0), e='out'), st('jaw', 1.9, d=(12, 0, 0)), st('jaw', 2.7)])
    fk('right_clavicle', [st('right_clavicle', 0), st('right_clavicle', 0.95, d=(0, 0, 8)), st('right_clavicle', 1.4, d=(0, 2, -4), e='out'), st('right_clavicle', 2.7)])
    fk('left_clavicle', [st('left_clavicle', 0), st('left_clavicle', 0.95, d=(0, 0, -10)), st('left_clavicle', 1.4, d=(0, 0, 4), e='out'), st('left_clavicle', 2.7)])
    FL = dict(d=Z)
    feet('L', [(0, FL, 'smooth'), (0.35, FL, 'inout'), (0.95, dict(d=(1.5, 15.0, -2.0), pitch=12, pivot='ankle'), 'smooth'), (1.15, dict(d=(1.5, 15.6, -2.2), pitch=14, pivot='ankle'), 'expo_in'),
               (1.38, FL, 'smooth'), (2.7, FL, 'smooth')])
    feet('R', [(0, dict(d=Z), 'smooth'), (2.7, dict(d=Z), 'smooth')])
    OUT = dict(grip=(23.0, 31.0, -6.0), blade=norm((0.45, -0.75, 0.45)), mode='cane')
    def st_sword(t):
        g0, b0 = V(STAND_SWORD['grip']), (V(STAND_SWORD['tip']) - V(STAND_SWORD['grip'])).normalized()
        if t <= 0.95:          # lifted off the ground and held out to counter the raised leg
            u = smooth(t / 0.95); return dict(grip=tuple(g0.lerp(V(OUT['grip']), u)), blade=tuple(b0.slerp(V(OUT['blade']), u)), mode='cane')
        if t <= 1.15: return OUT
        if t <= 1.5:           # the jolt runs down the arm: the point jumps
            u = (t - 1.15) / 0.35; jolt = math.exp(-((t - 1.42) / 0.05) ** 2)
            return dict(grip=tuple(V(OUT['grip']) + V((0, -3.0 * smooth(u) - 1.5 * jolt, 0))), blade=tuple(V(OUT['blade']).slerp(V(norm((0.45, -0.9, 0.3))), smooth(u))), mode='cane')
        u = smooth((t - 1.5) / 0.9); gA = V(OUT['grip']) + V((0, -3.0, 0)); bA = V(norm((0.45, -0.9, 0.3)))
        if u >= 1: return STAND_SWORD
        return dict(grip=tuple(gA.lerp(g0, u)), blade=tuple(bA.slerp(b0, u)), mode='cane')
    sword_dense(st_sword, 0.0, 2.7)
    grip('R', [(0, 'cane', 0)]); grip('L', [(0, 'free', 0)])
    hands('L', [(0, LEFT_RELAX, 'smooth'), (0.95, {'off': ((-7, 16, -6), (-40, 0, -52)), 'space': 'chest'}, 'smooth'), (1.15, {'off': ((-7, 16.5, -6), (-40, 0, -54)), 'space': 'chest'}, 'expo_in'),
                (1.42, {'off': ((1, 3, -6), (-18, 0, -8)), 'space': 'chest'}, 'out'), (1.6, {'off': ((2, 4, -7), (-22, 0, -10)), 'space': 'chest'}, 'smooth'), (2.7, LEFT_RELAX, 'smooth')])
    fingers('L', [(0, 22, 0, 'smooth'), (0.95, 6, 10, 'smooth'), (1.38, 40, 0, 'out'), (2.7, 22, 0, 'smooth')])
    finish()

# ================================================================== 10 death - The King's Last Rest (10.5 s)
#   mortal injury 0-1.3 | to one knee 1.3-3.1 | planting the sword 3.1-4.4 | the crown 4.4-6.3 | crown to the sword 6.3-8.4 | death 8.4-10.0 | hold
if want('withered_king_death'):
    begin('withered_king_death', 10.5, 'hold')
    for t_, k_ in ((0.0, 'mortal_blow'), (1.3, 'knee_begin'), (2.6, 'knee_down'), (3.1, 'plant_begin'), (4.05, 'sword_impact'), (4.4, 'crown_reach'),
                   (5.3, 'crown_grasp'), (6.3, 'crown_to_sword'), (7.55, 'crown_placed'), (7.75, 'crown_released'), (8.4, 'final_moments'),
                   (9.1, 'last_breath'), (10.0, 'still'), (10.5, 'complete')):
        event(t_, k_)
    DK = dict(footL=dict(d=(2.2, 0, -8.5), yaw=8), footR=dict(d=(-1.5, 2.6, 12.0), yaw=-6, pitch=-62, pivot='toe'))
    DPL = dict(grip=(7.0, 31.0, -24.0), tip=(6.8, -10.5, -24.6), mode='cane')
    fk('body', [st('body', 0), st('body', 0.18, d=(8, -4, 0), p=(0.5, -1.4, 2.4), e='out'), st('body', 0.6, d=(4, -2, 0), p=(0.5, -2.2, 3.6)),
                st('body', 1.3, d=(-2, 0, 0), p=(0.5, -3.6, 2.4), e='inout'), (2.0, (-6, -1, 0), (0.5, -8.0, 0.5), 'inout'), (2.6, (-8, -2, 0), (0.5, -12.2, -0.8), 'out'),
                (3.1, (-8, -2, 0), (0.5, -12.4, -0.8)), (3.6, (-4, -2, 0), (0.5, -11.6, -0.4)), (4.05, (-9, -2, 0), (0.5, -12.8, -1.0), 'out'), (4.4, (-8, -2, 0), (0.5, -12.6, -1.0)),
                (8.4, (-7, -2, 0), (0.5, -12.6, -1.0)), (9.0, (-6, -2, 0), (0.5, -12.4, -0.9)), (9.6, (-9, -2, 0), (0.5, -12.6, -1.2), 'inout'), (10.0, (-11, -2, -1), (0.5, -12.6, -1.4), 'out'),
                (10.5, (-11, -2, -1), (0.5, -12.6, -1.4))])
    fk('waist', [st('waist', 0), st('waist', 0.2, d=(8, 0, 0), e='out'), st('waist', 1.3, d=(-2, 0, 0)), (2.6, (-8, 0, 0)), (4.4, (-7, 0, 0)), (9.0, (-6, 0, 0)), (10.0, (-14, 0, 0), None, 'out'), (10.5, (-14, 0, 0))])
    fk('chest', [st('chest', 0), st('chest', 0.15, d=(14, -4, 0), e='out'), st('chest', 0.6, d=(4, -2, 0)), st('chest', 1.3, d=(-8, 0, 0)), (2.6, (-16, 0, -1)),
                 (3.3, (-12, 0, 0)), (3.9, (-6, 0, 0)), (4.1, (-14, 0, 0), None, 'out'), (4.6, (-12, 0, 0)), (5.5, (-8, 0, 1)), (6.3, (-9, 0, 0)), (7.5, (-12, 0, 0)), (8.4, (-14, 0, 0)),
                 (8.7, (-11, 0, 0), (0, 0.6, 0), 'inout'), (9.1, (-10, 0, 0), (0, 0.7, 0)), (9.6, (-14, 0, 0), Z, 'inout'), (10.0, (-17, 0, 6), Z, 'out'), (10.5, (-17, 0, 6), Z)])
    fk('neck', [st('neck', 0), st('neck', 0.15, d=(10, 0, 0), e='out'), st('neck', 1.3, d=(-6, 0, 0)), (2.6, (-10, 0, 0)), (4.4, (-8, 0, 0)), (5.6, (-4, 0, 0)), (6.0, (-14, 0, 0)),
                (7.6, (-14, 0, 0)), (8.4, (-16, 0, 0)), (9.6, (-14, 0, 0)), (10.0, (-10, 6, 9), None, 'out'), (10.5, (-10, 6, 9))])
    fk('head', [st('head', 0), st('head', 0.12, d=(18, 6, 0), e='out'), st('head', 0.6, d=(4, 2, 0)), st('head', 1.3, d=(-10, 0, 0)), (2.6, (-14, 0, 2)), (4.4, (-10, 0, 0)),
                (5.4, (-4, 2, 0)), (6.0, (-18, 0, 0), None, 'inout'), (6.3, (-18, 0, 0)), (7.4, (-16, -6, 0)), (8.4, (-18, -4, 0)), (8.8, (-14, -2, 0)), (9.6, (-18, 0, 2)),
                (10.0, (-14, 10, 20), None, 'out'), (10.5, (-14, 10, 20))])
    fk('jaw', [st('jaw', 0), st('jaw', 0.12, d=(26, 0, 0), e='out'), st('jaw', 0.8, d=(10, 0, 0)), (2.6, (8, 0, 0)), (9.0, (6, 0, 0)), (9.15, (14, 0, 0), None, 'out'),
               (9.6, (10, 0, 0)), (10.0, (22, 0, 0), None, 'out'), (10.5, (22, 0, 0))])
    fk('right_clavicle', [st('right_clavicle', 0), st('right_clavicle', 0.3, d=(0, 0, -6)), (2.6, (0, 4, -8)), (4.4, (0, 4, -6)), (8.4, (0, 2, -8)), (10.0, (0, 6, -14), None, 'out'), (10.5, (0, 6, -14))])
    fk('left_clavicle', [st('left_clavicle', 0), st('left_clavicle', 0.3, d=(0, 0, 6)), (2.6, (0, -4, 8)), (4.4, (0, -4, 6)), (5.2, (0, 2, -6)), (7.6, (0, -6, 2)), (8.4, (0, -2, 8)),
                         (10.0, (0, -6, 14), None, 'out'), (10.5, (0, -6, 14))])
    feet('R', [(0, dict(d=Z), 'smooth'), (0.25, dict(d=Z), 'out'), (0.45, dict(d=(0.5, 3.0, 4.0), pitch=-4, pivot='ankle'), 'smooth'), (0.65, dict(d=(1.0, 0, 6.0), yaw=-8), 'smooth'),
               (1.7, dict(d=(1.0, 0, 6.0), yaw=-8), 'out'), (2.05, dict(d=(-0.5, 3.6, 10.0), yaw=-6, pitch=-35, pivot='toe'), 'smooth'), (2.6, DK['footR'], 'smooth'), (10.5, DK['footR'], 'smooth')])
    feet('L', [(0, dict(d=Z), 'smooth'), (1.3, dict(d=Z), 'out'), (1.55, dict(d=(1.2, 3.0, -4.0), yaw=4, pitch=5, pivot='ankle'), 'smooth'), (1.85, DK['footL'], 'smooth'), (10.5, DK['footL'], 'smooth')])
    pole('POLE_knee.R', [(0, (8.14, 19.12, -33.86), 'smooth'), (1.7, (8.14, 19.12, -33.86), 'smooth'), (2.4, KPOLE_R, 'smooth'), (10.5, KPOLE_R, 'smooth')])
    # sword: drags as he staggers; leaned on, point on the ground; lifted, turned upright and driven in
    LEAN = dict(grip=(16.5, 28.0, -13.5), tip=(21.0, -0.4, -23.0), mode='cane')
    def d_sword(t):
        if t <= 1.3:
            u = smooth(t / 1.3); s = drag(tuple(V(DRAG_GRIP) + V((0.5, -2.0, 4.0)) * u), DRAG_HEAD + 8 * u); return s
        s0 = drag(tuple(V(DRAG_GRIP) + V((0.5, -2.0, 4.0))), DRAG_HEAD + 8)
        if t <= 2.4:          # swung forward to lean on as he goes down
            u = smooth((t - 1.3) / 1.1); g = V(s0['grip']).lerp(V(LEAN['grip']), u)
            b = (V(s0['tip']) - V(s0['grip'])).normalized().slerp((V(LEAN['tip']) - V(LEAN['grip'])).normalized(), u)
            return dict(grip=tuple(g + V((2.0, 3.0, -3.0)) * sin(pi * u)), blade=tuple(b), mode='cane')
        if t <= 3.1: return LEAN
        if t <= 3.75:         # lifted with what strength remains, turned upright
            u = smooth((t - 3.1) / 0.65); g = V(LEAN['grip']).lerp(V(DPL['grip']) + V((0, 13.0, 0)), u)
            b = (V(LEAN['tip']) - V(LEAN['grip'])).normalized().slerp(V(norm((0.0, -1, -0.015))), u)
            return dict(grip=tuple(g + V((0, 2.0, 0)) * sin(pi * u)), blade=tuple(b), mode='cane')
        if t <= 3.95: return dict(grip=tuple(V(DPL['grip']) + V((0, 13.0, 0))), blade=norm((0.0, -1, -0.015)), mode='cane')
        if t <= 4.05:
            u = ((t - 3.95) / 0.1) ** 2; return dict(grip=tuple(V(DPL['grip']) + V((0, 13.0 * (1 - u), 0))), blade=norm((0.0, -1, -0.015)), mode='cane')
        return dict(grip=DPL['grip'], blade=norm((0.0, -1, -0.015)), mode='cane')
    sword_dense(d_sword, 0.0, 10.5)
    grip('R', [(0, 'cane', 0), (5.6, 'free', 0.6)])
    grip('L', [(0, 'free', 0), (3.0, 'cane', 0.6), (4.25, 'free', 0.4)])
    hands('R', [(0, {'off': ((1, 2, -3), (-10, 0, 0)), 'space': 'chest'}, 'smooth'), (5.6, {'off': ((2, 2, -4), (-12, 0, 4)), 'space': 'chest'}, 'smooth'),
                (6.4, {'off': ((3.0, -4.0, -6.0), (-6, 0, 8)), 'space': 'chest'}, 'inout'), (9.6, {'off': ((3.0, -4.5, -6.0), (-6, 0, 8)), 'space': 'chest'}, 'smooth'),
                (10.1, {'off': ((2.5, -5.5, -3.5), (4, 0, 10)), 'space': 'chest'}, 'out'), (10.5, {'off': ((2.5, -5.5, -3.5), (4, 0, 10)), 'space': 'chest'}, 'smooth')])
    hands('L', [(0, LEFT_RELAX, 'smooth'), (0.15, {'off': ((-6, 8, 4), (16, 0, -40)), 'space': 'chest'}, 'out'), (1.3, {'off': ((1.5, -1.5, 1.0), (8, 0, 2)), 'space': 'chest'}, 'smooth'),
                (3.2, {'off': ((4, 4, -8), (-28, 0, -10)), 'space': 'chest'}, 'smooth'), (4.25, {'off': ((4, 3, -7), (-22, 0, -8)), 'space': 'chest'}, 'smooth'),
                (4.45, {'off': ((2, 1, -3), (-8, 0, -4)), 'space': 'chest'}, 'smooth'), (5.0, {'off': ((2, 18, -4), (-60, 0, -30)), 'space': 'chest'}, 'smooth'),
                (8.4, {'off': ((2.5, 0.0, -5.0), (-14, 0, -6)), 'space': 'chest'}, 'smooth'), (9.6, {'off': ((2.5, -0.5, -5.0), (-14, 0, -6)), 'space': 'chest'}, 'smooth'),
                (10.1, {'off': ((1.5, -4.5, -2.0), (6, 0, 6)), 'space': 'chest'}, 'out'), (10.5, {'off': ((1.5, -4.5, -2.0), (6, 0, 6)), 'space': 'chest'}, 'smooth')])
    # ---- the crown: head -> left hand (5.3) -> resting on the sword's guard (released 7.75)
    T_GRAB, T_PLACE, T_REL = 5.3, 7.55, 7.75
    CROWN_REST = L.WREST['crown']
    # crown space -> sword space when it sits on the guard: crown up (+y) along the handle (+z), centred on the handle
    c_piv = V(L.BONES['crown']['pivot']); s_axis = V((L.GRIP_L.x, L.GRIP_L.y, -7.8))   # crown pivot sits 5.3 px under its rim: rim rests on the guard top
    ON_SWORD = Matrix.Translation(s_axis) @ Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_4x4() @ Matrix.Translation(-c_piv)
    # where the left hand takes hold: palm against the left side of the crown, fingers over the rim
    GRASP = L.frame_from(L.palm_local('left'), V((c_piv.x - 7.0, c_piv.y + 3.0, c_piv.z)), (V((0, -1, 0)), V((1, 0, 0))), (V(norm((0.2, 1, 0))), V((1, 0, 0))))
    def crown_W_on_head(ctx): return ctx['head'] @ CROWN_REST                       # crown space -> world while on the head
    crown_keys = []   # (t, world matrix of crown space) for the carry, filled once the head pose at the grab is known
    def crown_path(t, ctx):
        if t < T_GRAB: return ctx['head']
        if not crown_keys:
            eval_at(T_GRAB); Wg = K_now('head') @ CROWN_REST
            eval_at(T_PLACE); Ws = K_now('sword') @ L.WREST['sword'] @ ON_SWORD
            up = Matrix.Translation(V((0, 4.0, -1.0))) @ Wg
            front = Matrix.Translation(V((-3.0, -10.0, -21.0))) @ Wg
            above = Matrix.Translation(V((0, 12.0, -5.0))) @ Ws
            crown_keys.extend([(T_GRAB, Wg), (5.75, up), (6.2, front), (6.55, front), (7.25, above), (T_PLACE, Ws)])
            eval_at(t)
        if t >= T_PLACE: Wc = crown_keys[-1][1]
        else:
            for (t0, W0), (t1, W1) in zip(crown_keys, crown_keys[1:]):
                if t0 <= t <= t1:
                    u = smooth((t - t0) / (t1 - t0)); l0, q0, _ = W0.decompose(); l1, q1, _ = W1.decompose()
                    Wc = Matrix.Translation(l0.lerp(l1, u)) @ q0.slerp(q1, u).to_matrix().to_4x4(); break
        return Wc @ CROWN_REST.inverted()
    L.crown_track(crown_path)
    def left_override(t, keyed, ctx):
        Kc = ctx['crown']; Wc = Kc @ CROWN_REST
        hand_on = Wc @ GRASP @ L.WREST['left_hand'].inverted()
        if 4.75 <= t < T_GRAB:                     # the hand closes in on the crown
            return L._blend_K(keyed, hand_on, smooth((t - 4.75) / (T_GRAB - 4.75)))
        if T_GRAB <= t < T_REL: return hand_on
        if T_REL <= t < 8.4:                        # released; the arm sinks
            return L._blend_K(hand_on, keyed, smooth((t - T_REL) / (8.4 - T_REL)))
        return None
    L.free_override('L', left_override)
    fingers('L', [(0, 22, 0, 'smooth'), (0.15, 0, 10, 'out'), (1.3, 20, 0, 'smooth'), (3.3, 74, 0, 'out'), (4.25, 74, 0, 'smooth'), (4.45, 10, 6, 'smooth'),
                  (5.05, 4, 8, 'smooth'), (T_GRAB, 58, 0, 'out'), (T_PLACE, 58, 0, 'smooth'), (T_REL, 8, 6, 'out'), (8.4, 24, 0, 'smooth'), (10.0, 40, 0, 'smooth'), (10.5, 40, 0, 'smooth')])
    fingers('R', [(0, 0, 0, 'smooth'), (5.4, 10, 0, 'smooth'), (5.8, 30, 0, 'smooth'), (10.0, 44, 0, 'smooth'), (10.5, 44, 0, 'smooth')])
    finish()

for o in bpy.data.objects: o.select_set(False)
out = os.path.join(L.BM.HERE, 'withered_king_anim.blend')
bpy.ops.wm.save_as_mainfile(filepath=out)
print('SAVED', out, sorted(a.name for a in bpy.data.actions if 'bb_length' in a))
