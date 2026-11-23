"""Batch 1: walk + sweep, rebuilt pose-to-pose with IK foot planting and full-body mechanics.
Run: blender -b withered_sentinel_reworked.blend --python ws_batch1.py   (saves in place)"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import ws_tools as T
from ws_tools import track, eul, dir_az_el, smooth, PX

from ws_common import *

# ================================================================= WALK  (2.4 s, 48 frames, two heavy steps)
NW = 48
STEP = 22.0                 # px per step (body travels 2 steps per cycle)
V = 2 * STEP / NW           # ground speed, px per frame: a planted foot moves back at exactly this rate
STANCE = 29                 # frames a foot is planted (double support ~10 frames per cycle)
Y_CONTACT = -13.0


def foot_walk(r, S, f):
    t = (f - (0 if S == "right" else NW // 2)) % NW
    x = -7.0 if S == "right" else 7.0
    if t <= STANCE:
        y = Y_CONTACT + V * t
        if t < 4:                                           # heel strike -> foot slap
            p = -8 * (1 - smooth(t / 4))
            plant(r, S, (x, y), z=3 * math.sin(math.radians(-p)), pitch=0, yaw=0)
            r.rotate(f"{S}_foot", Matrix.Rotation(math.radians(p), 3, "X"))
        elif t > STANCE - 7:                                # heel peels off, toe stays planted
            p = 24 * T.ease_in((t - (STANCE - 7)) / 7)
            plant(r, S, (x, y), pitch=p, yaw=0)
        else:
            plant(r, S, (x, y), yaw=0)
    else:
        s = (t - STANCE) / (NW - STANCE)
        y0, y1 = Y_CONTACT + V * STANCE, Y_CONTACT + V * NW - 2 * STEP
        y = y0 + (Y_CONTACT - y0) * smooth(s)
        lift = 4.5 * math.sin(math.pi * min(1.0, s ** 0.8))
        p = track([(0, 24), (0.35, 6), (0.75, -6), (1.0, -8)], s)
        z = lift + (3 * math.sin(math.radians(-p)) if p < 0 else 0)
        plant(r, S, (x, y), z=z, pitch=max(p, 0), yaw=0)
        if p < 0:
            r.rotate(f"{S}_foot", Matrix.Rotation(math.radians(p), 3, "X"))


def pose_walk(r, f):
    u = (f % (NW // 2)) / (NW // 2)                         # step phase: 0 = heel strike
    ph = 2 * math.pi * f / NW
    hz = track([(0, 0, "c"), (0.18, -1.1, "c"), (0.42, -0.35, "c"), (0.62, 0.35, "c"), (1.0, 0, "c")], u)
    hx = -1.5 * math.sin(ph)                                # over the planted foot
    yaw = -6 * math.sin(2 * math.pi * (f - 2) / NW)         # swing-side hip leads
    roll = 2.5 * math.sin(ph)
    r.move("body", (hx, 0, hz - 0.6))
    r.rotate("body", eul(4, roll, yaw))
    for S in ("right", "left"):
        foot_walk(r, S, f)
    lag = lambda k: -6 * math.sin(2 * math.pi * (f - 2 - k) / NW)
    impact = bump(u, 0.12, 0.08)
    r.rotate("waist", eul(3 + 1.2 * impact, 0, -0.6 * lag(2)))
    r.rotate("chest", eul(4 + 2.0 * impact, -roll * 0.5, -0.9 * lag(3)))
    head_world(r, yaw=1.5 * math.sin(ph - 1.0), pitch=7 + 2.5 * bump(u, 0.22, 0.1))
    r.rotate("jaw", eul(5 + 3 * math.sin(ph * 2 + 1.2)))
    # sword arm: dragged behind; the blade's resistance tugs it back at every heel strike
    tug = 0.07 * bump(u, 0.15, 0.12)
    r.aim("right_arm", (-0.34, 0.40 + tug, -0.85))
    r.aim("right_forearm", (-0.22, 0.60 + tug * 1.4, -0.77))
    r.aim("right_hand", (-0.14, 0.82, -0.56))
    drag_blade(r, f)
    # free arm: swings against its leg, elbow and claw trailing
    sl = lambda k: math.cos(2 * math.pi * (f - k) / NW)
    r.aim("left_arm", (0.30, -0.10 - 0.30 * sl(3), -0.93))
    r.aim("left_forearm", (0.22, -0.42 - 0.32 * sl(6), -0.80))
    r.aim("left_hand", (0.18, -0.55 - 0.3 * sl(8), -0.75))
    r.rotate("left_hand", eul(-14 - 6 * sl(9)))
    cape(r, back=8 + 4 * bump(u, 0.3, 0.15), yaw=-0.4 * lag(6), flutter=1.5 * math.sin(ph * 2 - 1.5))
    r.rotate("skirt", eul(1.5 * math.sin(ph * 2 - 0.8), 0, 0.5 * lag(4)))


T.bake(rig, "walk", NW, pose_walk, loop=True)
print("WALK_BAKED", flush=True)

# ================================================================= SWEEP (2.8 s = 56 frames; blade passes front on frame 26 = hit tick)
NS = 56
HIP_YAW = [(0, -8), (6, -14), (14, -28), (18, -30, "l"), (20, -22, "l"), (22, -6, "l"), (24, 10, "l"), (26, 22, "o"), (28, 30), (34, 36), (38, 32), (46, 6), (56, -8)]
CHEST_YAW = [(0, -4), (6, -30), (14, -62), (18, -66, "l"), (20, -62, "l"), (22, -40, "l"), (24, -8, "l"), (26, 25, "l"), (28, 48, "o"), (31, 64), (34, 72), (38, 64), (46, 22), (56, -4)]
SWORD_AZ = [(0, -28), (6, -90), (14, -150), (18, -156, "i"), (20, -150, "l"), (22, -118, "l"), (24, -66, "l"), (26, 2, "l"), (28, 55, "o"), (31, 95), (34, 118), (38, 110), (46, 40), (56, -28)]
HAND_EL = [(0, -55), (6, -25), (14, 5), (18, 8), (22, -4), (26, -10), (31, -20), (34, -30), (38, -42), (46, -50), (56, -55)]
BLADE_EL = [(0, -35), (6, -5), (14, 20), (18, 22), (22, 2), (26, -6), (31, -16), (34, -30), (38, -45), (46, -40), (56, -35)]
BODY_X = [(0, 0), (6, -1.2), (14, -1.8), (20, -1.5), (26, 1.6), (34, 1.8), (46, 0.3), (56, 0)]
BODY_Y = [(0, 0), (6, 1.5), (14, 2.5), (20, 2.0), (26, -2.5), (34, -2.2), (46, -0.3), (56, 0)]
BODY_Z = [(0, 0), (6, -1.0), (14, -2.2), (18, -2.4), (26, -1.6), (28, -2.8, "o"), (34, -2.2), (46, -0.5), (56, 0)]
HEAD_YAW = [(0, 0), (14, -8), (26, 4), (31, 14), (38, 10), (56, 0)]
LEFT_UP = [(0, (0.35, -0.55, -0.75)), (14, (0.45, -0.85, -0.10)), (22, (0.55, -0.3, -0.75)), (26, (0.6, 0.2, -0.75)), (34, (0.9, 0.1, -0.4)), (46, (0.5, -0.4, -0.75)), (56, (0.35, -0.55, -0.75))]
LEFT_FORE = [(0, (0.1, -0.85, -0.3)), (14, (0.3, -0.95, 0.05)), (22, (0.45, -0.2, -0.85)), (26, (0.45, 0.35, -0.8)), (34, (0.85, -0.2, -0.5)), (46, (0.2, -0.8, -0.5)), (56, (0.1, -0.85, -0.3))]
HEEL_R = [(0, 0), (24, 0), (30, 22, "o"), (38, 18), (46, 0), (56, 0)]


def pose_sweep(r, f):
    bx, by, bz = track(BODY_X, f), track(BODY_Y, f), track(BODY_Z, f)
    hy = track(HIP_YAW, f)
    r.move("body", (bx, -0.5 + by, -2.5 + bz))
    r.rotate("body", eul(5, 0, hy))
    plant(r, "left", STANCE_FEET["left"])
    plant(r, "right", STANCE_FEET["right"], pitch=track(HEEL_R, f))
    rel = track(CHEST_YAW, f) - hy
    tension = 0.6 * math.sin(f * 2.3) * smooth((f - 13) / 2) * (1 - smooth((f - 19) / 1))     # coiled tremble in the hold
    r.rotate("waist", eul(2, 0, rel * 0.4))
    r.rotate("chest", eul(3 + (4 if 24 <= f <= 32 else 0) * smooth((f - 24) / 3), 0, rel * 0.6 + tension))
    head_world(r, yaw=track(HEAD_YAW, f), pitch=5)
    r.rotate("jaw", eul(8 + 10 * smooth((f - 20) / 6) * (1 - smooth((f - 34) / 10))))
    # sword arm: the hand rides the arc, the elbow bends out-back, the blade points outward along the arc
    az, he, be = track(SWORD_AZ, f), track(HAND_EL, f), track(BLADE_EL, f)
    sh = r.head("right_arm")
    target = sh + dir_az_el(az, he) * REACH_R * 0.86
    r.ik("right_arm", "right_forearm", target, pole=Vector((-0.6, 0.5, -0.6)))
    bd = dir_az_el(az + 12, be)
    r.aim("right_hand", bd)
    sword_to(r, bd)
    # free arm counterbalances
    r.aim("left_arm", Vector(track(LEFT_UP, f)).normalized())
    r.aim("left_forearm", Vector(track(LEFT_FORE, f)).normalized())
    r.rotate("left_hand", eul(-16))
    cyaw = track(CHEST_YAW, max(0, f - 6))
    cape(r, back=8 + 14 * smooth((f - 24) / 4) * (1 - smooth((f - 36) / 14)), yaw=-0.35 * cyaw, flutter=2 * math.sin(f * 0.9))


T.bake(rig, "sweep", NS, pose_sweep)
print("SWEEP_BAKED", flush=True)

# ================================================================= quality numbers: foot sliding + floor + sword tip path
def foot_track(act, S, frames):
    rig.ob.animation_data.action = bpy.data.actions[act]
    out = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        pts = rig.sole_points(S)
        out.append((min(p.z for p in pts) / PX, sum(pts, Vector()) / len(pts) / PX))
    return out


for S in ("right", "left"):
    off = 0 if S == "right" else NW // 2
    tr = foot_track("walk", S, [(off + t) % NW for t in range(6, STANCE - 7)])
    speeds = [(tr[i + 1][1].y - tr[i][1].y) for i in range(len(tr) - 1)]
    print(f"WALK {S} planted: speed px/frame {min(speeds):.3f}..{max(speeds):.3f} (target {V:.3f}), sole z {min(z for z, _ in tr):.2f}..{max(z for z, _ in tr):.2f}")
for S in ("left", "right"):
    tr = foot_track("sweep", S, list(range(0, 24)) + list(range(46, 57)))
    xs = [c.x for _, c in tr]; ys = [c.y for _, c in tr]
    print(f"SWEEP {S} planted: drift x {max(xs)-min(xs):.3f}px y {max(ys)-min(ys):.3f}px, sole z {min(z for z, _ in tr):.2f}")
rig.ob.animation_data.action = bpy.data.actions["sweep"]
lows = []
for f in range(0, NS + 1):
    bpy.context.scene.frame_set(f)
    lows.append(round((rig.min_z("sword") - rig.ground) / PX, 2))
print("SWEEP sword lowest px above floor per frame:", min(lows))
bpy.context.scene.frame_set(26)
d = rig.seg("sword")
print("SWEEP at hit frame 26: blade azimuth", round(math.degrees(math.atan2(d.x, -d.y)), 1), "deg (0 = straight ahead)")
rig.ob.animation_data.action = bpy.data.actions["walk"]
tips = []
for f in range(0, NW + 1):
    bpy.context.scene.frame_set(f)
    tips.append(round((rig.min_z("sword") - rig.ground) / PX, 2))
print("WALK sword lowest px above floor:", min(tips), "..", max(tips))
bpy.ops.wm.save_mainfile()
print("BATCH1_OK")
