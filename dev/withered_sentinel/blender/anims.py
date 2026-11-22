"""The 12 Withered Sentinel actions.  Run in Blender on withered_sentinel_rig.blend:
   blender -b withered_sentinel_rig.blend --python anims.py [-- name ...]
All numbers are Blockbench pixels / degrees on top of his rest pose (see anim_lib).  Times in seconds.
Server hit frames these are timed to: sweep 1.30s, push 1.00s, stomp 0.95s, summon impact 1.80s,
awaken flash 2.20s, dash launch 0.45s / land 0.85s."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
import anim_lib as L
from anim_lib import fk, feet, hands, pole, begin, finish, eval_at
ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def want(n): return not ONLY or n in ONLY
Z = (0, 0, 0)
sin, cos, pi = math.sin, math.cos, math.pi

def norm(v):
    l = math.sqrt(sum(x * x for x in v)); return tuple(x / l for x in v)
def blade_dir(a, e):
    """a: degrees around him from straight ahead (+ = his right), e: elevation (+ = up)."""
    a, e = math.radians(a), math.radians(e)
    return (sin(a) * cos(e), sin(e), -cos(a) * cos(e))
def flat_for(blade, up=(0, 1, 0)):
    b = Vector(blade); u = Vector(up); f = (u - b * b.dot(u)).normalized(); return tuple(f)

# ----------------------------------------------------------------- shared stances
# combat stance: left foot forward, sword foot back, hips low and turned a touch to his right
CS = dict(
    body=((-3, -8, 0), (0.6, -3.0, 0.8)), waist=((-4, 3, 0), Z), chest=((-6, 6, -1), Z), head=((2, -3, 0), Z), jaw=((2, 0, 0), Z),
    skirt=((2, 0, 0), Z),
    footL=dict(d=(1.5, 0, -6.5), yaw=14), footR=dict(d=(-0.5, 0, 7.0), yaw=-22),
    sword=((15.5, 36.5, -17.0), norm((-0.08, -0.36, -0.93)), None, 'sword', 0.0),
    handL=dict(off=((3.0, 6.0, -8.0), (-28, 0, -12))),
)
def cs_fk(n, t, ease='smooth', d=Z, p=Z):
    r, ps = CS[n]; return (t, L.add3(r, d), L.add3(ps, p), ease)
REST_FEET = dict(d=Z)

def stance_feet(t, ease='smooth'):
    return [(t, CS['footL'], ease)], [(t, CS['footR'], ease)]

# ================================================================= 1. idle (6s loop) - planted sword, watching
if want('idle'):
    begin('idle', 6.0, 'loop')
    # two uneven breaths: a short one, then a deeper one with a held top and a slow, hitching exhale
    fk('body', [(0, (0, 0, 0), (0, 0, 0)), (1.6, (0, -0.5, 0.4), (0.5, -0.15, 0)), (2.6, (0, -0.8, 0.5), (0.7, -0.2, 0)),
                (4.4, (0, 0.3, -0.3), (-0.3, 0.05, 0)), (5.4, (0, 0.2, -0.2), (-0.2, 0, 0)), (6.0, Z, Z)])
    fk('waist', [(0, Z), (1.3, (0.5, 0, 0)), (2.8, (-0.2, 0, 0)), (4.2, (0.9, 0, 0)), (4.7, (0.8, 0, 0)), (6.0, Z)])
    fk('chest', [(0, Z, Z), (1.25, (1.6, 0.4, 0), (0, 0.35, 0.1)), (2.9, (-0.3, 0, 0), (0, -0.05, 0)), (3.3, (-0.3, 0, 0), (0, -0.05, 0)),
                 (4.35, (2.5, -0.4, 0), (0, 0.55, 0.15)), (4.75, (2.3, -0.4, 0), (0, 0.5, 0.15)), (5.2, (1.4, -0.2, 0), (0, 0.3, 0.1)),
                 (5.35, (1.5, -0.2, 0), (0, 0.32, 0.1)), (6.0, Z, Z)])
    # head: turns to watch (his right), holds dead still, cocks a slow tilt, then drifts back
    fk('head', [(0, (-2, 0, 0)), (0.7, (-2, 0, 0)), (1.7, (-3, -9, -1), None, 'out'), (3.1, (-3, -9.5, -1)),
                (3.7, (-1, -8, 5), None, 'inout'), (4.6, (-1.5, -8, 4.5)), (5.4, (-2.5, -1, 0), None, 'inout'), (6.0, (-2, 0, 0))])
    fk('jaw', [(0, (1, 0, 0)), (1.3, (3, 0, 0)), (2.6, (1, 0, 0)), (4.4, (4.5, 0, 0)), (5.0, (2, 0, 0)), (6.0, (1, 0, 0))])
    fk('skirt', [(0, Z), (2.6, (0, 0, -1.2)), (4.6, (0.5, 0, 0.8)), (6.0, Z)])
    feet('L', [(0, REST_FEET, 'smooth'), (6.0, REST_FEET, 'smooth')]); feet('R', [(0, REST_FEET, 'smooth'), (6.0, REST_FEET, 'smooth')])
    # right hand stays locked on the planted sword (world space) - the arm absorbs the breathing
    hands('R', [(0, {'off': (Z, Z)}, 'smooth'), (6.0, {'off': (Z, Z)}, 'smooth')])
    # left claw: slow curl, a sudden twitch at 4.9s, then relax
    hands('L', [(0, {'off': (Z, Z), 'space': 'chest'}, 'smooth'), (2.0, {'off': ((0, 0.2, 0), (0, 0, 7)), 'space': 'chest'}, 'smooth'),
                (3.6, {'off': ((0, 0.1, 0), (0, 0, 5)), 'space': 'chest'}, 'smooth'),
                (4.85, {'off': ((0, 0.1, 0), (0, 0, 4)), 'space': 'chest'}, 'in'), (4.95, {'off': ((0.3, 0.4, -0.3), (-6, 0, 14)), 'space': 'chest'}, 'out'),
                (5.4, {'off': ((0.1, 0.2, 0), (-2, 0, 6)), 'space': 'chest'}, 'smooth'), (6.0, {'off': (Z, Z), 'space': 'chest'}, 'smooth')])
    finish()

# ================================================================= 2. idle_combat (3.2s loop)
if want('idle_combat'):
    begin('idle_combat', 3.2, 'loop')
    fk('body', [cs_fk('body', 0), cs_fk('body', 0.8, p=(0.15, -0.35, -0.2)), cs_fk('body', 1.6, d=(0, 1.0, 0)), cs_fk('body', 2.4, p=(-0.1, -0.45, 0.2)), cs_fk('body', 3.2)])
    fk('waist', [cs_fk('waist', 0), cs_fk('waist', 1.6, d=(0.6, 0, 0)), cs_fk('waist', 3.2)])
    fk('chest', [cs_fk('chest', 0), cs_fk('chest', 0.7, d=(2.0, -1.0, 0), p=(0, 0.4, 0)), cs_fk('chest', 1.55, d=(-0.4, 0, 0)),
                 cs_fk('chest', 2.35, d=(2.4, 1.0, 0.5), p=(0, 0.45, 0)), cs_fk('chest', 3.2)])
    fk('head', [cs_fk('head', 0), cs_fk('head', 0.9, d=(-1.5, 2.5, -1)), cs_fk('head', 1.3, d=(-1.5, 2.6, -1)), cs_fk('head', 2.2, d=(0.5, -2.0, 1.5)), cs_fk('head', 3.2)])
    fk('jaw', [cs_fk('jaw', 0), cs_fk('jaw', 0.7, d=(3, 0, 0)), cs_fk('jaw', 1.4, d=(0, 0, 0)), cs_fk('jaw', 2.35, d=(3.5, 0, 0)), cs_fk('jaw', 3.2)])
    fk('skirt', [cs_fk('skirt', 0), cs_fk('skirt', 1.6, d=(1, 0, 0.6)), cs_fk('skirt', 3.2)])
    fl, fr = stance_feet(0); feet('L', fl + [(3.2, CS['footL'], 'smooth')]); feet('R', fr + [(3.2, CS['footR'], 'smooth')])
    g, b, f, m, tl = CS['sword']
    def tipcirc(a, k=1.0):     # the point traces a slow, small, menacing circle
        bb = Vector(b) + Vector((0.05 * cos(a), 0.05 * sin(a), 0)) * k
        return (L.add3(g, (0.4 * sin(a) * k, 0.3 * cos(a) * k, 0)), tuple(bb.normalized()), f, m, tl)
    hands('R', [(t, {'sword': tipcirc(2 * pi * t / 3.2), 'space': 'chest'}, 'smooth') for t in [0, 0.8, 1.6, 2.4, 3.2]])
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (1.1, {'off': ((3.0, 6.3, -8.4), (-31, 0, -18)), 'space': 'chest'}, 'smooth'),
                (2.1, {'off': ((3.2, 5.8, -7.8), (-25, 0, -8)), 'space': 'chest'}, 'smooth'), (3.2, dict(CS['handL'], space='chest'), 'smooth')])
    finish()

# ================================================================= 3. walk (2.4s loop, 14 px/s = 0.20 speed attribute)
if want('walk'):
    T = 2.4; V = 14.0; ST = 0.62; STRIDE = V * T; ZC = -10.4
    begin('walk', T, 'loop')
    def smoother(u): return u * u * u * (u * (u * 6 - 15) + 10)
    def hermite(p0, p1, m0, m1, u):
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1
    def foot_at(ph, side):
        ph %= 1.0; x = -1.6 if side == 'R' else 1.6; yaw = -7 if side == 'R' else 7
        if ph < ST:
            z = ZC + STRIDE * ph
            if ph < 0.09: pit = 15 * (1 - smoother(ph / 0.09))                # heel strike, foot slaps down
            elif ph < 0.45: pit = 0
            else: pit = -30 * smoother((ph - 0.45) / (ST - 0.45))          # heel peels up, rolling over the toes
            return dict(d=(x, 0, z), yaw=yaw, pitch=pit, pivot='heel' if pit > 0 else 'toe')
        u = (ph - ST) / (1 - ST)
        z = hermite(ZC + STRIDE * ST, ZC, 4.0, 6.0, u)
        y = 6.0 * math.sin(pi * min(1.0, u ** 0.7)) ** 1.1
        pit = -30 + 45 * smoother(min(1.0, u / 0.92))
        return dict(d=(x, y, z), yaw=yaw, pitch=pit, pivot='heel' if pit > 0 else 'toe')
    N = 48
    feet('R', [(T * k / N, foot_at(k / N, 'R'), 'linear') for k in range(N + 1)])
    feet('L', [(T * k / N, foot_at(k / N + 0.5, 'L'), 'linear') for k in range(N + 1)])
    # torso from the gait phase of the right foot (0 = right heel strike)
    def torso(ph):
        s = ph % 0.5 / 0.5                                                      # step phase (each heel strike = 0)
        dip = -0.55 * math.exp(-((s - 0.1) / 0.07) ** 2)                        # weight loading just after contact
        bob = 0.45 * -cos(2 * pi * s) + dip
        sway = 1.25 * sin(2 * pi * ph - 0.25)
        return dict(body=((-3.5 + 1.2 * dip, 4.5 * cos(2 * pi * ph), 2.0 * sin(2 * pi * ph - 0.3)), (sway, -2.2 + bob, 0)),
                    waist=((-2 + 0.6 * dip, -1.5 * cos(2 * pi * ph - 0.2), -0.6 * sin(2 * pi * ph)), Z),
                    chest=((-2 + 2.4 * dip, -6.0 * cos(2 * pi * ph - 0.35), -2.4 * sin(2 * pi * ph - 0.4)), Z),
                    head=((-5 + 2.0 * dip, 5.5 * cos(2 * pi * ph - 0.5), 2.0 * sin(2 * pi * ph - 0.5)), Z),
                    jaw=((2 - 6 * dip, 0, 0), Z),
                    skirt=((2 + 1.6 * dip, 0, 3.0 * sin(2 * pi * ph - 0.9)), Z))
    M = 24
    for n in ('body', 'waist', 'chest', 'head', 'jaw', 'skirt'):
        fk(n, [(T * k / M, *torso(k / M)[n], 'smooth') for k in range(M + 1)])
    # greatsword rides on his right shoulder (follows the chest) and kicks on every heel strike
    CARRY = ((12.5, 56.0, -9.0), norm((0.12, 0.42, 0.9)), None, 'sword', 0.0)
    def carry(ph):
        s = ph % 0.5 / 0.5; kick = 0.9 * math.exp(-((s - 0.16) / 0.1) ** 2)
        g, b, f, m, tl = CARRY
        bb = (Vector(b) + Vector((0, -0.06 * kick, 0))).normalized()
        return {'sword': (L.add3(g, (0, -kick, 0.2 * kick)), tuple(bb), f, m, tl), 'space': 'chest'}
    hands('R', [(T * k / M, carry(k / M), 'smooth') for k in range(M + 1)])
    # left arm swings against the left leg, a beat behind the body
    def swing(ph):
        a = cos(2 * pi * (ph - 0.07))
        return {'off': ((0.5 * a, 1.0 * (1 - a * a) * 0.5 + 0.6, -4.5 * a), (-12 * a, 0, -4 - 3 * abs(a))), 'space': 'chest'}
    hands('L', [(T * k / M, swing(k / M), 'smooth') for k in range(M + 1)])
    finish()

# ================================================================= 4. sweep (2.8s) - hit at 1.30s
if want('sweep'):
    begin('sweep', 2.8, 'once')
    C = Vector((2.0, 45.0, 0.0))
    def sw(a, e, rg, h, lead=0.0, roll=0.0):
        """sword around him: grip on a circle of radius rg at height h, angle a; blade at angle a+lead, elevation e."""
        ar = math.radians(a); g = (C.x + rg * sin(ar), h, C.z - rg * cos(ar))
        bd = blade_dir(a + lead, e)
        return (g, bd, None, 'sword', 0.0)
    # body: settle - coil back onto the right leg - hips fire first, chest follows, arm last - follow through - recover
    fk('body', [cs_fk('body', 0), cs_fk('body', 0.25, d=(0.5, 0, 0)), cs_fk('body', 0.95, d=(2, -12, 1), p=(1.6, -0.8, 1.6), ease='inout'),
                cs_fk('body', 1.12, d=(2, -14, 1), p=(1.8, -1.0, 1.8), ease='in'), cs_fk('body', 1.28, d=(-2, 10, -2), p=(-1.0, -1.8, -1.6), ease='out'),
                cs_fk('body', 1.5, d=(-3, 14, -3), p=(-1.6, -2.2, -2.0), ease='smooth'), cs_fk('body', 1.85, d=(-2, 11, -2), p=(-1.2, -1.8, -1.6)),
                cs_fk('body', 2.45, d=(0.5, -1.5, 0), p=(0.1, 0.15, 0.1), ease='inout'), cs_fk('body', 2.8)])
    fk('waist', [cs_fk('waist', 0), cs_fk('waist', 1.0, d=(1, -12, 0), ease='inout'), cs_fk('waist', 1.14, d=(1, -14, 0), ease='in'),
                 cs_fk('waist', 1.31, d=(-1, 8, 0), ease='out'), cs_fk('waist', 1.55, d=(-1, 10, 0)), cs_fk('waist', 1.9, d=(-1, 7, 0)),
                 cs_fk('waist', 2.5, d=(0, -1, 0), ease='inout'), cs_fk('waist', 2.8)])
    fk('chest', [cs_fk('chest', 0), cs_fk('chest', 0.3, d=(1.5, 0, 0)), cs_fk('chest', 1.02, d=(5, -20, -4), ease='inout'),
                 cs_fk('chest', 1.16, d=(5, -23, -5), ease='in'), cs_fk('chest', 1.34, d=(-3, 16, 4), ease='out'),
                 cs_fk('chest', 1.6, d=(-4, 20, 5)), cs_fk('chest', 1.95, d=(-3, 13, 3)), cs_fk('chest', 2.55, d=(0.5, -2, 0), ease='inout'), cs_fk('chest', 2.8)])
    # head keeps his eyes on the victim: counter-turns against the twist, snaps late
    fk('head', [cs_fk('head', 0), cs_fk('head', 1.05, d=(-4, 34, 3), ease='inout'), cs_fk('head', 1.2, d=(-5, 38, 3), ease='in'),
                cs_fk('head', 1.4, d=(-3, -22, -3), ease='out'), cs_fk('head', 1.75, d=(-2, -30, -3)), cs_fk('head', 2.1, d=(-2, -20, -2)),
                cs_fk('head', 2.6, d=(0, 2, 0), ease='inout'), cs_fk('head', 2.8)])
    fk('jaw', [cs_fk('jaw', 0), cs_fk('jaw', 1.0, d=(-2, 0, 0)), cs_fk('jaw', 1.2, d=(-2, 0, 0), ease='in'), cs_fk('jaw', 1.35, d=(22, 0, 0), ease='out'),
               cs_fk('jaw', 1.7, d=(14, 0, 0)), cs_fk('jaw', 2.3, d=(3, 0, 0)), cs_fk('jaw', 2.8)])
    fk('skirt', [cs_fk('skirt', 0), cs_fk('skirt', 1.0, d=(0, 0, 4)), cs_fk('skirt', 1.4, d=(-2, 0, 2)), cs_fk('skirt', 1.7, d=(1, 0, -6)),
                 cs_fk('skirt', 2.2, d=(0, 0, 2)), cs_fk('skirt', 2.8)])
    # feet: planted; the back (right) foot pivots on the ball as the hips come through
    feet('L', [(0, CS['footL'], 'smooth'), (2.8, CS['footL'], 'smooth')])
    fR = CS['footR']
    feet('R', [(0, fR, 'smooth'), (1.15, fR, 'in'), (1.4, dict(fR, yaw=fR['yaw'] + 22, pitch=-16, pivot='toe'), 'out'),
               (1.8, dict(fR, yaw=fR['yaw'] + 26, pitch=-18, pivot='toe'), 'smooth'), (2.35, dict(fR, yaw=fR['yaw'] + 4, pitch=-2, pivot='toe'), 'inout'), (2.8, fR, 'smooth')])
    # the blade: drawn back high over the right shoulder, then a flat arc through the front; blade trails the grip on the
    # way in (weight), whips past it after contact, and overshoots round to his left
    S = [(0, CS['sword'], 'smooth')]
    S += [(0.45, sw(70, 5, 18, 44, -8), 'smooth'), (0.95, sw(128, 30, 15, 58, -14), 'inout'), (1.12, sw(133, 33, 15, 59.5, -16), 'in')]
    for k, (t, a, e, lead) in enumerate([(1.17, 112, 18, 18), (1.21, 78, 4, 20), (1.25, 45, -4, 14), (1.29, 8, -8, 4), (1.33, -30, -10, -10),
                                          (1.38, -60, -12, -12), (1.45, -82, -14, -10), (1.55, -96, -16, -6)]):
        S.append((t, sw(a, e, 19 if abs(a) < 60 else 17, 40 + 0.06 * abs(a), lead), 'linear'))
    S += [(1.75, sw(-104, -24, 16, 38, -4), 'smooth'), (2.1, sw(-84, -30, 15, 37, -2), 'inout'), (2.55, sw(-10, -28, 17, 36, 0), 'inout'), (2.8, CS['sword'], 'smooth')]
    hands('R', [(t, {'sword': s}, e) for t, s, e in S])
    # off hand: reaches out toward the victim to aim the coil, then is flung back behind him by the swing
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'),
                (0.95, {'off': ((2.0, 16.0, -14.0), (-62, 0, -18)), 'space': 'chest'}, 'inout'),
                (1.12, {'off': ((2.0, 16.5, -14.5), (-64, 0, -18)), 'space': 'chest'}, 'in'),
                (1.38, {'off': ((-5.0, 8.0, 8.0), (30, 0, -26)), 'space': 'chest'}, 'out'),
                (1.8, {'off': ((-4.0, 5.0, 7.0), (26, 0, -20)), 'space': 'chest'}, 'smooth'),
                (2.8, dict(CS['handL'], space='chest'), 'smooth')])
    finish()

# ================================================================= 5. summon_start (2.2s, hold) - impact 1.80s
KNEEL = dict(body=((-6, -2, 0), (0.4, -12.2, -1.0)), waist=((-6, 0, 0), Z), chest=((-12, 0, 0), Z), head=((-10, 0, 0), Z),
             footL=dict(d=(2.0, 0, -9.0), yaw=6), footR=dict(d=(-1.5, 2.6, 13.0), yaw=-6, pitch=-62, pivot='toe'))
PLUNGE_R = ((6.0, 30.0, -21.0), (0, -1, -0.05), None, 'cane', 0.0)
PLUNGE_L = ((3.4, 34.6, -21.2), norm((0, 0.05, -1)), (1, 0, 0))
if want('summon_start'):
    begin('summon_start', 2.2, 'hold')
    fk('body', [cs_fk('body', 0), (0.4, (-1, -2, 0), (0.2, -1.0, 0.3), 'inout'), (1.15, (2, 0, 0), (0, 0.2, 0.6), 'inout'), (1.55, (2.5, 0, 0), (0, 0.4, 0.7), 'in'),
                (1.8, (-7, -2, 0), (0.4, -13.0, -1.2), 'out'), (1.95, (-6.5, -2, 0), (0.4, -11.9, -1.0), 'smooth'), (2.2, (*KNEEL['body'][0],), KNEEL['body'][1], 'smooth')])
    fk('waist', [cs_fk('waist', 0), (1.15, (3, 0, 0), Z, 'inout'), (1.55, (4, 0, 0), Z, 'in'), (1.8, (-8, 0, 0), Z, 'out'), (2.2, KNEEL['waist'][0], Z)])
    fk('chest', [cs_fk('chest', 0), (0.5, (-2, 0, 0), Z, 'inout'), (1.2, (9, 0, 0), (0, 0.5, 0), 'inout'), (1.55, (10, 0, 0), (0, 0.6, 0), 'in'),
                 (1.82, (-16, 0, 0), Z, 'out'), (2.0, (-11, 0, 0), Z), (2.2, KNEEL['chest'][0], Z)])
    fk('head', [cs_fk('head', 0), (0.6, (6, 0, 0), Z, 'inout'), (1.25, (14, 0, 0), Z), (1.55, (15, 0, 1), Z, 'in'), (1.84, (-18, 0, 0), Z, 'out'),
                (2.02, (-7, 0, 0), Z), (2.2, KNEEL['head'][0], Z)])
    fk('jaw', [cs_fk('jaw', 0), (1.0, (6, 0, 0), Z), (1.5, (14, 0, 0), Z, 'in'), (1.8, (26, 0, 0), Z, 'out'), (2.2, (12, 0, 0), Z)])
    fk('skirt', [cs_fk('skirt', 0), (1.2, (-2, 0, 0), Z), (1.8, (14, 0, 0), Z, 'out'), (2.2, (10, 0, 0), Z)])
    feet('L', [(0, CS['footL'], 'smooth'), (1.5, CS['footL'], 'in'), (1.62, dict(d=(2.0, 3.5, -8.0), yaw=6, pitch=6), 'out'),
               (1.78, KNEEL['footL'], 'smooth'), (2.2, KNEEL['footL'], 'smooth')])
    feet('R', [(0, CS['footR'], 'smooth'), (1.52, CS['footR'], 'out'), (1.6, dict(CS['footR'], d=L.add3(CS['footR']['d'], (0, 2.5, 0.5))), 'smooth'),
               (1.7, dict(d=(-1.0, 3.6, 11), yaw=-10, pitch=-40, pivot='toe'), 'out'), (1.8, KNEEL['footR'], 'smooth'), (2.2, KNEEL['footR'], 'smooth')])
    pole('POLE_knee.R', [(0, (8.14, 19.12, -33.86), 'smooth'), (1.55, (8.14, 19.12, -33.86), 'in'), (1.8, (8, 6, -32), 'smooth'), (2.2, (8, 6, -32), 'smooth')])
    # raise two-handed overhead, flipping the blade point-down on the way up; tremble; drive it into the ground
    RAISE = ((5.5, 70.0, -15.5), (0, -1, -0.1), None, 'cane', 0.0)
    hands('R', [(0, {'sword': CS['sword']}, 'smooth'), (0.45, {'sword': ((14, 46, -18), norm((0.2, 0.5, -0.8)), None, 'sword', 0.0)}, 'inout'),
                (0.85, {'sword': ((10, 62, -17), norm((0.1, 0.2, -1)), None, 'cane', 0.0)}, 'inout'),
                (1.2, {'sword': RAISE}, 'smooth'), (1.3, {'sword': ((5.6, 70.3, -15.4), (0, -1, -0.1), None, 'cane')}, 'linear'),
                (1.4, {'sword': ((5.4, 69.9, -15.6), (0, -1, -0.1), None, 'cane')}, 'linear'), (1.5, {'sword': ((5.6, 70.6, -15.5), (0, -1, -0.1), None, 'cane')}, 'in'),
                (1.8, {'sword': PLUNGE_R}, 'out'), (2.2, {'sword': PLUNGE_R}, 'smooth')])
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (0.6, {'off': ((6, 14, -10), (-40, 0, -20)), 'space': 'chest'}, 'inout'),
                (1.2, {'palm': ((3.0, 74.5, -15.6), norm((0, 0.05, -1)), (1, 0, 0))}, 'smooth'),
                (1.5, {'palm': ((3.1, 74.8, -15.6), norm((0, 0.05, -1)), (1, 0, 0))}, 'in'), (1.8, {'palm': PLUNGE_L}, 'out'), (2.2, {'palm': PLUNGE_L}, 'smooth')])
    finish()

# ================================================================= 6. summon_loop (3.0s loop) - knelt over the sword, chanting
if want('summon_loop'):
    begin('summon_loop', 3.0, 'loop')
    kb = KNEEL['body']
    fk('body', [(0, kb[0], kb[1]), (1.0, L.add3(kb[0], (0.8, 0, 0)), L.add3(kb[1], (0, 0.35, 0))), (2.1, L.add3(kb[0], (-0.4, 0, 0)), L.add3(kb[1], (0, -0.2, 0))), (3.0, kb[0], kb[1])])
    fk('waist', [(0, KNEEL['waist'][0]), (1.5, L.add3(KNEEL['waist'][0], (1, 0, 0))), (3.0, KNEEL['waist'][0])])
    fk('chest', [(0, KNEEL['chest'][0]), (0.9, L.add3(KNEEL['chest'][0], (3.0, 1.5, 0)), (0, 0.5, 0)), (1.6, L.add3(KNEEL['chest'][0], (1.0, 0, 0))),
                 (2.3, L.add3(KNEEL['chest'][0], (2.4, -1.5, 0)), (0, 0.35, 0)), (3.0, KNEEL['chest'][0])])
    fk('head', [(0, KNEEL['head'][0]), (0.75, (-14, 5, -4)), (1.5, (-8, 0, 0)), (2.25, (-14, -5, 4)), (3.0, KNEEL['head'][0])])
    fk('jaw', [(0, (12, 0, 0)), (0.35, (18, 0, 0)), (0.6, (10, 0, 0)), (1.05, (20, 0, 0)), (1.5, (11, 0, 0)), (2.0, (16, 0, 0)), (2.4, (22, 0, 0)), (3.0, (12, 0, 0))])
    fk('skirt', [(0, (10, 0, 0)), (1.5, (11, 0, 1)), (3.0, (10, 0, 0))])
    feet('L', [(0, KNEEL['footL'], 'smooth'), (3.0, KNEEL['footL'], 'smooth')]); feet('R', [(0, KNEEL['footR'], 'smooth'), (3.0, KNEEL['footR'], 'smooth')])
    pole('POLE_knee.R', [(0, (8, 6, -32), 'smooth'), (3.0, (8, 6, -32), 'smooth')])
    hands('R', [(0, {'sword': PLUNGE_R}, 'smooth'), (3.0, {'sword': PLUNGE_R}, 'smooth')])
    hands('L', [(0, {'palm': PLUNGE_L}, 'smooth'), (3.0, {'palm': PLUNGE_L}, 'smooth')])
    finish()

# ================================================================= 7. summon_end (1.8s) - wrench the blade free and rise
if want('summon_end'):
    begin('summon_end', 1.8, 'once')
    kb = KNEEL['body']
    fk('body', [(0, kb[0], kb[1]), (0.35, L.add3(kb[0], (-3, 0, 0)), L.add3(kb[1], (0, -0.6, -0.5)), 'inout'), (0.55, L.add3(kb[0], (-2, 0, 0)), L.add3(kb[1], (0, -0.3, -0.4)), 'in'),
                (0.95, (-2, -4, 0), (0.4, -4.5, 0.2), 'out'), (1.3, cs_fk('body', 0)[1], L.add3(CS['body'][1], (0, -0.9, 0)), 'smooth'), cs_fk('body', 1.8)])
    fk('waist', [(0, KNEEL['waist'][0]), (0.45, (-9, 0, 0), Z, 'in'), (0.95, (2, 0, 0), Z, 'out'), cs_fk('waist', 1.8)])
    fk('chest', [(0, KNEEL['chest'][0]), (0.4, (-18, 0, 0), Z, 'inout'), (0.6, (-12, 0, 0), (0, 0.6, 0), 'in'), (0.95, (6, 4, 0), Z, 'out'),
                 (1.25, cs_fk('chest', 0)[1], Z), cs_fk('chest', 1.8)])
    fk('head', [(0, KNEEL['head'][0]), (0.45, (-16, 0, 0)), (0.62, (-10, 0, 0), None, 'in'), (1.0, (8, 0, 0), None, 'out'), cs_fk('head', 1.8)])
    fk('jaw', [(0, (12, 0, 0)), (0.55, (2, 0, 0)), (0.85, (24, 0, 0)), (1.3, (6, 0, 0)), cs_fk('jaw', 1.8)])
    fk('skirt', [(0, (10, 0, 0)), (0.9, (-4, 0, 0)), (1.3, (4, 0, 0)), cs_fk('skirt', 1.8)])
    feet('L', [(0, KNEEL['footL'], 'smooth'), (0.6, KNEEL['footL'], 'smooth'), (1.0, CS['footL'], 'smooth'), (1.8, CS['footL'], 'smooth')])
    feet('R', [(0, KNEEL['footR'], 'smooth'), (0.6, KNEEL['footR'], 'in'), (0.8, dict(d=(-0.8, 4.0, 10.0), yaw=-16, pitch=-30, pivot='toe'), 'out'),
               (0.94, dict(CS['footR'], d=L.add3(CS['footR']['d'], (0, 2.0, 0.5))), 'smooth'), (1.05, CS['footR'], 'smooth'), (1.8, CS['footR'], 'smooth')])
    pole('POLE_knee.R', [(0, (8, 6, -32), 'smooth'), (0.6, (8, 6, -32), 'smooth'), (1.0, (8.14, 19.12, -33.86), 'smooth'), (1.8, (8.14, 19.12, -33.86), 'smooth')])
    hands('R', [(0, {'sword': PLUNGE_R}, 'smooth'), (0.55, {'sword': PLUNGE_R}, 'in'), (0.62, {'sword': ((6.0, 30.4, -21.0), (0, -1, -0.05), None, 'cane')}, 'out'),
                (0.95, {'sword': ((10, 42, -20), norm((0.1, -0.9, -0.3)), None, 'cane')}, 'smooth'),
                (1.25, {'sword': ((16, 40, -19), norm((0.0, -0.3, -0.95)), None, 'sword', 0.0)}, 'out'),
                (1.4, {'sword': ((15.5, 35.0, -17.4), norm((-0.08, -0.48, -0.87)), None, 'sword', 0.0)}, 'smooth'), (1.8, {'sword': CS['sword']}, 'smooth')])
    hands('L', [(0, {'palm': PLUNGE_L}, 'smooth'), (0.55, {'palm': PLUNGE_L}, 'in'), (0.62, {'palm': ((3.4, 35.0, -21.2), norm((0, 0.05, -1)), (1, 0, 0))}, 'out'),
                (0.95, {'off': ((10, 6, -10), (-30, 0, -10)), 'space': 'chest'}, 'smooth'), (1.8, dict(CS['handL'], space='chest'), 'smooth')])
    finish()

# ================================================================= 8. push (2.0s) - blast at 1.00s
if want('push'):
    begin('push', 2.0, 'once')
    fk('body', [cs_fk('body', 0), cs_fk('body', 0.55, d=(3, -12, 0), p=(0.8, -0.3, 2.0), ease='inout'), cs_fk('body', 0.78, d=(3, -13, 0), p=(0.9, -0.4, 2.2), ease='in'),
                cs_fk('body', 1.0, d=(-6, 14, 0), p=(-0.6, -1.6, -4.0), ease='out'), cs_fk('body', 1.2, d=(-7, 16, 0), p=(-0.7, -1.9, -4.6)),
                cs_fk('body', 1.65, d=(-1, 3, 0), p=(-0.2, -0.4, -1.0), ease='inout'), cs_fk('body', 2.0)])
    fk('waist', [cs_fk('waist', 0), cs_fk('waist', 0.6, d=(1, -6, 0), ease='inout'), cs_fk('waist', 0.8, d=(1, -7, 0), ease='in'), cs_fk('waist', 1.03, d=(-4, 7, 0), ease='out'),
                 cs_fk('waist', 1.25, d=(-5, 8, 0)), cs_fk('waist', 2.0)])
    fk('chest', [cs_fk('chest', 0), cs_fk('chest', 0.62, d=(4, -16, 0), ease='inout'), cs_fk('chest', 0.82, d=(5, -17, 0), ease='in'),
                 cs_fk('chest', 1.05, d=(-10, 18, 0), ease='out'), cs_fk('chest', 1.28, d=(-12, 20, 0)), cs_fk('chest', 1.75, d=(-2, 4, 0), ease='inout'), cs_fk('chest', 2.0)])
    fk('head', [cs_fk('head', 0), cs_fk('head', 0.6, d=(-6, 22, 0), ease='inout'), cs_fk('head', 0.84, d=(-7, 24, 0), ease='in'), cs_fk('head', 1.08, d=(-4, -24, 0), ease='out'),
                cs_fk('head', 1.35, d=(-3, -26, 0)), cs_fk('head', 1.8, d=(0, -4, 0), ease='inout'), cs_fk('head', 2.0)])
    fk('jaw', [cs_fk('jaw', 0), cs_fk('jaw', 0.8, d=(4, 0, 0)), cs_fk('jaw', 1.02, d=(30, 0, 0), ease='out'), cs_fk('jaw', 1.4, d=(20, 0, 0)), cs_fk('jaw', 2.0)])
    fk('skirt', [cs_fk('skirt', 0), cs_fk('skirt', 0.7, d=(4, 0, 0)), cs_fk('skirt', 1.05, d=(-6, 0, 0), ease='out'), cs_fk('skirt', 1.35, d=(4, 0, 0)), cs_fk('skirt', 2.0)])
    fL = CS['footL']; fLf = dict(fL, d=L.add3(fL['d'], (0.5, 0, -5.5)))
    feet('L', [(0, fL, 'smooth'), (0.7, fL, 'in'), (0.82, dict(fL, d=L.add3(fL['d'], (0.4, 3.0, -3.0)), pitch=6), 'out'), (0.97, fLf, 'smooth'), (1.4, fLf, 'in'),
               (1.55, dict(fL, d=L.add3(fL['d'], (0.3, 2.2, -2.5)), pitch=4), 'out'), (1.72, fL, 'smooth'), (2.0, fL, 'smooth')])
    feet('R', [(0, CS['footR'], 'smooth'), (2.0, CS['footR'], 'smooth')])
    g, b, f, m, tl = CS['sword']
    hands('R', [(0, {'sword': CS['sword']}, 'smooth'), (0.6, {'sword': (L.add3(g, (2.5, 1.5, 6)), norm((0.08, -0.3, -0.95)), f, m, tl)}, 'inout'),
                (1.05, {'sword': (L.add3(g, (2, 0.5, 3)), norm((0.12, -0.22, -0.97)), f, m, tl)}, 'out'),
                (1.4, {'sword': (L.add3(g, (1.5, 0, 2.5)), norm((0.08, -0.28, -0.96)), f, m, tl)}, 'smooth'), (2.0, {'sword': CS['sword']}, 'smooth')])
    PUP = norm((0.05, 1, 0.1)); PFW = (0, 0, -1)
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (0.62, {'palm': ((-18, 51, 3), PUP, PFW)}, 'inout'), (0.8, {'palm': ((-18, 51.5, 4), PUP, PFW)}, 'in'),
                (1.0, {'palm': ((-11, 50, -32), PUP, PFW)}, 'out'), (1.22, {'palm': ((-10.5, 50.5, -34), PUP, PFW)}, 'smooth'),
                (1.42, {'palm': ((-15, 45, -22), norm((0.0, 0.3, -0.95)), norm((0.45, 0.2, -0.85)))}, 'inout'),
                (1.65, {'off': ((3, 9, -10), (-40, 0, -16)), 'space': 'chest'}, 'inout'), (2.0, dict(CS['handL'], space='chest'), 'smooth')])
    pole('POLE_elbow.L', [(0, (-16.57, 37.56, 28.6), 'smooth'), (0.6, (-30, 30, 10), 'smooth'), (1.0, (-30, 34, 0), 'smooth'), (1.6, (-16.57, 37.56, 28.6), 'smooth')])
    finish()

# ================================================================= 9. awaken (3.6s) - phase two; flash at 2.20s
SLUMP = dict(body=((-4, 0, 0), (0.6, -5.0, 0.6)), waist=((-8, 0, 0), Z), chest=((-20, 0, 2), Z), head=((-26, 2, 4), Z), jaw=((10, 0, 0), Z))
PLANT_R = ((16.5, 37.0, -15.0), (0, -1, 0.02), None, 'cane', 0.0)
if want('awaken'):
    begin('awaken', 3.6, 'once')
    fk('body', [cs_fk('body', 0), (0.38, SLUMP['body'][0], L.add3(SLUMP['body'][1], (0, -0.6, 0)), 'out'), (0.55, *SLUMP['body'], 'smooth'), (1.3, *SLUMP['body'], 'inout'),
                (2.0, (-2, 0, 0), (0.3, -3.2, 0.4), 'in'), (2.22, (2, 0, 0), (0, 0.4, 0.8), 'out'), (2.9, (1.5, 0, 0), (0, 0.2, 0.7), 'inout'),
                (3.35, CS['body'][0], L.add3(CS['body'][1], (0, -0.5, 0)), 'smooth'), cs_fk('body', 3.6)])
    fk('waist', [cs_fk('waist', 0), (0.4, SLUMP['waist'][0], Z, 'out'), (1.35, SLUMP['waist'][0], Z, 'inout'), (2.0, (-3, 0, 0), Z, 'in'), (2.22, (6, 0, 0), Z, 'out'),
                 (2.9, (5, 0, 0), Z, 'inout'), cs_fk('waist', 3.6)])
    fk('chest', [cs_fk('chest', 0), (0.42, (-23, 0, 3), Z, 'out'), (0.6, SLUMP['chest'][0], Z), (1.35, SLUMP['chest'][0], Z, 'inout'), (1.6, (-17, 0, 1), (0, 0.3, 0)),
                 (2.02, (-8, 0, 0), (0, 0.6, 0), 'in'), (2.25, (18, 0, 0), (0, 1.0, 0), 'out'), (2.6, (16, 0, 0), (0, 0.9, 0)), (2.9, (15, 0, 0), (0, 0.8, 0), 'inout'),
                 (3.4, CS['chest'][0], Z), cs_fk('chest', 3.6)])
    fk('head', [cs_fk('head', 0), (0.45, (-30, 3, 5), Z, 'out'), (0.65, SLUMP['head'][0], Z), (0.9, (-25.5, 2, 3.5)), (1.45, SLUMP['head'][0], Z, 'inout'),
                (2.05, (6, 0, 0), Z, 'in'), (2.28, (28, 0, 0), Z, 'out'), (2.4, (27, 2, -3), Z, 'linear'), (2.5, (29, -2, 3), Z, 'linear'), (2.6, (27, 2, -3), Z, 'linear'),
                (2.7, (29, -1, 2), Z, 'linear'), (2.85, (26, 0, 0), Z, 'inout'), (3.45, CS['head'][0], Z), cs_fk('head', 3.6)])
    fk('jaw', [cs_fk('jaw', 0), (0.5, SLUMP['jaw'][0], Z), (1.4, SLUMP['jaw'][0], Z), (2.0, (2, 0, 0), Z, 'in'), (2.24, (36, 0, 0), Z, 'out'), (2.85, (32, 0, 0), Z, 'inout'),
               (3.3, (6, 0, 0), Z), cs_fk('jaw', 3.6)])
    fk('skirt', [cs_fk('skirt', 0), (0.5, (4, 0, 0)), (2.0, (2, 0, 0)), (2.3, (-10, 0, 0), None, 'out'), (2.8, (-4, 0, 0)), cs_fk('skirt', 3.6)])
    feet('L', [(0, CS['footL'], 'smooth'), (3.6, CS['footL'], 'smooth')]); feet('R', [(0, CS['footR'], 'smooth'), (3.6, CS['footR'], 'smooth')])
    # he flips the sword point-down and leans on it as he slumps; wrenches it up into guard at the end
    hands('R', [(0, {'sword': CS['sword']}, 'smooth'), (0.2, {'sword': ((17, 38, -17), norm((0.1, -0.7, -0.7)), None, 'sword', 0.0)}, 'smooth'),
                (0.38, {'sword': PLANT_R}, 'out'), (2.9, {'sword': PLANT_R}, 'in'), (3.1, {'sword': ((17, 42, -16), norm((0.05, -0.6, -0.8)), None, 'cane', 0.0)}, 'smooth'),
                (3.35, {'sword': ((15.5, 35.2, -17.3), norm((-0.08, -0.48, -0.87)), None, 'sword', 0.0)}, 'out'), (3.6, {'sword': CS['sword']}, 'smooth')])
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (0.5, {'off': ((1.5, -1.5, 1.0), (8, 0, 2)), 'space': 'chest'}, 'out'),
                (1.0, {'off': ((1.5, -1.5, 1.0), (8, 0, 2)), 'space': 'chest'}, 'in'), (1.06, {'off': ((1.4, -1.3, 0.8), (2, 0, 10)), 'space': 'chest'}, 'out'),
                (1.3, {'off': ((1.5, -1.5, 1.0), (8, 0, 2)), 'space': 'chest'}, 'inout'), (1.85, {'off': ((2.5, 2.0, -2.0), (-10, 0, -6)), 'space': 'chest'}, 'in'),
                (2.25, {'palm': ((-29, 54, -8), norm((-0.5, 0.8, -0.2)), norm((0.2, 0.2, -1)))}, 'out'), (2.85, {'palm': ((-28, 53, -7), norm((-0.5, 0.8, -0.2)), norm((0.2, 0.2, -1)))}, 'inout'),
                (3.6, dict(CS['handL'], space='chest'), 'smooth')])
    finish()

# ================================================================= 10. stomp (2.0s) - impact 0.95s
if want('stomp'):
    begin('stomp', 2.0, 'once')
    fk('body', [cs_fk('body', 0), cs_fk('body', 0.3, d=(0, 0, -3), p=(3.2, -2.4, 0.6), ease='inout'), cs_fk('body', 0.72, d=(3, 0, -4), p=(3.4, -1.2, 0.8), ease='smooth'),
                cs_fk('body', 0.8, d=(3.5, 0, -4), p=(3.4, -1.1, 0.8), ease='in4'), cs_fk('body', 0.95, d=(-6, 0, 1), p=(0.6, -4.4, -0.4), ease='out'),
                cs_fk('body', 1.03, d=(-7, 0, 1), p=(0.6, -5.0, -0.5), ease='smooth'), cs_fk('body', 1.2, d=(-4, 0, 0.5), p=(0.5, -3.6, -0.3), ease='inout'), cs_fk('body', 2.0)])
    fk('waist', [cs_fk('waist', 0), cs_fk('waist', 0.7, d=(2, 0, 3), ease='smooth'), cs_fk('waist', 0.8, d=(2.5, 0, 3), ease='in4'), cs_fk('waist', 0.97, d=(-5, 0, 0), ease='out'),
                 cs_fk('waist', 1.2, d=(-3, 0, 0)), cs_fk('waist', 2.0)])
    fk('chest', [cs_fk('chest', 0), cs_fk('chest', 0.72, d=(6, 4, 6), ease='smooth'), cs_fk('chest', 0.8, d=(7, 4, 6), ease='in4'), cs_fk('chest', 0.98, d=(-14, 0, -1), ease='out'),
                 cs_fk('chest', 1.08, d=(-16, 0, -1)), cs_fk('chest', 1.3, d=(-6, 0, 0), ease='inout'), cs_fk('chest', 2.0)])
    fk('head', [cs_fk('head', 0), cs_fk('head', 0.72, d=(-6, 0, -3)), cs_fk('head', 0.82, d=(-6, 0, -3), ease='in4'), cs_fk('head', 1.0, d=(-4, 0, 0), ease='out'),
                cs_fk('head', 1.06, d=(-12, 0, 2)), cs_fk('head', 1.2, d=(-2, 0, -1)), cs_fk('head', 2.0)])
    fk('jaw', [cs_fk('jaw', 0), cs_fk('jaw', 0.75, d=(6, 0, 0)), cs_fk('jaw', 0.95, d=(4, 0, 0), ease='out'), cs_fk('jaw', 1.02, d=(26, 0, 0), ease='out'), cs_fk('jaw', 1.35, d=(14, 0, 0)), cs_fk('jaw', 2.0)])
    fk('skirt', [cs_fk('skirt', 0), cs_fk('skirt', 0.72, d=(-8, 0, -8)), cs_fk('skirt', 0.96, d=(14, 0, 0), ease='out'), cs_fk('skirt', 1.2, d=(-3, 0, 0)), cs_fk('skirt', 2.0)])
    fL = CS['footL']
    feet('L', [(0, fL, 'smooth'), (0.28, fL, 'inout'), (0.7, dict(fL, d=L.add3(fL['d'], (1.5, 14.0, 2.5)), pitch=12, pivot='ankle'), 'smooth'),
               (0.8, dict(fL, d=L.add3(fL['d'], (1.5, 14.6, 2.6)), pitch=14, pivot='ankle'), 'in4'), (0.95, fL, 'smooth'), (2.0, fL, 'smooth')])
    feet('R', [(0, CS['footR'], 'smooth'), (2.0, CS['footR'], 'smooth')])
    g, b, f, m, tl = CS['sword']
    hands('R', [(0, {'sword': CS['sword'], 'space': 'chest'}, 'smooth'), (0.72, {'sword': (L.add3(g, (3, 4, 1)), norm((0.1, -0.2, -0.97)), f, m, tl), 'space': 'chest'}, 'smooth'),
                (0.8, {'sword': (L.add3(g, (3, 4.2, 1)), norm((0.1, -0.2, -0.97)), f, m, tl), 'space': 'chest'}, 'in4'),
                (0.98, {'sword': ((17.5, 31.5, -15.0), norm((0.04, -0.33, -0.94)), f, m, tl)}, 'out'),
                (1.1, {'sword': ((17.0, 32.5, -15.5), norm((0.0, -0.36, -0.93)), f, m, tl)}, 'smooth'), (2.0, {'sword': CS['sword']}, 'smooth')])
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (0.72, {'off': ((-6, 18, -6), (-40, 0, -50)), 'space': 'chest'}, 'smooth'),
                (0.8, {'off': ((-6, 18.5, -6), (-40, 0, -52)), 'space': 'chest'}, 'in4'), (0.98, {'off': ((1, 3, -6), (-20, 0, -8)), 'space': 'chest'}, 'out'),
                (1.15, {'off': ((2, 4, -7), (-24, 0, -10)), 'space': 'chest'}, 'smooth'), (2.0, dict(CS['handL'], space='chest'), 'smooth')])
    finish()

# ================================================================= 11. dash (1.6s) - launch 0.45s, airborne until 0.85s
if want('dash'):
    begin('dash', 1.6, 'once')
    fk('body', [cs_fk('body', 0), cs_fk('body', 0.36, d=(-8, 4, 0), p=(0, -5.5, 2.0), ease='smooth'), cs_fk('body', 0.42, d=(-9, 4, 0), p=(0, -6.0, 2.2), ease='expo_out'),
                cs_fk('body', 0.55, d=(-18, 6, 0), p=(0, -1.0, -5.0), ease='smooth'), cs_fk('body', 0.78, d=(-16, 6, 0), p=(0, -1.6, -4.0), ease='in'),
                cs_fk('body', 0.86, d=(-14, 4, 0), p=(0, -6.0, -2.0), ease='out'), cs_fk('body', 0.96, d=(-8, 2, 0), p=(0, -5.0, -0.8), ease='smooth'),
                cs_fk('body', 1.25, d=(-1, 0, 0), p=(0, -0.8, 0), ease='inout'), cs_fk('body', 1.6)])
    fk('waist', [cs_fk('waist', 0), cs_fk('waist', 0.4, d=(-4, 3, 0)), cs_fk('waist', 0.58, d=(-6, 4, 0)), cs_fk('waist', 0.88, d=(-8, 2, 0), ease='out'), cs_fk('waist', 1.6)])
    fk('chest', [cs_fk('chest', 0), cs_fk('chest', 0.4, d=(-8, 6, 0), ease='smooth'), cs_fk('chest', 0.6, d=(-12, 10, 0)), cs_fk('chest', 0.8, d=(-10, 8, 0), ease='in'),
                 cs_fk('chest', 0.9, d=(-16, 4, 0), ease='out'), cs_fk('chest', 1.05, d=(-4, 0, 0)), cs_fk('chest', 1.6)])
    fk('head', [cs_fk('head', 0), cs_fk('head', 0.4, d=(14, -8, 0)), cs_fk('head', 0.62, d=(22, -12, 0)), cs_fk('head', 0.86, d=(16, -6, 0)), cs_fk('head', 0.98, d=(6, 0, 0), ease='out'),
                cs_fk('head', 1.6)])
    fk('jaw', [cs_fk('jaw', 0), cs_fk('jaw', 0.38, d=(10, 0, 0)), cs_fk('jaw', 0.5, d=(30, 0, 0), ease='out'), cs_fk('jaw', 0.8, d=(22, 0, 0)), cs_fk('jaw', 1.0, d=(8, 0, 0)), cs_fk('jaw', 1.6)])
    fk('skirt', [cs_fk('skirt', 0), cs_fk('skirt', 0.42, d=(-6, 0, 0)), cs_fk('skirt', 0.6, d=(18, 0, 0), ease='out'), cs_fk('skirt', 0.86, d=(-6, 0, 0)), cs_fk('skirt', 1.1, d=(4, 0, 0)), cs_fk('skirt', 1.6)])
    fL, fR = CS['footL'], CS['footR']
    feet('L', [(0, fL, 'smooth'), (0.42, fL, 'expo_out'), (0.55, dict(fL, d=L.add3(fL['d'], (0, 6.5, -3)), pitch=8, pivot='ankle'), 'smooth'),
               (0.76, dict(fL, d=L.add3(fL['d'], (0, 3.0, 0)), pitch=14, pivot='ankle'), 'in'), (0.84, dict(fL, pitch=12, pivot='heel'), 'out'), (0.92, fL, 'smooth'), (1.6, fL, 'smooth')])
    feet('R', [(0, fR, 'smooth'), (0.4, fR, 'in'), (0.47, dict(fR, pitch=-34, pivot='toe'), 'out'), (0.6, dict(fR, d=L.add3(fR['d'], (0, 8, 6)), pitch=-40, pivot='ankle'), 'smooth'),
               (0.8, dict(fR, d=L.add3(fR['d'], (0, 4, 2)), pitch=-18, pivot='ankle'), 'in'), (0.88, dict(fR, pitch=-8, pivot='toe'), 'out'), (0.96, fR, 'smooth'), (1.6, fR, 'smooth')])
    THR = ((10.0, 40.0, -31.0), norm((-0.08, -0.08, -1)), None, 'sword', 0.0)
    hands('R', [(0, {'sword': CS['sword']}, 'smooth'), (0.38, {'sword': ((21, 38, 4), norm((0, 0.04, -1)), None, 'sword', 0.0)}, 'smooth'),
                (0.43, {'sword': ((21.5, 38, 5), norm((0, 0.04, -1)), None, 'sword', 0.0)}, 'expo_out'), (0.6, {'sword': THR}, 'smooth'),
                (0.8, {'sword': ((10.5, 39.0, -30.0), norm((-0.06, -0.15, -1)), None, 'sword', 0.0)}, 'in'),
                (0.9, {'sword': ((13, 36, -24), norm((-0.04, -0.4, -0.92)), None, 'sword', 0.0)}, 'out'), (1.6, {'sword': CS['sword']}, 'smooth')])
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (0.38, {'off': ((4, 10, -12), (-50, 0, -10)), 'space': 'chest'}, 'smooth'),
                (0.6, {'off': ((-3, 5, 10), (14, 0, -18)), 'space': 'chest'}, 'smooth'), (0.86, {'off': ((2, 4, -4), (-10, 0, -20)), 'space': 'chest'}, 'out'),
                (1.6, dict(CS['handL'], space='chest'), 'smooth')])
    finish()

# ================================================================= 12. death (3.8s, hold)
if want('death'):
    begin('death', 3.8, 'hold')
    K1 = dict(footL=dict(d=(2.0, 0, -8.0), yaw=6), footR=dict(d=(-1.5, 2.6, 13.0), yaw=-6, pitch=-62, pivot='toe'))
    K2L = dict(d=(1.5, 2.6, 12.0), yaw=8, pitch=-64, pivot='toe')
    fk('body', [cs_fk('body', 0), (0.16, (6, -6, 0), (0.6, -2.4, 2.2), 'out'), (0.45, (2, -4, 0), (0.6, -3.0, 2.6), 'smooth'), (0.8, (-4, -2, 0), (0.4, -4.4, 0.8), 'in'),
                (1.1, (-6, -2, 0), (0.4, -12.8, -1.2), 'out'), (1.3, (-5, -2, 0), (0.4, -12.2, -1.0), 'smooth'), (1.5, (-5, -1, 0), (0.3, -12.2, -0.6), 'in'),
                (1.72, (-8, 0, 0), (0.2, -9.4, 0.6), 'out'), (1.85, (-7, 0, 0), (0.2, -8.8, 0.5), 'smooth'), (2.5, (-7, 0, 0), (0.2, -8.9, 0.5), 'in'),
                (3.05, (-8, 2, -2), (0.2, -10.6, -0.6), 'out'), (3.25, (-7, 2, -2), (0.2, -10.3, -0.5), 'smooth'), (3.8, (-7, 2, -2), (0.2, -10.4, -0.5), 'smooth')])
    fk('waist', [cs_fk('waist', 0), (0.18, (6, 0, 0), Z, 'out'), (0.8, (-6, 0, 0), Z), (1.75, (-8, 0, 0), Z), (2.5, (-8, 0, 0), Z, 'in'), (3.1, (-10, 0, 0), Z, 'out'), (3.8, (-9, 0, 0), Z)])
    fk('chest', [cs_fk('chest', 0), (0.14, (14, -4, 0), Z, 'out'), (0.5, (2, -2, 0), Z), (0.85, (-10, 0, 0), Z, 'in'), (1.15, (-16, 0, 0), Z, 'out'), (1.8, (-18, 0, 0), Z),
                 (2.05, (-15, 0, 0), (0, 0.4, 0)), (2.3, (-19, 0, 0), Z), (2.6, (-20, 0, 2), Z, 'in'), (3.1, (-24, 0, 8), Z, 'out'), (3.3, (-22, 0, 7), Z), (3.8, (-23, 0, 8), Z)])
    fk('head', [cs_fk('head', 0), (0.12, (24, 6, 0), Z, 'out'), (0.45, (6, 2, 0), Z), (0.9, (-14, 0, 0), Z), (1.8, (-20, 0, 2), Z), (2.5, (-26, 0, 4), Z, 'in'),
                (3.12, (-36, 6, 16), Z, 'out'), (3.25, (-32, 6, 14), Z, 'smooth'), (3.45, (-35, 6, 15), Z), (3.8, (-35, 6, 15), Z)])
    fk('jaw', [cs_fk('jaw', 0), (0.12, (28, 0, 0), Z, 'out'), (0.6, (14, 0, 0), Z), (1.8, (8, 0, 0), Z), (3.0, (6, 0, 0), Z, 'in'), (3.3, (24, 0, 0), Z, 'out'), (3.8, (22, 0, 0), Z)])
    fk('skirt', [cs_fk('skirt', 0), (0.2, (-6, 0, 0)), (1.1, (12, 0, 0)), (1.75, (16, 0, 0)), (3.1, (20, 0, 2)), (3.8, (20, 0, 2))])
    feet('L', [(0, CS['footL'], 'smooth'), (0.8, CS['footL'], 'smooth'), (0.88, dict(CS['footL'], d=L.add3(CS['footL']['d'], (0, 2.0, 0))), 'smooth'),
               (1.0, K1['footL'], 'smooth'), (1.48, K1['footL'], 'out'), (1.56, dict(K1['footL'], d=L.add3(K1['footL']['d'], (0, 3.0, 1.0))), 'smooth'),
               (1.64, dict(d=(1.8, 3.4, 4.0), yaw=8, pitch=-34, pivot='ankle'), 'out'), (1.72, K2L, 'smooth'), (3.8, K2L, 'smooth')])
    feet('R', [(0, CS['footR'], 'smooth'), (0.78, CS['footR'], 'out'), (0.86, dict(CS['footR'], d=L.add3(CS['footR']['d'], (0, 2.5, 0.5))), 'smooth'),
               (0.96, dict(d=(-1.0, 3.6, 11), yaw=-10, pitch=-40, pivot='toe'), 'out'), (1.1, K1['footR'], 'smooth'), (3.8, K1['footR'], 'smooth')])
    pole('POLE_knee.R', [(0, (8.14, 19.12, -33.86), 'smooth'), (0.8, (8.14, 19.12, -33.86), 'in'), (1.1, (8, 6, -32), 'smooth'), (3.8, (8, 6, -32), 'smooth')])
    pole('POLE_knee.L', [(0, (-8.42, 18.82, -32.43), 'smooth'), (1.5, (-8.42, 18.82, -32.43), 'in'), (1.72, (-8, 6, -32), 'smooth'), (3.8, (-8, 6, -32), 'smooth')])
    DPL = ((8.0, 30.0, -20.0), (0, -1, -0.04), None, 'cane', 0.0)
    hands('R', [(0, {'sword': CS['sword']}, 'smooth'), (0.16, {'sword': ((17, 33, -15), norm((0.0, -0.75, -0.66)), None, 'sword', 0.0)}, 'out'),
                (0.4, {'sword': ((15, 34, -18), norm((0.05, -0.8, -0.6)), None, 'cane', 0.0)}, 'smooth'),
                (0.7, {'sword': ((10, 36, -20), (0, -1, -0.04), None, 'cane', 0.0)}, 'out'), (1.1, {'sword': ((8.0, 31.0, -20.0), (0, -1, -0.04), None, 'cane')}, 'smooth'),
                (1.72, {'sword': DPL}, 'smooth'), (3.8, {'sword': DPL}, 'smooth')])
    DLP = ((5.4, 34.5, -20.2), norm((0, 0.05, -1)), (1, 0, 0))
    hands('L', [(0, dict(CS['handL'], space='chest'), 'smooth'), (0.15, {'off': ((-6, 10, 4), (20, 0, -50)), 'space': 'chest'}, 'out'),
                (0.7, {'off': ((4, 6, -10), (-30, 0, -10)), 'space': 'chest'}, 'smooth'), (1.15, {'palm': DLP}, 'smooth'), (2.55, {'palm': DLP}, 'in'),
                (2.75, {'palm': ((4, 31, -21), norm((0.1, -0.3, -0.95)), (1, 0, 0))}, 'smooth'),
                (3.15, {'off': ((5, -8, -3), (10, 0, 10)), 'space': 'chest'}, 'out'), (3.35, {'off': ((5, -7.2, -3), (8, 0, 8)), 'space': 'chest'}, 'smooth'),
                (3.8, {'off': ((5, -7.5, -3), (9, 0, 9)), 'space': 'chest'}, 'smooth')])
    finish()

for o in bpy.data.objects: o.select_set(False)
out = os.path.join(L.BM.HERE, 'withered_sentinel_anim.blend')
bpy.ops.wm.save_as_mainfile(filepath=out)
print('SAVED', out, [a.name for a in bpy.data.actions if 'bb_length' in a])
